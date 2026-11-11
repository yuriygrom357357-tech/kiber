# Зразки безкоштовних голосів без ключів: Piper (відкриті українські моделі) і Microsoft Edge.
import json, os, subprocess, urllib.request, asyncio
TXT = "Інструктор особисто доводить заходи безпеки перед кожним заняттям. Яке положення зброї використовують під час бойового наказу? Правильно. За спиною."
os.makedirs("tts/samples", exist_ok=True)
base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/"
for name in ["ukrainian_tts/medium/uk_UA-ukrainian_tts-medium", "lada/x_low/uk_UA-lada-x_low"]:
    fn = name.split("/")[-1]
    for ext in (".onnx", ".onnx.json"):
        if not os.path.exists(fn + ext): urllib.request.urlretrieve(base + name + ext, fn + ext)
    cfg = json.load(open(fn + ".onnx.json"))
    spk = cfg.get("speaker_id_map") or {"": 0}
    print(fn, spk)
    for s, sid in spk.items():
        out = "tts/samples/piper_%s%s.wav" % (fn.split("-")[1], ("_" + s) if s else "")
        args = ["piper", "--model", fn + ".onnx", "--output_file", out] + (["--speaker", str(sid)] if s else [])
        subprocess.run(args, input=TXT.encode(), check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", out, "-b:a", "96k", out[:-4] + ".mp3"], check=True); os.remove(out)
import edge_tts
async def e():
    for v in ["uk-UA-OstapNeural"]:
        await edge_tts.Communicate(TXT, v).save("tts/samples/edge_%s.mp3" % v)
asyncio.run(e())
print(os.listdir("tts/samples"))
