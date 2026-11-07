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
        key = hashlib.md5((VOICE + RATE + json.dumps(sec["blocks"], ensure_ascii=False)).encode()).hexdigest()[:12]
        if old.get(sec["f"], {}).get("k") == key and os.path.exists("audio/" + sec["f"]):
            timing[sec["f"]] = old[sec["f"]]; print("skip", sec["f"]); continue
        parts, marks, t = [], [], 0.0
        for bid, text in sec["blocks"]:
            mp = "tts/cache/%s.mp3" % hashlib.md5((VOICE + RATE + text).encode()).hexdigest()
            if not os.path.exists(mp):
                await synth(text, mp)
            wav = mp[:-4] + ".wav"
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
