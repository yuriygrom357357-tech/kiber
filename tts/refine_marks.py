# Уточнює позначки підсвічування: кожен абзац починається там, де в аудіо справді починається мова
# (після паузи), а не на початку паузи. Працює по готових mp3, тож підходить для будь-якого голосу.
import json, subprocess, sys, os
def silences(path):
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-af", "silencedetect=n=-38dB:d=0.12", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return [float(l.split("silence_end: ")[1].split()[0]) for l in out.splitlines() if "silence_end" in l]
def refine(path, marks):
    ends = silences(path); res = []
    for i, (bid, t) in enumerate(marks):
        if i == 0: res.append([bid, t]); continue
        c = [e for e in ends if t - 0.15 <= e <= t + 0.9]
        res.append([bid, round(c[0] - 0.04, 2) if c else t])
    # порядок має лишатися зростаючим
    for i in range(1, len(res)):
        if res[i][1] < res[i - 1][1]: res[i][1] = res[i - 1][1]
    return res
if __name__ == "__main__":
    T = json.load(open("tts/timing.json")); n = 0
    for f, v in T.items():
        p = "audio/" + f
        if v.get("m") and os.path.exists(p) and not v.get("r"):
            v["m"] = refine(p, v["m"]); v["r"] = 1; n += 1
    json.dump(T, open("tts/timing.json", "w"), ensure_ascii=False); print("refined", n)
