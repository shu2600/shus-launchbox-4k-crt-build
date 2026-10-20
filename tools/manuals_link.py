"""Match manuals from the retrokit-manuals packs (archive.org) to your LaunchBox games and link them.
Each matched PDF goes to LaunchBox\\Manuals\\<Platform>\\<title>.pdf (English preferred) and the game gets <ManualPath>.
lb_build.py picks the same files up on any rebuild. LaunchBox must be closed.
Usage: py -I manuals_link.py <pack-key> [...]   e.g. atari2600 atari7800"""
import os, re, sys, zipfile, shutil, xml.etree.ElementTree as ET
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

args = sys.argv[1:]; sys.argv = [sys.argv[0]]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lb_build import compare, clean_name, LB, DATA, write_xml

SRC = _os.path.join(C.ROOT, r"Manuals\_src")
PLAT = {"atari2600": "Atari 2600", "atari5200": "Atari 5200", "atari7800": "Atari 7800", "atarijaguar": "Atari Jaguar",
        "atarilynx": "Atari Lynx", "vectrex": "GCE Vectrex"}
LANG = ["en", "en-gb", "en-us"]


def safe(t):
    return re.sub(r"[:/\\?*\"<>|']", "_", t)


for key in args:
    plat = PLAT[key]
    z = zipfile.ZipFile(os.path.join(SRC, f"{key}-compressed.zip"))
    best = {}
    for n in z.namelist():
        if not n.lower().endswith(".pdf"):
            continue
        base = os.path.basename(n)
        langs = re.findall(r"\(([a-z]{2}(?:-[a-z]{2})?(?:,[a-z]{2}(?:-[a-z]{2})?)*)\)", base)
        rank = 0 if any(l in LANG for x in langs for l in x.split(",")) else 1
        k = compare(clean_name(base))
        if k not in best or rank < best[k][0]:
            best[k] = (rank, n)
    xmlp = os.path.join(DATA, "Platforms", plat + ".xml")
    root = ET.parse(xmlp).getroot()
    outdir = os.path.join(LB, "Manuals", plat); os.makedirs(outdir, exist_ok=True)
    linked = 0
    for g in root.findall("Game"):
        t = g.findtext("Title", "")
        hit = best.get(compare(t))
        if not hit:
            continue
        dst = os.path.join(outdir, safe(t) + ".pdf")
        if not os.path.exists(dst):
            with z.open(hit[1]) as s, open(dst, "wb") as d:
                shutil.copyfileobj(s, d)
        mp = g.find("ManualPath")
        if mp is None:
            mp = ET.SubElement(g, "ManualPath")
        mp.text = dst
        linked += 1
    write_xml(root, xmlp)
    print(f"{plat}: {len(best)} manuals in pack, {linked} of {len(root.findall('Game'))} games linked", flush=True)
