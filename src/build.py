# Збирання «Кібер»: python3 src/build.py job  -> tts/job.json (тексти для озвучки)
#                   python3 src/build.py html -> index.html, sw.js, manifest
import json, os, re, sys, html as H
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from lessons import L, COURSE
SHEETS = json.load(open(os.path.join(ROOT, "src", "sheets.json")))

# ---------- текст для озвучки ----------
SAY = [
 (r"\bExplanation\b", "Експлейнейшн"), (r"\bDemonstration\b", "Демонстрейшн"), (r"\bImitation\b", "Імітейшн"),
 (r"\bPractice\b", "Практис"), (r"\bPractise\b", "Практис"), (r"\bExplain\b", "Експлейн"), (r"\bDemonstrate\b", "Демонстрейт"),
 (r"\bImitate\b", "Імітейт"), (r"After[- ]Action Reviews?", "Афтер екшн рев'ю"), (r"\bhasty AAR\b", "хейсті Ей-Ей-Ар"),
 (r"\bAAR\b", "Ей-Ей-Ар"), (r"\bEDIP\b", "ЕДІП"), (r"АПД", "А-П-Д"), (r"\bOPFOR\b", "опфор"), (r"\bSTANAG\b", "станаг"),
 (r"ADP 7-0, ADRP 7-0, FM 7-0", "Ей-Ді-Пі сім-нуль, Ей-Ді-Ар-Пі сім-нуль і Еф-Ем сім-нуль"),
 (r"TC 25-20 «A Leader’s Guide to After-Action Reviews»", "Ті-Сі двадцять п'ять — двадцять, «Посібник лідера з аналізу проведених дій»"),
 (r"\bAJP-3\b", "Ей-Джей-Пі три"), (r"ВП 7\(3\)-00\(01\)\.01", "ВП сім три, нуль нуль, нуль один, нуль один"),
 (r"«Aim – Outcome – Lessons – Actions»", "«Ейм — Аутком — Лессонз — Екшнз», тобто мета, результат, уроки, дії"),
 (r"\bТТХ\b", "тактико-технічні характеристики"), (r"АК-74", "АК сімдесят чотири"), (r"\bЗСУ\b", "Зе-Ес-У"), (r"\bПЗ\b", "практичне заняття"),
 (r"\bБпЛА\b", "бе-пе-ел-а"), (r"±2 см", "плюс-мінус два сантиметри"), (r"\bвід’єднує\b", "від'єднує"),
 (r" = ", " це "), (r"→", ", далі "), (r"—", ", "), (r"–", ", "), (r"\bс\.\b", ""),
]
def say(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = H.unescape(s)
    for a, b in SAY: s = re.sub(a, b, s)
    s = re.sub(r"\s+,", ",", s); s = re.sub(r",\s*,", ",", s)
    return re.sub(r"\s+", " ", s).strip()

def blocks_of(sec, si):
    out = [["s%dh" % si, say(sec["h"]) + "."]]
    for bi, (k, v) in enumerate(sec["body"]):
        if k == "ul":
            for li, it in enumerate(v): out.append(["s%db%di%d" % (si, bi, li), say(it)])
        else:
            pre = "Ключова думка. " if k == "key" else ("Важливо. " if k == "warn" else "")
            out.append(["s%db%d" % (si, bi), pre + say(v)])
    return out

def job():
    secs = []
    for t in L:
        for si, sec in enumerate(t["sections"]):
            secs.append({"f": "%s_%02d.mp3" % (t["id"], si), "blocks": blocks_of(sec, si)})
    json.dump({"voice": "uk-UA-OstapNeural", "rate": "+0%", "sections": secs}, open(os.path.join(ROOT, "tts", "job.json"), "w"), ensure_ascii=False, indent=1)
    print("sections", len(secs), "chars", sum(len(b[1]) for s in secs for b in s["blocks"]))

def build_html():
    tm = json.load(open(os.path.join(ROOT, "tts", "timing.json")))
    TIMING = {}
    for t in L:
        arr = []
        for si, _ in enumerate(t["sections"]):
            f = "%s_%02d.mp3" % (t["id"], si)
            x = tm.get(f)
            arr.append({"f": f, "d": x["d"], "m": x["m"]} if x else {"f": f, "d": 0, "m": []})
        TIMING[t["id"]] = arr
    data = {"topics": L, "course": COURSE, "sheets": SHEETS}
    tpl = open(os.path.join(ROOT, "src", "app.html")).read()
    files = ["index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"] + ["fonts/" + f for f in sorted(os.listdir(os.path.join(ROOT, "fonts")))]
    audio = []
    for t in L:
        for x in TIMING[t["id"]]: audio.append("audio/" + x["f"])
    out = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False)).replace("/*TIMING*/null", json.dumps(TIMING, ensure_ascii=False))
    ver = "kb-" + str(abs(hash(out)) % 10**6)
    sizes = lambda lst: [[p, os.path.getsize(os.path.join(ROOT, p)) if os.path.exists(os.path.join(ROOT, p)) else 0] for p in lst]
    assets = sizes(files[1:] + audio)
    out = out.replace("/*CACHE*/\"kb\"", json.dumps(ver))
    idx_size = len(out.encode()) + 4000
    assets = [["./", idx_size], ["index.html", idx_size]] + assets
    out = out.replace("/*ASSETS*/null", json.dumps(assets, ensure_ascii=False))
    open(os.path.join(ROOT, "index.html"), "w").write(out)
    sw = open(os.path.join(ROOT, "src", "sw.js")).read().replace("__CACHE__", ver).replace("__SHELL__", json.dumps(["./"] + files))
    open(os.path.join(ROOT, "sw.js"), "w").write(sw)
    print("index.html", len(out), "audio files", len(audio), "cache", ver)

if __name__ == "__main__":
    {"job": job, "html": build_html}[sys.argv[1]]()
