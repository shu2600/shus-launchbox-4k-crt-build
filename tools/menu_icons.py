"""Give every LaunchBox menu entry (platform, category, playlist) an icon from the installed icon pack, reusing the
nearest existing icon: 'Best of <system>' = that system's icon, genres = the pack's genre icon. Never overwrites.
Usage: py -I menu_icons.py [--dry]"""
import os, sys, glob, shutil
import xml.etree.ElementTree as ET

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C

PACK = os.path.join(C.LB, "Images", "Media Packs", "Platform Icons", "Nostalgic Platform Icons")
LOGO_PACK = os.path.join(C.LB, "Images", "Media Packs", "Platform Clear Logos", "Nostalgic Platform Clear Logos")
fname = lambda n: n.replace("'", "_").replace(":", "_").replace("/", "_") + ".png"
PLATFORM_ALIAS = {"NEC TurboGrafx-16": "NEC TurboGrafx 16", "Visual Pinball X": "Pinball"}
PLAYLIST_FROM = {   # playlist -> (pack folder, icon name)
    "Beat 'em Ups": ("Playlists", "Beat Em Ups"), "Boxing": ("Playlists", "Sports Games"),
    "Football": ("Playlists", "Sports Games"), "Driving (Arcade)": ("Playlists", "Racing Games"),
    "Lightgun Games": ("Playlists", "Light Gun Games"), "Platformers": ("Playlists", "Platform Games"),
    "Pinball": ("Playlists", "Pinball Arcade"), "Top 100 of All Time": ("Playlists", "All Games"),
    "Amiga Classics": ("Platforms", "Commodore Amiga"), "Speccy Classics": ("Platforms", "Sinclair ZX Spectrum"),
    "Racing": ("Playlists", "Racing Games"), "Fighting Games": ("Playlists", "Fighting Games"),
}
CATEGORY_FROM = {"Best of Each System": ("Playlists", "Favorites"), "Collections": ("Playlists", "All Games")}
DRY = "--dry" in sys.argv
made = []


def give(kind, name, src_folder, src_name):
    for pack in (PACK, LOGO_PACK):
        dst = os.path.join(pack, kind, fname(name))
        src = os.path.join(pack, src_folder, fname(src_name))
        if os.path.exists(dst) or not os.path.exists(src):
            continue
        if not DRY:
            os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)
        made.append(f"{kind}/{name} <- {src_folder}/{src_name}" + ("" if pack == PACK else " (logo)"))


D = os.path.join(C.LB, "Data")
P = ET.parse(os.path.join(D, "Platforms.xml")).getroot()
for p in P.findall("Platform"):
    n = p.findtext("Name")
    give("Platforms", n, "Platforms", PLATFORM_ALIAS.get(n, n))
for c in P.findall("PlatformCategory"):
    n = c.findtext("Name")
    if n in CATEGORY_FROM:
        give("Platform Categories", n, *CATEGORY_FROM[n])
for f in glob.glob(os.path.join(D, "Playlists", "*.xml")):
    n = ET.parse(f).getroot().findtext("Playlist/Name") or ""
    if n.startswith("Best of "):
        sysname = n[len("Best of "):]
        give("Playlists", n, "Platforms", PLATFORM_ALIAS.get(sysname, sysname))
    elif n in PLAYLIST_FROM:
        give("Playlists", n, *PLAYLIST_FROM[n])
missing = []
for f in glob.glob(os.path.join(D, "Playlists", "*.xml")):
    n = ET.parse(f).getroot().findtext("Playlist/Name") or ""
    if not os.path.exists(os.path.join(PACK, "Playlists", fname(n))):
        missing.append(n)
print("\n".join(made) or "nothing to add")
print(f"{len(made)} icons/logos added; playlists still without an icon: {missing}")
