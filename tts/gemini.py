# Озвучка тестових кліпів голосом Google Gemini TTS (безкоштовний ключ AI Studio).
# Кліпи групуються по кілька в один запит (економія безкоштовного ліміту), потім ріжуться за паузами.
# Прогрес зберігається в tts/gemini_done.json; при вичерпанні ліміту скрипт зупиняється і продовжує наступного разу.
import json, os, sys, base64, subprocess, hashlib, time, urllib.request, urllib.error

KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not KEY:
    print("GEMINI_API_KEY не задано — пропускаю"); sys.exit(0)
G = json.load(open("tts/gemini.json"))
job = json.load(open("tts/job.json"))
DONE_P = "tts/gemini_done.json"
done = json.load(open(DONE_P)) if os.path.exists(DONE_P) else {}
VOICE = G["voice"]
os.makedirs("tts/cache", exist_ok=True); os.makedirs("audio/q", exist_ok=True)
REQ = {"n": 0}
class Limit(Exception): pass

def tts(text, voice):
    if REQ["n"] >= G.get("max_requests", 90): raise Limit("max_requests")
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % G["model"]
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    for attempt in range(4):
        REQ["n"] += 1
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
            for p in d["candidates"][0]["content"]["parts"]:
                if "inlineData" in p: return base64.b64decode(p["inlineData"]["data"])
            raise RuntimeError("no audio")
        except urllib.error.HTTPError as e:
            msg = e.read()[:400].decode("utf-8", "ignore"); print("Gemini HTTP", e.code, msg)
            if e.code == 429:
                if "PerDay" in msg or "per day" in msg.lower() or attempt >= 2: raise Limit("429")
                time.sleep(40); continue
            if e.code == 404 and G["model"] != "gemini-2.5-flash-preview-tts":
                G["model"] = "gemini-2.5-flash-preview-tts"; url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % G["model"]; print("fallback model", G["model"]); continue
            if e.code in (400, 401, 403): raise Limit(str(e.code))
        except Limit: raise
        except Exception as e:
            print("Gemini retry", attempt, e)
        time.sleep(8 + attempt * 8)
    raise Limit("failed")

def pcm_to_wav(pcm, path):
    raw = path + ".pcm"; open(raw, "wb").write(pcm)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", raw, path], check=True); os.remove(raw)

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode())

def split_by_silence(wav, n):
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", wav, "-af", "silencedetect=n=-40dB:d=0.7", "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x.split("silence_start: ")[1].split()[0]) for x in out.splitlines() if "silence_start" in x]
    ends = [float(x.split("silence_end: ")[1].split()[0]) for x in out.splitlines() if "silence_end" in x]
    total = dur(wav)
    gaps = [(s, e) for s, e in zip(starts, ends) if s > 0.3 and e < total - 0.3]
    if len(gaps) < n - 1: return None
    gaps = sorted(sorted(gaps, key=lambda g: g[1] - g[0], reverse=True)[:n - 1])
    cuts, t0 = [], 0.0
    for s, e in gaps:
        cuts.append((t0, s + 0.15)); t0 = max(e - 0.15, s)
    cuts.append((t0, total))
    return cuts

def save_clip(wav, a, b, f):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-ss", "%.3f" % a, "-to", "%.3f" % b, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                    "-ac", "1", "-ar", "24000", "-b:a", "48k", "audio/" + f], check=True)

def batch_prompt(texts):
    lines = "\n\n".join(texts)
    return (G["style"] + " Прочитай по черзі кожен з наведених нижче фрагментів. Між фрагментами роби паузу дві секунди. "
            "Нічого не додавай від себе, не читай номерів і не коментуй.\n\n" + lines)

if "--samples" in sys.argv:
    os.makedirs("tts/samples", exist_ok=True)
    txt = G["style"] + " Прочитай: Інструктор особисто доводить заходи безпеки перед кожним заняттям. Яке положення зброї використовують під час бойового наказу? Правильно. За спиною."
    for v in G["samples"]:
        try:
            pcm_to_wav(tts(txt, v), "tts/samples/%s.wav" % v)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "tts/samples/%s.wav" % v, "-b:a", "96k", "tts/samples/%s.mp3" % v], check=True)
            os.remove("tts/samples/%s.wav" % v); print("sample ok", v)
        except Limit as e:
            print("sample failed", v, e)
    sys.exit(0)

clips = [c for c in job.get("clips", []) if done.get(c["f"]) != hashlib.md5((VOICE + c["text"]).encode()).hexdigest()[:10]]
print("Gemini: кліпів до озвучки", len(clips), "голос", VOICE)
B = G.get("batch", 10)
made = 0
try:
    i = 0
    while i < len(clips):
        grp = clips[i:i + B]
        wav = "tts/cache/gbatch.wav"
        ok = False
        if len(grp) > 1:
            pcm_to_wav(tts(batch_prompt([c["text"] for c in grp]), VOICE), wav)
            cuts = split_by_silence(wav, len(grp))
            if cuts:
                for c, (a, b) in zip(grp, cuts): save_clip(wav, a, b, c["f"])
                ok = True
            else:
                print("batch split mismatch -> по одному")
        if not ok:
            for c in grp:
                pcm_to_wav(tts(G["style"] + " Прочитай: " + c["text"], VOICE), wav)
                save_clip(wav, 0, dur(wav), c["f"])
        for c in grp:
            done[c["f"]] = hashlib.md5((VOICE + c["text"]).encode()).hexdigest()[:10]
        made += len(grp); i += B
        json.dump(done, open(DONE_P, "w"))
        time.sleep(7)
except Limit as e:
    print("Gemini: зупинка (ліміт/помилка):", e)
json.dump(done, open(DONE_P, "w"))
print("Gemini: озвучено цього разу", made, "запитів", REQ["n"], "лишилось", len(clips) - made)
