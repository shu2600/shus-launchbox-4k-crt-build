"""Paths for the LaunchBox build tools, read from lb_settings.json next to this file.
Copy lb_settings.example.json to lb_settings.json and point it at your own folders. Every tool imports from here,
so no script has a drive letter written into it.

    import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from lbconfig import ROOT, LB, RA_DIR, MAME_DIR, WORK
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_path = os.path.join(HERE, "lb_settings.json")
if not os.path.exists(_path):
    _path = os.path.join(HERE, "lb_settings.example.json")
with open(_path, encoding="utf-8") as _f:
    S = json.load(_f)


def _p(key, default=""):
    v = S.get(key, default)
    if not isinstance(v, str) or not v:
        return v
    return os.path.normpath(os.path.expandvars(os.path.expanduser(v)))   # one slash style, so game IDs (made from paths) never shift


ROOT = _p("emulation_root")                                    # top folder holding ROM folders and emulators
LB = _p("launchbox") or os.path.join(ROOT, "LaunchBox")        # the LaunchBox install (folder with LaunchBox.exe)
RA_DIR = _p("retroarch") or os.path.join(LB, "Emulators", "RetroArch")
MAME_DIR = _p("mame") or os.path.join(ROOT, "Mame")
WORK = _p("work_dir") or os.path.join(HERE, "work")             # logs, backups, review renders
REVIEW = _p("review_dir") or os.path.join(WORK, "bezel_review")
DOWNLOADS = _p("downloads") or os.path.join(os.path.expanduser("~"), "Downloads")
SEVEN_ZIP = _p("seven_zip", r"C:\Program Files\7-Zip\7z.exe")
DECK = S.get("steam_deck", {})                                 # {"host": "deck@steamdeck.local", ...} or empty
ROM_FOLDERS = S.get("rom_folders", {})                         # platform key -> [folders under ROOT]; overrides lb_build defaults
EMULATOR_PATHS = S.get("emulator_paths", {})                   # emulator name -> exe path; overrides lb_build defaults
FAVOURITES = S.get("favourites", {})                           # LaunchBox platform -> [titles], for fav_mark.py
LOGS = os.path.join(WORK, "logs")
os.makedirs(LOGS, exist_ok=True)
