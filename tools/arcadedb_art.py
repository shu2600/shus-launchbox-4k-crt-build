"""Fill Arcade art gaps from ArcadeDB (adb.arcadeitalia.net, free, looked up by MAME rom name).
For each LaunchBox Arcade game: no Box Front / Box 3D / Flyer Front -> ArcadeDB flyer into 'Advertisement Flyer - Front';
no Gameplay screenshot -> ArcadeDB ingame shot; no Marquee -> ArcadeDB marquee. Existing files are never overwritten.
Usage: py -I arcadedb_art.py [--dry] [--platform "Nintendo Game & Watch"]   (default Arcade)"""
import os, re, sys, glob, json, time, urllib.request
import xml.etree.ElementTree as E

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

LB = C.LB
PLAT = sys.argv[sys.argv.index("--platform") + 1] if "--platform" in sys.argv else "Arcade"
IMG = os.path.join(LB, "Images", PLAT)
API = "https://adb.arcadeitalia.net/service_scraper.php?ajax=query_mame&game_name="
UA = {"User-Agent": "lb-build/1.0 (personal LaunchBox setup)"}
DRY = "--dry" in sys.argv


def clean(t):
    return re.sub(r"[:/\?*\"<>|']", "_", t)


def has(kind, title):
    d = os.path.join(IMG, kind)
    return os.path.isdir(d) and bool(glob.glob(os.path.join(glob.escape(d), "**", glob.escape(clean(title)) + "-0*.*"), recursive=True))


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:
            err = e; time.sleep(2 + 3 * i)
    print("  fail", url[:100], err, flush=True)
    return None


def save(kind, title, data):
    ext = ".png" if data[:4] == b"\x89PNG" else ".jpg" if data[:2] == b"\xff\xd8" else None
    if not ext or len(data) < 2000:
        return False
    d = os.path.join(IMG, kind); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, clean(title) + "-01" + ext)
    if os.path.exists(p):
        return False
    open(p, "wb").write(data)
    return True


_xml = os.path.join(LB, "Data", "Platforms", PLAT + ".xml")
if not os.path.exists(_xml):
    print(f"{PLAT}: not in your LaunchBox library, nothing to do")
    sys.exit(0)
games = E.parse(_xml).getroot().findall("Game")
todo = {}
for g in games:
    t = g.findtext("Title") or ""; ap = g.findtext("ApplicationPath") or ""
    rom = os.path.splitext(os.path.basename(ap))[0].lower()
    if not rom or "://" in ap:
        continue
    need = []
    if not (has("Box - Front", t) or has("Box - 3D", t) or has("Advertisement Flyer - Front", t)):
        need.append(("url_image_flyer", "Advertisement Flyer - Front"))
    if not has("Screenshot - Gameplay", t):
        need.append(("url_image_ingame", "Screenshot - Gameplay"))
    if not has("Arcade - Marquee", t):
        need.append(("url_image_marquee", "Arcade - Marquee"))
    if need:
        todo.setdefault(rom, (t, need))
print(f"{len(todo)} games need something", flush=True)
if DRY:
    sys.exit()
roms = sorted(todo); got = {k: 0 for k in ("Advertisement Flyer - Front", "Screenshot - Gameplay", "Arcade - Marquee")}
for i in range(0, len(roms), 40):
    raw = get(API + ";".join(roms[i:i + 40]))
    if not raw:
        continue
    try:
        res = {r["game_name"]: r for r in json.loads(raw).get("result", [])}
    except ValueError:
        print("  bad json at", i, flush=True); continue
    for rom in roms[i:i + 40]:
        r = res.get(rom)
        if not r:
            continue
        title, need = todo[rom]
        for field, kind in need:
            u = r.get(field)
            if u:
                data = get(u)
                if data and save(kind, title, data):
                    got[kind] += 1
        time.sleep(0.3)
    print(f"  {min(i + 40, len(roms))}/{len(roms)} {got}", flush=True)
print("done", got)
