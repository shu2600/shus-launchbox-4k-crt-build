"""Mark your favourite games (the 'favourites' list in lb_settings.json) as LaunchBox favourites (Favorite=true). LaunchBox must be closed.
Titles are matched loosely (case, punctuation, 'The'), and a title that matches several games marks them all only
when listed with '*' (e.g. 'Super Star Wars*'). Prints what was marked and what was not found.
Usage: py -I fav_mark.py [--dry]"""
import os, re, sys, shutil, datetime
import xml.etree.ElementTree as ET

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

LB = C.LB
P = os.path.join(LB, "Data", "Platforms")
FAVS = C.FAVOURITES   # LaunchBox platform -> [titles], from lb_settings.json


def key(s):
    s = s.lower().replace("&", "and")
    s = re.sub(r"^the\s+|,\s*the$", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


dry = "--dry" in sys.argv
if not dry:
    shutil.copytree(os.path.join(LB, "Data"), _os.path.join(C.LOGS, rf"lb_data_backup_{datetime.datetime.now():%Y%m%d_%H%M%S}_fav"))
for plat, titles in FAVS.items():
    f = os.path.join(P, plat + ".xml")
    if not os.path.exists(f):
        print(f"{plat}: no platform file"); continue
    tree = ET.parse(f); games = tree.getroot().findall("Game")
    by = {}
    for g in games:
        by.setdefault(key(g.findtext("Title") or ""), []).append(g)
    marked, missing = [], []
    for t in titles:
        star = t.endswith("*"); k = key(t.rstrip("*"))
        hits = [g for kk, gs in by.items() for g in gs if (kk.startswith(k) if star else kk == k)]
        if not hits:
            missing.append(t); continue
        for g in hits:
            e = g.find("Favorite")
            if e is None:
                e = ET.SubElement(g, "Favorite")
            e.text = "true"; marked.append(g.findtext("Title"))
    if not dry and marked:
        ET.indent(tree.getroot(), space="  ")
        open(f, "w", encoding="utf-8").write('<?xml version="1.0" standalone="yes"?>\n' + ET.tostring(tree.getroot(), encoding="unicode") + "\n")
    print(f"{plat}: {len(marked)} marked" + (f"; not in library: {', '.join(missing)}" if missing else ""))
