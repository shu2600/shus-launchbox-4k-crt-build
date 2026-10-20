"""Work out which games from the PC's LaunchBox go to the Steam Deck (EmuDeck folders on the SD card).
Small cartridge systems go over whole; big disc systems get only the games in your playlists.
Writes deck_sync_list.json: [{"src": PC path, "dst": deck relative path, "size": bytes}]"""
import os, json, glob, xml.etree.ElementTree as ET

import os as _os, sys as _sys
_here = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:0] = [_here, _os.path.join(_here, "..", "lb_build")]   # lbconfig lives with the build tools
import lbconfig as C  # paths from lb_settings.json

LB = C.LB
FOLDER = {  # LaunchBox platform -> EmuDeck roms folder
    "Atari 2600": "atari2600", "Atari 5200": "atari5200", "Atari 7800": "atari7800", "Atari Jaguar": "atarijaguar",
    "Atari Lynx": "atarilynx", "Atari ST": "atarist", "ColecoVision": "colecovision", "Commodore Amiga": "amiga",
    "GCE Vectrex": "vectrex", "Mattel Intellivision": "intellivision", "NEC TurboGrafx-16": "tg16",
    "Nintendo 3DS": "3ds", "Nintendo 64": "n64", "Nintendo DS": "nds", "Nintendo GameCube": "gamecube",
    "Sony Playstation 2": "ps2", "Nintendo Switch": "switch", "SNK Neo Geo AES": "neogeo",
    "SNK Neo Geo Pocket Color": "ngpc", "Sega Genesis": "megadrive", "Super Nintendo Entertainment System": "snes",
    "Sinclair ZX Spectrum": "zxspectrum", "Sony PSP": "psp", "Arcade": "arcade",
}
WHOLE = {"Atari 2600", "Atari 5200", "Atari 7800", "Atari Jaguar", "Atari Lynx", "ColecoVision", "GCE Vectrex",
         "Mattel Intellivision", "NEC TurboGrafx-16", "SNK Neo Geo Pocket Color", "Sega Genesis",
         "Super Nintendo Entertainment System", "Nintendo DS", "Sinclair ZX Spectrum", "Commodore Amiga", "Atari ST", "Sony PSP"}

games = {}
for f in glob.glob(os.path.join(LB, "Data", "Platforms", "*.xml")):
    for g in ET.parse(f).getroot().findall("Game"):
        games[g.findtext("ID")] = (g.findtext("Platform"), g.findtext("ApplicationPath"), g.findtext("Title"))

picked = set()
for f in glob.glob(os.path.join(LB, "Data", "Playlists", "*.xml")):
    if "Windows" in f:
        continue
    for pg in ET.parse(f).getroot().findall("PlaylistGame"):
        if pg.findtext("GameId") in games:
            picked.add(pg.findtext("GameId"))
for gid, (plat, path, title) in games.items():
    if plat in WHOLE:
        picked.add(gid)


def files_for(path):
    out = [path]
    if path.lower().endswith(".m3u") and os.path.exists(path):
        d = os.path.dirname(path)
        for line in open(path, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(os.path.join(d, line))
    if path.lower().endswith(".bin") and os.path.basename(os.path.dirname(path)).upper() == "USRDIR":
        return []  # PS3 is not going to the Deck
    return out


items, missing = [], []
for gid in sorted(picked):
    plat, path, title = games[gid]
    if plat not in FOLDER or not path:
        continue
    if not os.path.isabs(path):
        path = os.path.normpath(os.path.join(LB, path))
    for p in files_for(path):
        if os.path.isfile(p):
            items.append({"src": p, "dst": FOLDER[plat] + "/" + os.path.basename(p), "size": os.path.getsize(p), "plat": plat})
        else:
            missing.append(p)

# arcade: add the BIOS/device sets the chosen games need (romof chain from MAME.xml is not stored, so take known BIOS zips)
MAME_ROMS = [_os.path.join(C.ROOT, r"Arcade\MAME 0.261 ROMs (non-merged)"), _os.path.join(C.MAME_DIR, "roms")]
for b in ["neogeo", "pgm", "cpzn1", "cpzn2", "naomi", "awbios", "stvbios", "skns", "decocass", "nss", "playch10", "megaplay",
          "qsound", "isgsm", "hng64", "konamigx", "atarisy1", "coh1000c", "coh1000t", "taitofx1", "tps", "sys573", "aleck64", "crysbios"]:
    for d in MAME_ROMS:
        p = os.path.join(d, b + ".zip")
        if os.path.isfile(p):
            items.append({"src": p, "dst": "arcade/" + b + ".zip", "size": os.path.getsize(p), "plat": "Arcade"})
            break

seen, uniq = set(), []
for it in items:
    if it["dst"].lower() not in seen:
        seen.add(it["dst"].lower())
        uniq.append(it)
json.dump(uniq, open(os.path.join(os.path.dirname(__file__), "deck_sync_list.json"), "w"), indent=0)
by = {}
for it in uniq:
    by.setdefault(it["plat"], [0, 0])
    by[it["plat"]][0] += 1
    by[it["plat"]][1] += it["size"]
for k, (n, s) in sorted(by.items(), key=lambda x: -x[1][1]):
    print(f"{s/1e9:8.2f} GB  {n:5d}  {k}")
print(f"TOTAL {sum(v[1] for v in by.values())/1e9:.1f} GB, {len(uniq)} files, {len(missing)} missing")
