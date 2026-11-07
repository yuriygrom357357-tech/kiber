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
 (r"ВКП 7-00\(03\)\.01", "ВКП сім, нуль нуль, нуль три, нуль один"), (r"ВКП 7-00\(01\)\.01", "ВКП сім, нуль нуль, нуль один, нуль один"),
 (r"КРП 03\.032\.056-2018", "КРП нуль три, нуль тридцять два, нуль п'ятдесят шість, дві тисячі вісімнадцять"),
 (r"\bЖБП\b", "же-бе-пе"), (r"\bВСК\b", "ве-ес-ка"), (r"\bКТЗ\b", "ка-те-зе"), (r"\bСТІ\b", "ес-те-і"), (r"\bНЦ\b", "ен-це"),
 (r"\bЦПСС\b", "це-пе-ес-ес"), (r"\bВКСС\b", "ве-ка-ес-ес"), (r"\bВВНЗ\b", "ве-ве-ен-зе"), (r"\bНМТБ\b", "ен-ем-те-бе"),
 (r"\bБЗВП\b", "бе-зе-ве-пе"), (r"\bМОУ\b", "Ем-О-У"), (r"\bГШ\b", "Ге-Ша"), (r"\bСП\b", "ес-пе"), (r"\bПІБ\b", "пе-і-бе"),
 (r"\bКІБР\b", "кі-бе-ер"), (r"\bІБР\b", "і-бе-ер"), (r"\bРПС\b", "ер-пе-ес"), (r"\bВОС\b", "ве-о-ес"), (r"\bSOP\b", "ес-о-пі"),
 (r"\bL-(\d)\b", r"ел \1"), (r"\bFPV\b", "еф-пі-ві"), (r"\bCQB\b", "сі-к'ю-бі"), (r"High Ready", "хай реді"), (r"Low Ready", "лоу реді"),
 (r"High Combat Ready", "хай комбат реді"), (r"Low Combat Ready", "лоу комбат реді"), (r"Combat Ready", "комбат реді"),
 (r"Patrol Carry", "патрол кері"), (r"\bSlinged\b", "слінгд"), (r"\bWorkspace\b", "воркспейс"), (r"№\s*", "номер "),
 (r"(\d)\s*–\s*(\d)", r"\1 до \2"), (r"(\d)°", r"\1 градусів"),
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

import hashlib
LETTERS = ["А", "Б", "В", "Г"]
def cid(text):
    return "q/" + hashlib.md5(("v1|" + text).encode()).hexdigest()[:12] + ".mp3"
def quiz_clips():
    """тексти кліпів для тестів; повертає (список кліпів, мапу на кожне питання)"""
    clips = {}
    def add(text):
        f = cid(text); clips[f] = text; return f
    for l in LETTERS: add(l + ".")
    add("Правильно."); add("Неправильно. Правильна відповідь:")
    qmap = {}
    for t in L:
        for i, (q, opts, ex) in enumerate(t["test"]):
            qmap[(t["id"], i)] = {"q": add(say(q)), "o": [add(say(o)) for o in opts], "e": add(say(ex))}
    return [{"f": f, "text": x} for f, x in clips.items()], qmap

def job():
    secs = []
    for t in L:
        for si, sec in enumerate(t["sections"]):
            secs.append({"f": "%s_%02d.mp3" % (t["id"], si), "blocks": blocks_of(sec, si)})
    clips, _ = quiz_clips()
    json.dump({"voice": "uk-UA-OstapNeural", "rate": "+0%", "sections": secs, "clips": clips}, open(os.path.join(ROOT, "tts", "job.json"), "w"), ensure_ascii=False, indent=1)
    print("sections", len(secs), "chars", sum(len(b[1]) for s in secs for b in s["blocks"]))

SITE = "https://yuriygrom357357-tech.github.io/kiber/"
def icons():
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(os.path.join(ROOT, "icons"), exist_ok=True)
    fp = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    import shutil
    brand = os.path.join(ROOT, "src", "brand")
    if os.path.exists(os.path.join(brand, "emblem.png")):
        shutil.copy(os.path.join(brand, "emblem.png"), os.path.join(ROOT, "icons", "emblem.png"))
    for name, sz in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
        if os.path.exists(os.path.join(brand, name)):
            shutil.copy(os.path.join(brand, name), os.path.join(ROOT, "icons", name)); continue
        S = 4; W = sz * S
        im = Image.new("RGB", (W, W), "#10130D"); d = ImageDraw.Draw(im)
        u = W / 36.0
        P = lambda pts: [(x * u, y * u) for x, y in pts]
        import math
        shield = [(18, 4), (30.5, 8.4)] + [(30.5, 8.4 + k * 0.9) for k in range(1, 10)]
        # контур щита
        pts = [(18, 4.5), (30, 8.6), (30, 17)]
        for k in range(1, 21):
            t = k / 20; pts.append((30 - 12 * t, 17 + 14.2 * math.sin(t * math.pi / 2)))
        for k in range(1, 21):
            t = k / 20; pts.append((18 - 12 * t, 31.2 - 14.2 * (1 - math.cos(t * math.pi / 2))))
        pts += [(6, 8.6)]
        d.polygon(P(pts), fill="#1B2116", outline="#F2A33A", width=int(1.6 * u))
        c = (18 * u, 17.6 * u); r = 6.2 * u
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline="#F2A33A", width=int(1.7 * u))
        for (x1, y1, x2, y2) in [(18, 8.5, 18, 13), (18, 22.2, 18, 26.7), (8.9, 17.6, 13.4, 17.6), (22.6, 17.6, 27.1, 17.6)]:
            d.line(P([(x1, y1), (x2, y2)]), fill="#F2A33A", width=int(1.7 * u))
        rr = 1.6 * u; d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr], fill="#F2A33A")
        im = im.resize((sz, sz), Image.LANCZOS)
        im.save(os.path.join(ROOT, "icons", name))
    man = {"name": "КІБЕР · Курс інструктора базового рівня · 158 навчальний центр", "short_name": "КІБЕР",
      "description": "Курс інструктора базового рівня: лекції з озвучкою, тести, оціночний лист, тренажери. Працює офлайн.",
      "start_url": "./", "scope": "./", "display": "standalone", "orientation": "any", "lang": "uk", "background_color": "#10130D", "theme_color": "#10130D",
      "icons": [{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"}, {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"}, {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}
    json.dump(man, open(os.path.join(ROOT, "manifest.webmanifest"), "w"), ensure_ascii=False, indent=1)

def build_html():
    icons()
    tm = json.load(open(os.path.join(ROOT, "tts", "timing.json")))
    TIMING = {}
    for t in L:
        arr = []
        for si, _ in enumerate(t["sections"]):
            f = "%s_%02d.mp3" % (t["id"], si)
            x = tm.get(f)
            arr.append({"f": f, "d": x["d"], "m": x["m"]} if x else {"f": f, "d": 0, "m": []})
        TIMING[t["id"]] = arr
    clips, qmap = quiz_clips()
    have = lambda f: os.path.exists(os.path.join(ROOT, "audio", f))
    topics = []
    for t in L:
        t2 = dict(t); t2["test"] = []
        for i, item in enumerate(t["test"]):
            m = qmap[(t["id"], i)]
            ok = have(m["q"]) and all(have(x) for x in m["o"]) and have(m["e"])
            t2["test"].append(list(item) + ([m] if ok else []))
        topics.append(t2)
    QA = {"letters": [cid(l + ".") for l in LETTERS], "right": cid("Правильно."), "wrong": cid("Неправильно. Правильна відповідь:")}
    data = {"topics": topics, "course": COURSE, "sheets": SHEETS, "qa": QA if have(QA["right"]) else None}
    tpl = open(os.path.join(ROOT, "src", "app.html")).read()
    files = ["index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png", "vendor/html2pdf.bundle.min.js", "vendor/docx.min.js", "icons/emblem.png"] + ["fonts/" + f for f in sorted(os.listdir(os.path.join(ROOT, "fonts")))]
    audio = []
    for t in L:
        for x in TIMING[t["id"]]: audio.append("audio/" + x["f"])
    audio += ["audio/" + c["f"] for c in clips if have(c["f"])]
    out = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False)).replace("/*TIMING*/null", json.dumps(TIMING, ensure_ascii=False))
    ver = "kb-" + str(abs(hash(out)) % 10**6)
    sizes = lambda lst: [[p, os.path.getsize(os.path.join(ROOT, p)) if os.path.exists(os.path.join(ROOT, p)) else 0] for p in lst]
    assets = sizes(files[1:] + audio)
    out = out.replace("/*CACHE*/\"kb\"", json.dumps(ver))
    idx_size = len(out.encode()) + 4000
    assets = [["./", idx_size], ["index.html", idx_size]] + assets
    out = out.replace("/*ASSETS*/null", json.dumps(assets, ensure_ascii=False))
    import segno, io
    q = segno.make(SITE, error="m"); buf = io.BytesIO(); q.save(buf, kind="svg", scale=1, border=1, dark="#0B1422", light="#FFFFFF", xmldecl=False, svgns=True, nl=False)
    n = q.symbol_size(scale=1, border=1)[0]
    svg = re.sub(r'width="\d+" height="\d+"', 'viewBox="0 0 %d %d"' % (n, n), buf.getvalue().decode(), count=1)
    out = out.replace("/*QR*/", svg)
    import base64, io
    from PIL import Image as _I
    _b = io.BytesIO(); _I.open(os.path.join(ROOT, "src", "brand", "emblem.png")).resize((160, 160), _I.LANCZOS).save(_b, "PNG", optimize=True)
    out = out.replace('"/*EMBLEM*/"', json.dumps("data:image/png;base64," + base64.b64encode(_b.getvalue()).decode()))
    open(os.path.join(ROOT, "index.html"), "w").write(out)
    sw = open(os.path.join(ROOT, "src", "sw.js")).read().replace("__CACHE__", ver).replace("__SHELL__", json.dumps(["./"] + files))
    open(os.path.join(ROOT, "sw.js"), "w").write(sw)
    print("index.html", len(out), "audio files", len(audio), "cache", ver)

if __name__ == "__main__":
    {"job": job, "html": build_html}[sys.argv[1]]()
