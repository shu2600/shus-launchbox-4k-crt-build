"""Check LaunchBox's Data folder the way LaunchBox will read it, without opening LaunchBox:
every XML parses, game IDs are unique, every game's emulator exists, every platform in Platforms.xml has a category,
playlist entries point at real games, and manual paths exist. Usage: py -I lb_validate.py"""
import os, glob, collections
import xml.etree.ElementTree as ET

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

DATA = os.path.join(C.LB, "Data")
problems = []
emus = {e.findtext("ID") for e in ET.parse(os.path.join(DATA, "Emulators.xml")).getroot().findall("Emulator")}
plats_xml = ET.parse(os.path.join(DATA, "Platforms.xml")).getroot()
plat_names = {p.findtext("Name") for p in plats_xml.findall("Platform")}
parents = ET.parse(os.path.join(DATA, "Parents.xml")).getroot()
parented = {x.findtext("PlatformName") for x in parents.findall("Parent") if x.findtext("PlatformName")}
ids = collections.Counter()
games = 0
for f in glob.glob(os.path.join(DATA, "Platforms", "*.xml")):
    try:
        root = ET.parse(f).getroot()
    except ET.ParseError as e:
        problems.append(f"does not parse: {os.path.basename(f)}: {e}"); continue
    plat = os.path.basename(f)[:-4]
    if root.findall("Game") and plat not in plat_names:
        problems.append(f"{plat}: has games but is not in Platforms.xml")
    if plat in plat_names and plat not in parented:
        problems.append(f"{plat}: no category in Parents.xml")
    for g in root.findall("Game"):
        games += 1
        ids[g.findtext("ID")] += 1
        e = g.findtext("Emulator")
        ap = g.findtext("ApplicationPath") or ""
        if e and e not in emus:
            problems.append(f"{plat}: {g.findtext('Title')}: emulator id not in Emulators.xml")
        man = g.findtext("ManualPath")
        if man and not os.path.exists(man if os.path.isabs(man) else os.path.join(C.LB, man)):
            problems.append(f"{plat}: {g.findtext('Title')}: manual missing {man}")
dupes = [i for i, n in ids.items() if n > 1]
if dupes:
    problems.append(f"{len(dupes)} game IDs used more than once")
dangling = 0
for f in glob.glob(os.path.join(DATA, "Playlists", "*.xml")):
    try:
        for pg in ET.parse(f).getroot().findall("PlaylistGame"):
            if pg.findtext("GameId") not in ids:
                dangling += 1
    except ET.ParseError as e:
        problems.append(f"playlist does not parse: {os.path.basename(f)}: {e}")
if dangling:
    problems.append(f"{dangling} playlist entries point at games that no longer exist")
print(f"{games} games, {len(plat_names)} platforms, {len(emus)} emulators checked")
print("\n".join(problems[:50]) if problems else "no problems found")
