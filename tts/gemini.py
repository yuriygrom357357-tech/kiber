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

MODELS = G.get("models") or [G["model"]]
try:
    _ml = json.loads(urllib.request.urlopen(urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers={"x-goog-api-key": KEY}), timeout=60).read())
    for m in _ml.get("models", []):
        n = m["name"].split("/")[-1]
        if "tts" in n and n not in MODELS: MODELS.append(n)
except Exception as e:
    print("models list failed", e)
print("Gemini моделі:", MODELS)
MI = {"i": 0}
def tts(text, voice):
    while True:
        if MI["i"] >= len(MODELS): raise Limit("усі моделі вичерпали денний ліміт")
        try:
            return tts_model(text, voice, MODELS[MI["i"]])
        except Limit as e:
            if str(e) in ("429", "404"):
                print("модель", MODELS[MI["i"]], "недоступна/ліміт -> наступна"); MI["i"] += 1; continue
            raise

def tts_model(text, voice, model):
    if REQ["n"] >= G.get("max_requests", 90): raise Limit("max_requests")
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    for attempt in range(3):
        gap = time.time() - REQ.get("t", 0)
        if gap < 21: time.sleep(21 - gap)   # безкоштовний ліміт ~3 запити на хвилину
        REQ["t"] = time.time()
        REQ["n"] += 1
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            for p in d["candidates"][0]["content"]["parts"]:
                if "inlineData" in p: return base64.b64decode(p["inlineData"]["data"])
            raise RuntimeError("no audio")
        except urllib.error.HTTPError as e:
            msg = e.read()[:400].decode("utf-8", "ignore"); print("Gemini HTTP", model, e.code, msg[:300])
            if e.code == 429:
                if "PerDay" in msg or "per day" in msg.lower() or "free_tier_requests" in msg or attempt >= 1: raise Limit("429")
                time.sleep(65); continue
            if e.code == 404: raise Limit("404")
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
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", wav, "-af", "silencedetect=n=-38dB:d=0.3", "-f", "null", "-"], capture_output=True, text=True).stderr
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
    if any(b - a < 0.35 for a, b in cuts): return None
    return cuts

def save_clip(wav, a, b, f):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-ss", "%.3f" % a, "-to", "%.3f" % b, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                    "-ac", "1", "-ar", "24000", "-b:a", "48k", "audio/" + f], check=True)

def batch_prompt(texts):
    lines = "\n\n".join(texts)
    return (G["style"] + " Прочитай по черзі кожен з наведених нижче фрагментів. Після кожного фрагмента обов’язково роби довгу паузу — три секунди тиші. "
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

# ---------- Лекції: розділи, які не озвучує ElevenLabs ----------
EL = json.load(open("tts/eleven.json")) if os.path.exists("tts/eleven.json") else {}
EL_LESSONS = set(EL.get("lessons", [])); EL_SECTIONS = set(EL.get("sections", []))
TIM_P = "tts/timing.json"
timing = json.load(open(TIM_P)) if os.path.exists(TIM_P) else {}
def bhash(blocks): return hashlib.md5(json.dumps(blocks, ensure_ascii=False).encode()).hexdigest()[:12]
lect_todo = [s for s in job["sections"] if s["f"].split("_")[0] not in EL_LESSONS and s["f"] not in EL_SECTIONS and timing.get(s["f"], {}).get("g") != bhash(s["blocks"])]
print("Gemini: розділів лекцій до озвучки", len(lect_todo))
lect_made = 0
try:
    for sec in lect_todo:
        texts = [t for _, t in sec["blocks"]]
        prompt = (G.get("lecture_style", G["style"]) + " Прочитай текст лекції повністю, дослівно, нічого не пропускаючи і не додаючи. "
                  "Між абзацами роби паузу приблизно одну секунду.\n\n" + "\n\n".join(texts))
        wav = "tts/cache/glect.wav"
        nchar = sum(len(t) for t in texts)
        okaudio = False
        for attempt in range(2):
            pcm_to_wav(tts(prompt, VOICE), wav + ".raw.wav")
            # стиснути задовгі паузи і прибрати тишу в кінці
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav + ".raw.wav", "-af",
                "silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=1.1:stop_threshold=-45dB:stop_silence=0.6", wav], check=True)
            rate = nchar / max(dur(wav), 0.1)
            if 7.0 <= rate <= 17.0: okaudio = True; break
            print("брак озвучки", sec["f"], "символів/с", round(rate, 1), "— повтор")
        if not okaudio:
            print("пропускаю розділ (неякісна генерація)", sec["f"]); continue
        total = dur(wav)
        cuts = split_by_silence(wav, len(texts)) if len(texts) > 1 else [(0, total)]
        if cuts:
            starts = [max(0.0, round(c[0], 2)) for c in cuts]
        else:
            L = [max(1, len(t)) for t in texts]; acc, starts = 0, []
            for l in L: starts.append(round(total * acc / sum(L), 2)); acc += l
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-ac", "1", "-ar", "24000", "-b:a", "64k", "audio/" + sec["f"]], check=True)
        d = dur("audio/" + sec["f"])
        timing[sec["f"]] = {"d": round(d, 1), "m": [[bid, st] for (bid, _), st in zip(sec["blocks"], starts)], "k": "g-" + bhash(sec["blocks"]), "g": bhash(sec["blocks"])}
        json.dump(timing, open(TIM_P, "w"), ensure_ascii=False)
        lect_made += 1; print("lecture ok", sec["f"], round(d, 1), "split" if cuts else "proportional")
except Limit as e:
    print("Gemini: лекції — зупинка:", e)
    json.dump(timing, open(TIM_P, "w"), ensure_ascii=False)
    print("Gemini: розділів озвучено", lect_made); sys.exit(0)
print("Gemini: розділів озвучено", lect_made)

# ---------- Тести ----------
clips = [c for c in job.get("clips", []) if done.get(c["f"]) != hashlib.md5((VOICE + c["text"]).encode()).hexdigest()[:10]]
print("Gemini: кліпів до озвучки", len(clips), "голос", VOICE)
B = G.get("batch", 10)
made = 0
def do_group(grp):
    wav = "tts/cache/gbatch.wav"
    if len(grp) == 1:
        c = grp[0]
        pcm_to_wav(tts(G["style"] + " Прочитай: " + c["text"], VOICE), wav)
        save_clip(wav, 0, dur(wav), c["f"]); return
    pcm_to_wav(tts(batch_prompt([c["text"] for c in grp]), VOICE), wav)
    cuts = split_by_silence(wav, len(grp))
    if cuts:
        for c, (x, y) in zip(grp, cuts): save_clip(wav, x, y, c["f"])
        return
    print("batch split mismatch (%d) -> ділю навпіл" % len(grp))
    if len(grp) >= 20:
        os.makedirs("tts/debug", exist_ok=True); import shutil
        shutil.copy(wav, "tts/debug/batch_%d.wav" % len(grp))
        json.dump([c["text"] for c in grp], open("tts/debug/batch_%d.json" % len(grp), "w"), ensure_ascii=False)
    h = len(grp) // 2
    do_group(grp[:h]); do_group(grp[h:])
try:
    i = 0
    while i < len(clips):
        grp = clips[i:i + B]
        do_group(grp)
        for c in grp:
            done[c["f"]] = hashlib.md5((VOICE + c["text"]).encode()).hexdigest()[:10]
        made += len(grp); i += B
        json.dump(done, open(DONE_P, "w"))
except Limit as e:
    print("Gemini: зупинка (ліміт/помилка):", e)
json.dump(done, open(DONE_P, "w"))
print("Gemini: озвучено цього разу", made, "запитів", REQ["n"], "лишилось", len(clips) - made)
