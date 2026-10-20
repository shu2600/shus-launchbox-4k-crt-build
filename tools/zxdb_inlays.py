"""Fill ZX Spectrum art gaps from ZXDB (Spectrum Computing's open database, github.com/zxdb/ZXDB).
Reads entries + downloads from the SQL dump, matches LaunchBox titles that still have no image of that kind,
and fetches it from spectrumcomputing.co.uk politely (one at a time, short pause).
  --kind front    Inlay - Front   -> Box - Front (default)
  --kind loading  Loading screen  -> Screenshot - Game Title
  --kind running  Running screen  -> Screenshot - Gameplay
Usage: py -I zxdb_inlays.py [--kind front|loading|running] [--dry] [--limit N]"""
import os, re, sys, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

args = list(sys.argv); sys.argv = [sys.argv[0]]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lb_build import compare, LB

SQL = _os.path.join(C.WORK, r"zxdb\ZXDB_mysql.sql")
KINDS = {"front": ("5", "Box - Front"), "loading": ("1", "Screenshot - Game Title"), "running": ("2", "Screenshot - Gameplay")}
KIND = args[args.index("--kind") + 1] if "--kind" in args else "front"
FILETYPE, MEDIA = KINDS[KIND]
IMG = os.path.join(LB, "Images", "Sinclair ZX Spectrum", MEDIA)
os.makedirs(IMG, exist_ok=True)
BASE = "https://spectrumcomputing.co.uk"
DRY = "--dry" in args
LIMIT = int(args[args.index("--limit") + 1]) if "--limit" in args else 10**9
TUP = re.compile(r"\((.*?)\)(?:,|;)\s*$")


def fields(s):
    out, cur, q, i = [], "", False, 0
    while i < len(s):
        ch = s[i]
        if q:
            if ch == "\\": cur += s[i + 1]; i += 2; continue
            if ch == "'": q = False
            else: cur += ch
        elif ch == "'": q = True
        elif ch == ",": out.append(cur.strip()); cur = ""
        else: cur += ch
        i += 1
    out.append(cur.strip())
    return out


titles, inlays, table = {}, {}, None
for line in open(SQL, encoding="utf-8", errors="replace"):
    if line.startswith("INSERT INTO `"):
        table = line.split("`")[1]; continue
    if table not in ("entries", "downloads", "aliases"):
        continue
    m = TUP.match(line.strip())
    if not m:
        if not line.startswith("\t"): table = None
        continue
    f = fields(m.group(1))
    if table == "entries":
        titles.setdefault(compare(f[1]), int(f[0]))
    elif table == "aliases":
        titles.setdefault(compare(f[3] if len(f) > 3 else f[-1]), int(f[0]))
    elif table == "downloads" and f[7] == FILETYPE and os.path.splitext(f[3])[1].lower() in (".png", ".jpg", ".jpeg", ".gif", ".scr"):
        prev = inlays.get(int(f[1]))
        if prev is None or (prev.lower().endswith(".scr") and not f[3].lower().endswith(".scr")):
            inlays[int(f[1])] = f[3]   # prefer a ready-made picture; raw .scr screens are converted below

safe = lambda t: re.sub(r"[:/\\?*\"<>|']", "_", t)
have = {re.sub(r"-\d\d$", "", os.path.splitext(x)[0]).lower() for dp, _d, fs in os.walk(IMG) for x in fs}
games = ET.parse(os.path.join(LB, r"Data\Platforms\Sinclair ZX Spectrum.xml")).getroot().findall("Game")
todo = []
for g in games:
    t = g.findtext("Title", "")
    if safe(t).lower() in have: continue
    eid = titles.get(compare(t))
    if eid and eid in inlays:
        todo.append((t, inlays[eid])); have.add(safe(t).lower())
print(f"ZXDB: {len(titles)} titles, {len(inlays)} entries with a {MEDIA} image; {len(todo)} of our missing games matched", flush=True)
def scr_to_png(data, dst, scale=2):
    """ZX Spectrum screen dump (6912 bytes: interleaved 256x192 bitmap + 32x24 colour attributes) -> PNG."""
    from PIL import Image
    pal = [(0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215), (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215)]
    bright = [(0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0), (255, 255, 255)]
    img = Image.new("RGB", (256, 192)); px = img.load()
    for y in range(192):
        row = ((y & 0xC0) << 5) | ((y & 0x07) << 8) | ((y & 0x38) << 2)   # the Spectrum's interleaved screen address
        for cx in range(32):
            bits = data[row + cx]
            a = data[6144 + (y // 8) * 32 + cx]
            p = bright if a & 0x40 else pal
            ink, paper = p[a & 7], p[(a >> 3) & 7]
            for b in range(8):
                px[cx * 8 + b, y] = ink if bits & (0x80 >> b) else paper
    img.resize((256 * scale, 192 * scale), Image.NEAREST).save(dst)


got = 0
for t, link in todo[:LIMIT]:
    if DRY: continue
    ext = os.path.splitext(link)[1].lower() or ".jpg"
    dst = os.path.join(IMG, re.sub(r"[:/\\?*\"<>|']", "_", t) + "-01" + (".png" if ext == ".scr" else ext))
    try:
        req = urllib.request.Request(BASE + urllib.parse.quote(link), headers={"User-Agent": "LaunchBoxBuild/1.0 (collection art)"})
        data = urllib.request.urlopen(req, timeout=30).read()
        if ext == ".scr":
            if len(data) < 6912:
                continue
            scr_to_png(data, dst)
        else:
            open(dst, "wb").write(data)
        got += 1
    except Exception as e:
        print(f"  {t}: {e}", flush=True)
    time.sleep(0.5)
print(f"downloaded {got}{' (dry run)' if DRY else ''}")
