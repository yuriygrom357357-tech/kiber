# Озвучка «Кібер»: кожен блок синтезується окремо, блоки склеюються в один mp3 на розділ,
# мітки часу блоків рахуються з точних тривалостей. Запускається в GitHub Actions.
import asyncio, json, os, subprocess, hashlib, shutil

job = json.load(open("tts/job.json"))
VOICE = job.get("voice", "uk-UA-OstapNeural")
RATE = job.get("rate", "+0%")
GAP = 0.45
os.makedirs("audio", exist_ok=True)
os.makedirs("tts/cache", exist_ok=True)
import edge_tts
import urllib.request, urllib.error

# ---- ElevenLabs (Тарас Вовк) для вибраних лекцій; блоки кешуються в tts/eleven/ (комітяться) ----
EL = {}
if os.path.exists("tts/eleven.json"):
    EL = json.load(open("tts/eleven.json"))
EL_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
EL_LESSONS = set(EL.get("lessons", [])) if EL_KEY else set()
EL_SECTIONS = set(EL.get("sections", [])) if EL_KEY else set()
os.makedirs("tts/eleven", exist_ok=True)
class NoBudget(Exception): pass

def el_req(path, data=None):
    req = urllib.request.Request("https://api.elevenlabs.io" + path, data=json.dumps(data).encode() if data is not None else None,
        headers={"xi-api-key": EL_KEY, "Content-Type": "application/json", "Accept": "*/*"}, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def el_model():
    m = EL.get("model", "auto-v4")
    if not m.startswith("auto"): return m
    try:
        ms = json.loads(el_req("/v1/models"))
        for x in ms:
            if "v4" in x.get("model_id", "") and x.get("can_do_text_to_speech", True): return x["model_id"]
        for x in ms:
            if "v3" in x.get("model_id", "") and x.get("can_do_text_to_speech", True): return x["model_id"]
    except Exception as e:
        print("models lookup failed", e)
    return "eleven_multilingual_v2"

def el_left():
    try:
        s = json.loads(el_req("/v1/user/subscription"))
        return s["character_limit"] - s["character_count"]
    except Exception as e:
        print("subscription check failed (продовжую з локальним лімітом)", e); return None

EL_STATE = {"model": None, "left": None, "used": 0}
def el_block(text):
    p = "tts/eleven/%s.mp3" % hashlib.md5((EL["voice_id"] + text).encode()).hexdigest()
    if os.path.exists(p): return p
    if EL_STATE["model"] is None:
        EL_STATE["model"] = el_model(); EL_STATE["left"] = el_left(); print("ElevenLabs model", EL_STATE["model"], "credits left", EL_STATE["left"])
    left = EL_STATE["left"]
    if left is not None and left - EL_STATE["used"] - len(text) < EL.get("reserve", 2500):
        raise NoBudget()
    body = {"text": text, "model_id": EL_STATE["model"], "voice_settings": {"stability": EL.get("stability", 0.5), "similarity_boost": EL.get("similarity", 0.75)}}
    for attempt in range(4):
        try:
            audio = el_req("/v1/text-to-speech/%s?output_format=mp3_44100_128" % EL["voice_id"], body)
            if len(audio) > 1000:
                open(p, "wb").write(audio); EL_STATE["used"] += len(text); return p
        except urllib.error.HTTPError as e:
            msg = e.read()[:300]
            print("ElevenLabs HTTP", e.code, msg)
            if e.code in (401, 402, 403) or b"quota" in msg: raise NoBudget()
        except Exception as e:
            print("ElevenLabs retry", attempt, e)
        import time; time.sleep(3 + attempt * 3)
    raise NoBudget()

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode().strip())

async def synth(text, path):
    for attempt in range(5):
        try:
            c = edge_tts.Communicate(text, VOICE, rate=RATE)
            await c.save(path)
            if os.path.getsize(path) > 1000:
                return
        except Exception as e:
            print("retry", attempt, e)
        await asyncio.sleep(2 + attempt * 2)
    raise RuntimeError("TTS failed: " + text[:60])

async def main():
    timing = {}
    old = {}
    if os.path.exists("tts/timing.json"):
        try: old = json.load(open("tts/timing.json"))
        except Exception: old = {}
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP), "-ar", "24000", "-ac", "1", "tts/cache/gap.wav"], check=True)
    for sec in job["sections"]:
        use_el = sec["f"].split("_")[0] in EL_LESSONS or sec["f"] in EL_SECTIONS
        vtag = ("EL:" + EL["voice_id"]) if use_el else (VOICE + RATE)
        key = hashlib.md5((vtag + json.dumps(sec["blocks"], ensure_ascii=False)).encode()).hexdigest()[:12]
        if old.get(sec["f"], {}).get("k") == key and os.path.exists("audio/" + sec["f"]):
            timing[sec["f"]] = old[sec["f"]]; print("skip", sec["f"]); continue
        gh = hashlib.md5(json.dumps(sec["blocks"], ensure_ascii=False).encode()).hexdigest()[:12]
        if not use_el and old.get(sec["f"], {}).get("g") == gh and os.path.exists("audio/" + sec["f"]):
            timing[sec["f"]] = old[sec["f"]]; print("keep gemini", sec["f"]); continue
        if use_el:
            try:
                for bid, text in sec["blocks"]: el_block(text)
            except NoBudget:
                print("ElevenLabs: не вистачає кредитів — розділ лишається з попереднім голосом", sec["f"])
                if sec["f"] in old and os.path.exists("audio/" + sec["f"]):
                    timing[sec["f"]] = old[sec["f"]]; continue
                use_el = False
                key = hashlib.md5((VOICE + RATE + json.dumps(sec["blocks"], ensure_ascii=False)).encode()).hexdigest()[:12]
        parts, marks, t = [], [], 0.0
        for bid, text in sec["blocks"]:
            if use_el:
                mp = el_block(text)
            else:
                mp = "tts/cache/%s.mp3" % hashlib.md5((VOICE + RATE + text).encode()).hexdigest()
                if not os.path.exists(mp):
                    await synth(text, mp)
            wav = "tts/cache/" + os.path.basename(mp)[:-4] + (".el" if use_el else "") + ".wav"
            if not os.path.exists(wav):
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp, "-ar", "24000", "-ac", "1", wav], check=True)
            marks.append([bid, round(t, 2)])
            parts.append(wav); t += dur(wav)
            parts.append("tts/cache/gap.wav"); t += GAP
        lst = "tts/cache/list.txt"
        with open(lst, "w") as fh:
            for p in parts: fh.write("file '%s'\n" % os.path.abspath(p))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-ac", "1", "-ar", "24000", "-b:a", "64k", "audio/" + sec["f"]], check=True)
        timing[sec["f"]] = {"d": round(dur("audio/" + sec["f"]), 1), "m": marks, "k": key}
        print("ok", sec["f"], timing[sec["f"]]["d"])
    json.dump(timing, open("tts/timing.json", "w"), ensure_ascii=False)
    if EL_LESSONS or EL_SECTIONS: print("ElevenLabs characters used this run:", EL_STATE["used"])
    # короткі кліпи для тестів (питання, варіанти, пояснення)
    clips = job.get("clips", [])
    os.makedirs("audio/q", exist_ok=True)
    sem = asyncio.Semaphore(5)
    todo = [c for c in clips if not os.path.exists("audio/" + c["f"])]
    print("clips total", len(clips), "to make", len(todo))
    async def one(c):
        async with sem:
            tmp = "tts/cache/clip_%s.mp3" % c["f"].replace("/", "_")
            await synth(c["text"], tmp)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-ac", "1", "-ar", "24000", "-b:a", "48k", "audio/" + c["f"]], check=True)
    await asyncio.gather(*[one(c) for c in todo])
    keep = set(c["f"] for c in clips)
    for fn in os.listdir("audio/q"):
        if "q/" + fn not in keep: os.remove("audio/q/" + fn)

asyncio.run(main())
