"""Build LaunchBox platform/game/emulator XML for a whole collection, straight from the ROM folders.

Format copied from files LaunchBox 14.0.1 wrote itself (Data/Platforms/Windows.xml, Data/Platforms.xml).
Titles, years, developers, genres and descriptions come from LaunchBox's own Metadata/LaunchBox.Metadata.db.
LaunchBox must be CLOSED while this runs (it rewrites Data on exit).

Usage: py lb_build.py <platform key> [<platform key> ...]   (keys from PLATFORMS below; 'all' for every one)
Paths come from lb_settings.json (see lbconfig.py). Backs Data up to <work_dir>\\logs\\lb_data_backup_<time> first.
Re-running is safe: game IDs come from file paths, and favourites, play history, ratings and manuals carry over.
"""
import os, re, sys, uuid, shutil, sqlite3, datetime, html, subprocess, bisect
import xml.etree.ElementTree as ET

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

ROOT = C.ROOT
LB = C.LB
DATA = os.path.join(LB, "Data")
DB = os.path.join(LB, r"Metadata\LaunchBox.Metadata.db")
NS = uuid.UUID("6f1c2b9e-1d7a-4b8e-9a51-5b0c8d2e7f10")  # fixed namespace so re-runs keep the same IDs

RA = os.path.join(os.path.relpath(C.RA_DIR, LB), "retroarch.exe")  # relative to the LaunchBox folder, as LaunchBox stores it
EMULATORS = {
    "RetroArch": {"path": RA, "cmd": "-f"},
    "MAME": {"path": os.path.join(ROOT, r"Mame\mame.exe"), "cmd": "", "noquotes": True, "filename_only": True},
    "Dolphin": {"path": os.path.join(ROOT, r"Emulators & Utils\Dolphin-x64\Dolphin.exe"),
                "cmd": "-b -C Dolphin.Display.Fullscreen=True -C Dolphin.Interface.ConfirmStop=False -e"},
    "Cemu": {"path": os.path.join(ROOT, r"Emulators & Utils\Cemu_2.0-60\Cemu.exe"), "cmd": "-f -g"},
    "RPCS3": {"path": os.path.join(ROOT, r"PS3\rpcs3.exe"), "cmd": "--no-gui"},
    "PCSX2": {"path": os.path.join(ROOT, r"Emulators & Utils\PCSX2 2.8.2\pcsx2-qt.exe"), "cmd": "-batch -fullscreen"},
    "WinUAE": {"path": os.path.join(ROOT, r"Amiga\Amiga WinUAE\winuae64.exe"), "cmd": "-s use_gui=no -config=", "nospace": True},
    "VPX": {"path": os.path.join(ROOT, r"Pinball\VPX\VPinballX64.exe"),
            "cmd": '-Ini "' + os.path.join(ROOT, r"Pinball\VPX\VPinballX.ini") + '" -ExtMinimized -Primary -Play'},
    "Spectaculator": {"path": r"C:\Program Files (x86)\Spectaculator\Spectaculator.exe", "cmd": ""},
    "Ryujinx": {"path": os.path.join(ROOT, r"Emulators & Utils\Ryujinx\ryujinx-1.1.734-win_x64\ryujinx\Ryujinx.exe"), "cmd": "--fullscreen"},
    "Hypseus": {"path": os.path.join(ROOT, r"Emulators & Utils\Hypseus\hypseus_launch.bat"), "cmd": ""},
    "Xenia": {"path": os.path.join(ROOT, r"XBOX 360\xenia_master\xenia.exe"), "cmd": ""},
}
for _name, _exe in C.EMULATOR_PATHS.items():   # lb_settings.json "emulator_paths" wins over the defaults above
    EMULATORS.setdefault(_name, {"cmd": ""})["path"] = os.path.normpath(_exe)

# key: (LaunchBox platform name, category, [rom folders under ROOT], extensions, emulator, retroarch core or None)
PLATFORMS = {
    "a2600": ("Atari 2600", "Consoles", ["Atari 2600", r"Roms\Atari 2600"], [".bin", ".a26", ".zip"], "RetroArch", "stella"),
    "a5200": ("Atari 5200", "Consoles", ["Atari 5200"], [".a52", ".bin", ".zip"], "RetroArch", "a5200"),
    "a7800": ("Atari 7800", "Consoles", ["Atari 7800", r"Roms\Atari 7800"], [".a78", ".bin", ".zip"], "RetroArch", "prosystem"),
    "jaguar": ("Atari Jaguar", "Consoles", ["Atari Jaguar Games"], [".j64", ".jag", ".zip"], "RetroArch", "virtualjaguar"),
    "lynx": ("Atari Lynx", "Handhelds", ["Atari Lynx Games", r"Roms\Lynx"], [".lnx", ".zip", ".7z"], "RetroArch", "handy"),
    "coleco": ("ColecoVision", "Consoles", ["Colecovision"], [".col", ".rom", ".zip"], "RetroArch", "gearcoleco"),
    "intv": ("Mattel Intellivision", "Consoles", ["Intellivision"], [".int", ".bin", ".rom", ".zip"], "RetroArch", "freeintv"),
    "vectrex": ("GCE Vectrex", "Consoles", ["Vectrex"], [".vec", ".bin", ".zip"], "RetroArch", "vecx"),
    "pce": ("NEC TurboGrafx-16", "Consoles", ["TurboGrafx 16 Games", "PC Engine Games"], [".pce", ".zip"], "RetroArch", "mednafen_pce"),
    "snes": ("Super Nintendo Entertainment System", "Consoles", ["Super Nintendo", r"Roms\SNES"], [".sfc", ".smc", ".zip"], "RetroArch", "snes9x"),
    "n64": ("Nintendo 64", "Consoles", ["Nintendo 64"], [".z64", ".n64", ".v64", ".zip"], "RetroArch", "mupen64plus_next"),
    "nds": ("Nintendo DS", "Handhelds", ["Nintendo DS"], [".nds", ".zip", ".7z"], "RetroArch", "melonds"),
    "psp": ("Sony PSP", "Handhelds", ["Sony PSP", r"Roms\PSP"], [".iso", ".cso", ".pbp", ".zip"], "RetroArch", "ppsspp"),
    "neogeo": ("SNK Neo Geo AES", "Consoles", ["NeoGeo"], [".zip"], "RetroArch", "fbneo"),
    "arcade": ("Arcade", "Arcade", [r"Arcade\MAME 0.261 ROMs (non-merged)", r"Roms\Arcade"], [".zip"], "MAME", None),
    "gnw": ("Nintendo Game & Watch", "Handhelds", [r"Arcade\MAME 0.261 ROMs (non-merged)"], [".zip"], "MAME", None),
    "ps2": ("Sony Playstation 2", "Consoles", [r"Roms\PS 2"], [".iso", ".chd", ".cso"], "PCSX2", None),
    "ngp": ("SNK Neo Geo Pocket Color", "Handhelds", [r"Roms\Neo Pocket"], [".zip"], "RetroArch", "mednafen_ngp"),
    "3ds": ("Nintendo 3DS", "Handhelds", ["Nintendo 3DS"], [".3ds", ".cci", ".cia"], "RetroArch", "citra"),
    "wiiu": ("Nintendo Wii U", "Consoles", ["Wii U"], [".rpx", ".wud", ".wux", ".wua"], "Cemu", None),
    "amiga": ("Commodore Amiga", "Computers", [r"Amiga\Amiga WinUAE\ADF Games", r"Amiga\Amiga WinUAE\PC Drive", r"Amiga\Retroplay WHDLoad"], [".m3u", ".adf", ".lha"], "RetroArch", "puae"),
    "x360": ("Microsoft Xbox 360", "Consoles", [r"XBOX 360\xenia_master\ROMS"], [".iso", ".xex"], "Xenia", None),
    "ps3": ("Sony Playstation 3", "Consoles", [r"PS3\ROMS"], [".bin"], "RPCS3", None),
    "vpx": ("Visual Pinball X", "Arcade", [r"Pinball\VPX\Tables"], [".vpx"], "VPX", None),
    "zx": ("Sinclair ZX Spectrum", "Computers", ["ZX Spectrum"], [".tzx", ".tap", ".z80", ".sna", ".szx", ".dsk"], "RetroArch", "fuse"),
    "switch": ("Nintendo Switch", "Consoles", ["Nintendo Switch"], [".nsp", ".xci"], "Ryujinx", None),
    "md": ("Sega Genesis", "Consoles", ["Mega Drive"], [".md", ".gen", ".bin", ".smd", ".zip"], "RetroArch", "genesis_plus_gx"),
    "st": ("Atari ST", "Computers", ["Atari ST"], [".zip", ".st", ".stx", ".msa"], "RetroArch", "hatari"),
    "dc": ("Sega Dreamcast", "Consoles", ["Dreamcast"], [".chd", ".gdi", ".cdi"], "RetroArch", "flycast"),
    "nes": ("Nintendo Entertainment System", "Consoles", ["NES"], [".nes", ".zip", ".7z"], "RetroArch", "mesen"),
    "gb": ("Nintendo Game Boy", "Handhelds", ["Game Boy"], [".gb", ".zip", ".7z"], "RetroArch", "sameboy"),
    "gbc": ("Nintendo Game Boy Color", "Handhelds", ["Game Boy Color"], [".gbc", ".zip", ".7z"], "RetroArch", "sameboy"),
    "gba": ("Nintendo Game Boy Advance", "Handhelds", ["Game Boy Advance"], [".gba", ".zip", ".7z"], "RetroArch", "mgba"),
    "sms": ("Sega Master System", "Consoles", ["Master System"], [".sms", ".zip", ".7z"], "RetroArch", "genesis_plus_gx"),
    "gg": ("Sega Game Gear", "Handhelds", ["Game Gear"], [".gg", ".zip", ".7z"], "RetroArch", "genesis_plus_gx"),
    "scd": ("Sega CD", "Consoles", ["Mega-CD"], [".chd", ".cue", ".m3u"], "RetroArch", "genesis_plus_gx"),
    "32x": ("Sega 32X", "Consoles", ["32X", "Mega Drive"], [".32x", ".zip", ".7z"], "RetroArch", "picodrive"),
    "saturn": ("Sega Saturn", "Consoles", ["Saturn"], [".chd", ".cue", ".m3u"], "RetroArch", "mednafen_saturn"),
    "ps1": ("Sony Playstation", "Consoles", ["PS1"], [".chd", ".cue", ".m3u", ".pbp"], "RetroArch", "swanstation"),
    "c64": ("Commodore 64", "Computers", ["Commodore 64"], [".d64", ".t64", ".prg", ".crt", ".tap", ".zip"], "RetroArch", "vice_x64sc"),
    "cpc": ("Amstrad CPC", "Computers", ["Amstrad CPC"], [".dsk", ".cdt", ".zip"], "RetroArch", "cap32"),
    "dos": ("MS-DOS", "Computers", ["DOS"], [".zip", ".dosz", ".exe"], "RetroArch", "dosbox_pure"),
    "wii": ("Nintendo Wii", "Consoles", ["Nintendo Wii"], [".iso", ".rvz", ".wbfs", ".ciso"], "Dolphin", None),
    "gc": ("Nintendo GameCube", "Consoles", ["Nintendo GameCube", r"Roms\GameCube"], [".iso", ".gcm", ".gcz", ".rvz", ".ciso"], "Dolphin", None),
}
for _k, _f in C.ROM_FOLDERS.items():   # lb_settings.json "rom_folders" (relative to emulation_root) wins over the defaults
    if _k in PLATFORMS:
        PLATFORMS[_k] = PLATFORMS[_k][:2] + ([os.path.normpath(x) for x in _f],) + PLATFORMS[_k][3:]

ET_FIELDS_DEFAULT = [  # fields LaunchBox writes on every game, in its own order
    ("Completed", "false"), ("Favorite", "false"), ("ScummVMAspectCorrection", "false"), ("ScummVMFullscreen", "false"),
    ("StarRatingFloat", "0"), ("StarRating", "0"), ("UseDosBox", "false"), ("UseScummVM", "false"),
    ("PlayCount", "0"), ("PlayTime", "0"), ("Portable", "false"), ("Hide", "false"), ("Broken", "false"),
]


def gid(*parts):
    return str(uuid.uuid5(NS, "|".join(parts)))


def compare(s):
    s = s.upper().replace("&", " AND ").replace("'", "").replace("’", "")
    s = re.sub(r"[^A-Z0-9]+", " ", s).strip()
    s = re.sub(r"^THE ", "", s)   # 'The Untouchables' == 'Untouchables'
    s = re.sub(r"\b(II|III|IV|V|VI|VII|VIII|IX|X)\b", lambda m: ROMAN[m.group(1)], s)   # Gauntlet IV == Gauntlet 4
    s = s.replace("WONDERBOY", "WONDER BOY")
    return re.sub(r"\s+", " ", s).strip()


ROMAN = {"II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10"}
# public-domain demos, test carts and utilities in the GoodTools sets: not games
JUNK_WORDS = re.compile(r"(?i)\b(demo|sample|editor|viewer|test|intro|music|player|bios|tracker)\b")


def is_junk(fn):
    return bool(re.search(r"(?i)\bbios\b", fn)) or ("(PD)" in fn and bool(JUNK_WORDS.search(fn)))


TITLE_FIX = {  # file name -> the real title, where the file name alone matches the wrong game
    "clue_v1.1_aga.lha": "The Clue!",
}


def clean_name(fn):
    if os.path.basename(fn).lower() in TITLE_FIX:
        return TITLE_FIX[os.path.basename(fn).lower()]
    base = os.path.splitext(fn)[0]
    base = re.sub(r"(?i)\.(bin|smd|md|gen|sms|gg|32x|nes|sfc|smc|a26|a78|lnx|col|int|pce|z64|n64|v64)$", "", base)   # "X.bin.zip"
    base = re.sub(r"\s*[\(\[].*?[\)\]]", "", base)          # (USA) [!] (1) etc
    base = re.sub(r"\s+", " ", base).strip(" -_")
    base = re.sub(r"(?i)\.nkit$", "", base)
    if fn.lower().endswith(".lha"):                          # WHDLoad: AlienBreed2_v1.4_AGA_0044 -> Alien Breed 2
        base = re.sub(r"_v\d.*$", "", base)
        base = re.sub(r"(_(BETA|JST|Files|Image|NTSC|PAL))+$", "", base, flags=re.I)   # WHDLoad tags with no version
        base = re.sub(r"_(AGA|CD32|NTSC|PAL|Fr|De|It|Es)$", "", base)
        base = base.replace("_", " ")
        base = re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Z][a-z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", base)   # 3DTennis -> 3D Tennis
    base = re.sub(r"^\d{4} - ", "", base)
    base = re.sub(r"\s*\[[0-9A-Fa-f]{16}\].*$", "", base)        # Switch title IDs                    # 3DS release numbers "0004 - "
    base = re.sub(r"(?i)\s+(disc|disk|dvd|cd)\s*1$", "", base)  # "... DVD 1" -> the game
    m = re.match(r"^(.*?), (The|A|An)( - .*)?$", base)        # "Legend of Zelda, The - Twilight Princess"
    if m:
        base = f"{m.group(2)} {m.group(1)}{m.group(3) or ''}"
    return base


class Db:
    def __init__(self):
        self.c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    def index(self, platform):
        idx = {}
        q = "select DatabaseID,Name,CompareName,ReleaseDate,ReleaseYear,Overview,MaxPlayers,CommunityRating,CommunityRatingCount,WikipediaURL,Genres,Developer,Publisher,VideoURL from Games where Platform=?"
        rows = {r[0]: r for r in self.c.execute(q, (platform,))}
        for r in rows.values():
            idx.setdefault(compare(r[1]), r)
        for alt, dbid in self.c.execute(
                "select a.AlternateName,a.DatabaseID from GameAlternateTitles a join Games g on g.DatabaseID=a.DatabaseID where g.Platform=?",
                (platform,)):
            if dbid in rows:
                idx.setdefault(compare(alt), rows[dbid])
        # last resort: 'Speedball 2' -> 'Speedball 2: Brutal Deluxe', only when that is the ONLY database game whose
        # name starts with those words ('ECCO' must not become 'Ecco: The Tides of Time' while 'Ecco the Dolphin' exists)
        names = sorted(compare(r[1]) for r in rows.values())
        mains = {}
        for r in rows.values():
            m = re.split(r":| - ", r[1], maxsplit=1)
            if len(m) == 2:
                mains.setdefault(compare(m[0]), []).append(r)
        for k, rs in mains.items():
            if len(rs) != 1 or not k:
                continue
            lo = bisect.bisect_left(names, k)
            hi = bisect.bisect_left(names, k + " ￿")
            same = [n for n in names[lo:hi] if n == k or n.startswith(k + " ")]
            if len(same) == 1:
                idx.setdefault(k, rs[0])
        for k in list(idx):   # spacing differences: 'Auto Duel' == 'Autoduel', 'X Treme Racing' == 'XTreme Racing'
            idx.setdefault("~" + k.replace(" ", ""), idx[k])
        return idx


def lookup(idx, title):
    """Database row for a title: exact, then 'A / B' first half, then ignoring spaces, then 'Game&Data Disk' -> Game."""
    k = compare(title)
    meta = idx.get(k)
    if not meta and " / " in title:
        meta = idx.get(compare(title.split(" / ")[0]))
    if not meta:
        meta = idx.get("~" + k.replace(" ", ""))
    if not meta and "&" in title:
        meta = idx.get(compare(title.split("&")[0]))
    return meta


def sub(parent, tag, text):
    e = ET.SubElement(parent, tag)
    if text is not None and text != "":
        e.text = str(text)
    return e


def game_xml(root, title, path, platform, emu_id, meta, extra=None):
    g = ET.SubElement(root, "Game")
    now = datetime.datetime.now().astimezone().isoformat()
    sub(g, "ApplicationPath", path)
    sub(g, "DateAdded", now)
    sub(g, "DateModified", now)
    sub(g, "ID", gid(platform, path))
    sub(g, "Platform", platform)
    sub(g, "Emulator", emu_id)
    sub(g, "Title", title)
    if meta:
        (dbid, name, _c, rdate, ryear, overview, maxp, rating, votes, wiki, genres, dev, pub, video) = meta
        sub(g, "DatabaseID", dbid)
        if rdate:
            sub(g, "ReleaseDate", str(rdate)[:10])
        if dev:
            sub(g, "Developer", dev)
        if pub:
            sub(g, "Publisher", pub)
        if overview:
            sub(g, "Notes", overview)
        if genres:
            sub(g, "Genre", genres)
        if maxp:
            sub(g, "MaxPlayers", maxp)
        if rating:
            sub(g, "CommunityStarRating", rating)
            sub(g, "CommunityStarRatingTotalVotes", votes or 0)
        if wiki:
            sub(g, "WikipediaURL", wiki)
        if video:
            sub(g, "VideoUrl", video)
    man = os.path.join(LB, "Manuals", platform, re.sub(r"[:/\\?*\"<>|']", "_", title) + ".pdf")
    if os.path.exists(man):   # manuals placed by manuals_link.py
        sub(g, "ManualPath", man)
    for k, v in (extra or {}).items():
        sub(g, k, v)
    for k, v in ET_FIELDS_DEFAULT:
        sub(g, k, v)
    return g


KEEP_FIELDS = ("Favorite", "Completed", "StarRating", "StarRatingFloat", "PlayCount", "PlayTime", "LastPlayedDate",
               "Hide", "Broken", "ManualPath", "DateAdded")


def carry_over(root, old_path):
    """Keep what the player did (favourites, play history, ratings, hidden/broken, manuals) across rebuilds, by game ID."""
    if not os.path.exists(old_path):
        return 0
    old = {g.findtext("ID"): g for g in ET.parse(old_path).getroot().findall("Game")}
    new_ids = {g.findtext("ID") for g in root.findall("Game")}
    # a game whose file changed (a better copy chosen, a ROM replaced) gets a new ID: fall back to its title
    gone_by_title = {}
    for i, o in old.items():
        if i not in new_ids:
            gone_by_title.setdefault(compare(o.findtext("Title") or ""), o)
    n = 0
    renames = {}
    for g in root.findall("Game"):
        o = old.get(g.findtext("ID"))
        if o is None:
            o = gone_by_title.pop(compare(g.findtext("Title") or ""), None)
        if o is None:
            continue
        retitled = (o.findtext("Title") or "") != (g.findtext("Title") or "")
        if retitled:
            renames[o.findtext("Title")] = g.findtext("Title")
        for f in KEEP_FIELDS:
            if f == "ManualPath" and retitled:
                continue          # set again below, after the manual file is renamed
            v = o.findtext(f)
            if v is None or v == "":
                continue
            e = g.find(f)
            if e is None:
                e = ET.SubElement(g, f)
            if e.text != v:
                e.text = v; n += 1
    if renames:
        current = {(g.findtext("Title") or "").lower() for g in root.findall("Game")}
        renames = {a: b for a, b in renames.items() if a.lower() not in current}   # old title still used by another game
        plat = root.findtext("Game/Platform") or ""
        rename_media(plat, renames)
        for g in root.findall("Game"):
            if g.findtext("Title") in renames.values() and g.find("ManualPath") is None:
                man = os.path.join(LB, "Manuals", plat, re.sub(r"[:/\\?*\"<>|']", "_", g.findtext("Title")) + ".pdf")
                if os.path.exists(man):
                    sub(g, "ManualPath", man)
    return n


def rename_media(platform, renames):
    """A game whose title changed (now matched to the database) keeps its images, video and manual:
    '<old title>-01.png' -> '<new title>-01.png'. Never overwrites; skips titles shared by another game."""
    safe = lambda t: re.sub(r"[:/\\?*\"<>|']", "_", t)
    olds = {safe(a).lower(): safe(b) for a, b in renames.items() if safe(a).lower() != safe(b).lower()}
    moved = 0
    for top in (os.path.join(LB, "Images", platform), os.path.join(LB, "Videos", platform), os.path.join(LB, "Manuals", platform)):
        for dp, _d, files in os.walk(top):
            for f in files:
                m = re.match(r"^(.*?)(-0\d+)?(\.[^.]+)$", f)
                new = olds.get(m.group(1).lower()) if m else None
                if not new:
                    continue
                dst = os.path.join(dp, new + (m.group(2) or "") + m.group(3))
                if not os.path.exists(dst):
                    os.rename(os.path.join(dp, f), dst); moved += 1
    print(f"  {len(olds)} titles changed, {moved} media files renamed")


def write_xml(root, path):
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" standalone="yes"?>\n' + body + "\n")


def load(path):
    return ET.parse(path).getroot() if os.path.exists(path) else ET.Element("LaunchBox")


def ensure_emulator(emus, name, platform, core):
    eid = gid("emulator", name)
    cfg = EMULATORS[name]
    for e in emus.findall("Emulator"):
        if e.findtext("ID") == eid:
            e.find("ApplicationPath").text = cfg["path"]
    if not any(e.findtext("ID") == eid for e in emus.findall("Emulator")):
        e = ET.SubElement(emus, "Emulator")
        sub(e, "ApplicationPath", cfg["path"])
        sub(e, "CommandLine", cfg["cmd"])
        sub(e, "ID", eid)
        sub(e, "Title", name)
        sub(e, "NoQuotes", "true" if cfg.get("noquotes") else "false")
        sub(e, "NoSpace", "true" if cfg.get("nospace") else "false")
        sub(e, "HideConsole", "false")
        sub(e, "FileNameWithoutExtensionAndPath", "true" if cfg.get("filename_only") else "false")
        sub(e, "AutoExtract", "false")
        sub(e, "UseStartupScreen", "true")
        sub(e, "UsePauseScreen", "true")
    for ep in emus.findall("EmulatorPlatform"):
        if ep.findtext("Emulator") == eid and ep.findtext("Platform") == platform:
            emus.remove(ep)
    ep = ET.SubElement(emus, "EmulatorPlatform")
    sub(ep, "Emulator", eid)
    sub(ep, "Platform", platform)
    sub(ep, "CommandLine", f'-L "cores\\{core}_libretro.dll"' if core else "")
    sub(ep, "Default", "true")
    sub(ep, "M3uDiscLoadEnabled", "false")
    return eid


def ensure_platform(plats, parents, name, category):
    if not any(p.findtext("Name") == name for p in plats.findall("Platform")):
        p = ET.SubElement(plats, "Platform")
        sub(p, "Name", name)
        sub(p, "ScrapeAs", name)
        sub(p, "LocalDbParsed", "false")
        sub(p, "HideInBigBox", "false")
        sub(p, "DisableAutoImport", "false")
        media = [f.findtext("MediaType") for f in plats.findall("PlatformFolder") if f.findtext("Platform") == "Windows"]
        for m in media:
            f = ET.SubElement(plats, "PlatformFolder")
            sub(f, "MediaType", m)
            folder = {"Video": "Videos", "Manual": "Manuals", "Music": "Music"}.get(m)
            sub(f, "FolderPath", f"{folder}\\{name}" if folder else f"Images\\{name}\\{m}")
            sub(f, "Platform", name)
    if not any(x.findtext("PlatformName") == name for x in parents.findall("Parent")):
        x = ET.SubElement(parents, "Parent")
        sub(x, "PlatformName", name)
        sub(x, "ParentPlatformCategoryName", category)
    if not any(c.findtext("Name") == category for c in plats.findall("PlatformCategory")):
        c = ET.SubElement(plats, "PlatformCategory")
        sub(c, "Name", category)
        sub(c, "NestedName", category)
        sub(c, "IsAutogenerated", "false")
        sub(c, "HideInBigBox", "false")
    if not any(x.findtext("PlatformCategoryName") == category and x.find("PlatformName") is None for x in parents.findall("Parent")):
        x = ET.SubElement(parents, "Parent")
        sub(x, "PlatformCategoryName", category)


BAD_TAGS = re.compile(r"(?i)\[(b|a|h|t|f|o|p|cr|tr|m|u|x)[^\]]*\]|\((beta|proto|prototype|demo|sample|hack|pirate|unl)[^)]*\)")
FORMAT_ORDER = {".tzx": 0, ".tap": 1, ".z80": 2, ".sna": 3}


def quality(fn):
    """Lower is better: verified good dumps first, then clean copies; betas, bad dumps, hacks, cracks and trainers last."""
    s = FORMAT_ORDER.get(os.path.splitext(fn)[1].lower(), 0)
    s += 20 * len(BAD_TAGS.findall(fn))
    if "[!]" in fn:
        s -= 5
    s += region_rank(fn)
    return s


REGIONS = [  # (pattern, penalty): English 60 Hz first, then PAL English, then Japan, then other-language releases
    (r"\((World|USA|U|UE|UJ|JU|JUE|EUJ|EJU|UEJ|4|USA, Europe)\)", 0),
    (r"\((Europe|E|UK|EU|Australia|A|5)\)", 1),
    (r"\((Japan|J|1)\)", 3),
    (r"\((F|G|S|I|Fr|De|Es|It|Sw|NL|B|Brazil|Korea|K|Chinese|C|French|German|Spanish|Italian)\)", 4),
]


def region_rank(fn):
    for pat, pen in REGIONS:
        if re.search(pat, fn, re.I):
            return pen
    return 2   # no region tag: between PAL and Japan


def mame_index():
    out = {}
    for _ev, el in ET.iterparse(os.path.join(LB, r"Metadata\MAME.xml")):
        if el.tag == "MameFile":
            out[(el.findtext("FileName") or "").lower()] = {"name": el.findtext("Name") or "",
                                                           "clone": bool(el.findtext("CloneOf"))}
            el.clear()
    return out


KEEP_CLONES = {"pacman", "gradius"}  # the names everyone knows, which MAME files as clones of Puck Man and Nemesis

SKIP_FLAGS = ("IsMechanical", "IsBootleg", "IsMature", "IsQuiz", "IsFruit", "IsCasino", "IsMahjong",
              "IsNonArcade", "IsPlayChoice", "IsTableTop", "IsRhythm")


def arcade_games(root, platform, eid, idx, folders):
    """Parents only, from LaunchBox's MAME.xml: no clones, bootlegs, mature, casino, mahjong, quiz or non-working sets."""
    have = {}
    for folder in folders:
        if not os.path.isdir(os.path.join(ROOT, folder)):
            print(f"  {platform}: folder not found, skipped: {os.path.join(ROOT, folder)}  (set rom_folders in lb_settings.json)")
            continue
        for fn in os.listdir(os.path.join(ROOT, folder)):
            if fn.lower().endswith(".zip"):
                have.setdefault(fn[:-4].lower(), os.path.join(ROOT, folder, fn))
    n = hit = 0
    for _ev, el in ET.iterparse(os.path.join(LB, r"Metadata\MAME.xml")):
        if el.tag != "MameFile":
            continue
        rom = (el.findtext("FileName") or "").lower()
        ok = (rom in have and (not el.findtext("CloneOf") or rom in KEEP_CLONES)
              and el.findtext("Status") in ("good", "imperfect")
              and all(el.findtext(f) != "true" for f in SKIP_FLAGS))
        if ok:
            title = el.findtext("Name") or rom
            meta = idx.get(compare(title)) or (idx.get(compare(title.split(" / ")[0])) if " / " in title else None)
            extra = {"Version": el.findtext("Version") or "", "Region": el.findtext("Region") or "",
                     "PlayMode": el.findtext("PlayMode") or "", "Status": el.findtext("Status") or "",
                     "Source": el.findtext("Source") or ""}
            g = game_xml(root, meta[1] if meta else title, have[rom], platform, eid, meta,
                         {k: v for k, v in extra.items() if v})
            if not meta:
                for tag, field in (("Developer", "Developer"), ("Publisher", "Publisher"), ("Genre", "Genre")):
                    v = el.findtext(field)
                    if v:
                        sub(g, tag, v)
                y = el.findtext("Year")
                if y and y.isdigit():
                    sub(g, "ReleaseDate", f"{y}-01-01")
            n += 1
            hit += bool(meta)
        el.clear()
    return n, hit


def gnw_games(root, platform, eid, idx, folders):
    """Nintendo Game & Watch from the MAME set (gnw_*.zip, LCD screen SVG is inside each zip). Parents only;
    'Game & Watch: Ball' -> 'Ball' to match the LaunchBox database."""
    have = {}
    for folder in folders:
        if not os.path.isdir(os.path.join(ROOT, folder)):
            print(f"  {platform}: folder not found, skipped: {os.path.join(ROOT, folder)}  (set rom_folders in lb_settings.json)")
            continue
        for e in os.scandir(os.path.join(ROOT, folder)):
            if e.name.lower().startswith("gnw_") and e.name.lower().endswith(".zip"):
                have.setdefault(e.name[:-4].lower(), e.path)
    n = hit = 0
    for _ev, el in ET.iterparse(os.path.join(LB, r"Metadata\MAME.xml")):
        if el.tag != "MameFile":
            continue
        rom = (el.findtext("FileName") or "").lower()
        if rom in have and not el.findtext("CloneOf") and el.findtext("Status") in ("good", "imperfect"):
            full = el.findtext("Name") or rom
            short = re.sub(r"^Game & Watch:\s*", "", full)
            meta = idx.get(compare(short)) or idx.get(compare(full))
            g = game_xml(root, meta[1] if meta else short, have[rom], platform, eid, meta,
                         {k: v for k, v in {"Version": el.findtext("Version") or ""}.items() if v})
            if not meta:
                sub(g, "Publisher", "Nintendo")
                sub(g, "Genre", "Handheld / Electronic Game")
                y = el.findtext("Year")
                if y and y.isdigit():
                    sub(g, "ReleaseDate", f"{y}-01-01")
            n += 1
            hit += bool(meta)
        el.clear()
    return n, hit


def build(keys):
    running = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    if "launchbox.exe" in running or "bigbox.exe" in running:
        sys.exit("Close LaunchBox / Big Box first: it rewrites its Data folder on exit and would undo this build.")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copytree(DATA, _os.path.join(C.LOGS, rf"lb_data_backup_{stamp}"))
    db = Db()
    emus = load(os.path.join(DATA, "Emulators.xml"))
    plats = load(os.path.join(DATA, "Platforms.xml"))
    parents = load(os.path.join(DATA, "Parents.xml"))
    for key in keys:
        name, cat, folders, exts, emu, core = PLATFORMS[key]
        eid = ensure_emulator(emus, emu, name, core)
        ensure_platform(plats, parents, name, cat)
        idx = db.index(name)
        root = ET.Element("LaunchBox")
        best = {}
        n = hit = 0
        mame_names = mame_index() if key == "neogeo" else None
        if key == "gnw":
            n, hit = gnw_games(root, name, eid, idx, folders)
            folders = []
        if key == "arcade":
            n, hit = arcade_games(root, name, eid, idx, folders)
            folders = []
            # laserdisc games (Dragon's Lair etc.) run in Hypseus Singe, with the video from your own Daphne set
            vl = os.path.join(ROOT, r"Emulators & Utils\Hypseus\Hypseus Singe\vldp")
            hid = ensure_emulator(emus, "Hypseus", name, None) if os.path.isdir(vl) else None
            for ep in emus.findall("EmulatorPlatform"):
                if hid and ep.findtext("Emulator") == hid and ep.findtext("Platform") == name:
                    ep.find("Default").text = "false"
            for folder, ff, title in (("lair", "lair.txt", "Dragon's Lair"), ("lair2", "dl2-framefile.txt", "Dragon's Lair II: Time Warp"),
                                      ("ace", "ace.txt", "Space Ace"), ("tq", "tq.txt", "Thayer's Quest")):
                fp = os.path.join(vl, folder, ff)
                if hid and os.path.exists(fp):
                    meta = idx.get(compare(title))
                    game_xml(root, meta[1] if meta else title, fp, name, hid, meta)
                    n += 1; hit += bool(meta)
        for folder in folders:
            base = os.path.join(ROOT, folder)
            for dirpath, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith("_")]   # _broken, _tmp, _INBOX: not part of the library
                if key == "amiga":   # WHDLoad demos and disk magazines have their own platform (amigademo)
                    dirs[:] = [d for d in dirs if d.lower() not in ("demos", "magazines")]
                order = {".tzx": 0, ".tap": 1, ".z80": 2, ".sna": 3}
                for fn in sorted(files, key=lambda f: (order.get(os.path.splitext(f)[1].lower(), 9), f.lower())):
                    if os.path.splitext(fn)[1].lower() not in exts:
                        continue
                    path = os.path.join(dirpath, fn)
                    if re.search(r"(?i)(disc|disk|dvd|cd) ?[2-9]", fn):   # later discs are swapped in game, not listed
                        continue
                    if fn.lower().endswith(".adf") and any(x.lower().endswith(".m3u") for x in files):
                        continue          # disk 1..n are in the .m3u
                    if fn.lower().startswith(("whdload", "skick", "pfs3aio")):
                        continue          # WHDLoad/kickstart tools, not games
                    if key == "vpx" and re.search(r"(?i)test|calibration", fn):
                        continue          # VPX sample/calibration tables
                    if key == "switch" and "[UPD]" in fn:
                        continue          # updates install on top of the game, not a game
                    if key == "switch":
                        with open(path, "rb") as fh:
                            if fh.read(4) != b"PFS0":   # zero-filled, never finished downloading
                                continue
                    if fn.startswith("[BIOS]") or is_junk(fn):
                        continue
                    is32 = bool(re.search(r"(?i)\b32X\b", fn)) or fn.lower().endswith(".32x")
                    if (key == "md" and is32) or (key == "32x" and not is32):
                        continue          # GoodGen keeps 32X games in the Mega Drive set; they need PicoDrive
                    if key == "32x":
                        fn_title = re.sub(r"(?i)\s*\b32X\b", "", fn)
                    if key == "ps3":
                        if fn.upper() != "EBOOT.BIN" or not dirpath.upper().endswith(r"PS3_GAME\USRDIR"):
                            continue
                        fn_for_title = os.path.basename(os.path.dirname(os.path.dirname(dirpath)))
                    else:
                        fn_for_title = fn_title if key == "32x" else fn
                    title = clean_name(fn_for_title + ("" if key != "ps3" else ".x"))
                    if key == "vpx":                    # "Terminator 2 (Williams 1991) g5k 1.25.vpx" -> "Terminator 2 (Williams 1991)"
                        m = re.match(r"^(.*?\(.*?\d{4}\))", fn)
                        title = m.group(1) if m else title
                    if fn.lower().endswith(".rpx"):
                        title = clean_name(os.path.basename(os.path.dirname(dirpath)))
                    if key == "x360" and fn.lower().endswith(".xex"):   # unpacked game folder: only its default.xex, named by the folder
                        if fn.lower() != "default.xex" and os.path.splitext(fn)[0].lower() != os.path.basename(dirpath).lower():
                            continue   # the game's start file is default.xex or '<folder name>.xex'
                        parts = os.path.relpath(dirpath, base).split(os.sep)
                        parts = [p for p in parts if p.lower() not in ("arcade", ".")]
                        title = clean_name((parts[0] if parts else os.path.basename(dirpath)) + ".x")
                    title = re.sub(r"^\d{4} - ", "", title)          # 3DS release numbers "0270 - "
                    title = re.sub(r"(?i)\s+decrypted$", "", title)
                    if mame_names is not None:          # MAME short names: mslug.zip -> Metal Slug
                        m = mame_names.get(os.path.splitext(fn)[0].lower())
                        if not m or m["clone"] or os.path.splitext(fn)[0].lower() in ("neogeo", "aes"):
                            continue
                        title = m["name"]
                    meta = lookup(idx, title)
                    if meta:
                        title = meta[1]
                    score = quality(fn)
                    if key == "a7800" and "(Europe)" in fn:   # ProSystem draws the headerless PAL dumps scrambled (Joust, 17/10)
                        score += 10
                    k = compare(title)
                    if k not in best or score < best[k][0]:   # keep the cleanest copy of each game
                        best[k] = (score, title, path, meta)
        for _k, (_s, title, path, meta) in best.items():
            game_xml(root, title, path, name, eid, meta)
            n += 1
            hit += bool(meta)
        best.clear()
        whd = C.S.get("amiga_whdload", {})   # optional: a WinUAE hard-drive setup listed as one entry
        if key == "amiga" and whd.get("config") and os.path.exists(os.path.join(ROOT, whd["config"])):
            wid = ensure_emulator(emus, "WinUAE", name, None)
            cfgfile = os.path.join(ROOT, os.path.normpath(whd["config"]))
            game_xml(root, whd.get("title", "Amiga WHDLoad Collection"), cfgfile, name, wid, None,
                     {"Notes": whd.get("notes", "Boots the WinUAE setup with the WHDLoad games drive.")})
            # keep the floppy games on RetroArch as the platform default
            for ep in emus.findall("EmulatorPlatform"):
                if ep.findtext("Emulator") == wid and ep.findtext("Platform") == name:
                    ep.find("Default").text = "false"
            n += 1
        if key == "zx" and os.path.exists(EMULATORS["Spectaculator"]["path"]):   # Fuse stays default (CRT bezel); Spectaculator is a Launch With choice
            sid = ensure_emulator(emus, "Spectaculator", name, None)
            for ep in emus.findall("EmulatorPlatform"):
                if ep.findtext("Emulator") == sid and ep.findtext("Platform") == name:
                    ep.find("Default").text = "false"
        target = os.path.join(DATA, "Platforms", f"{name}.xml")
        if n == 0 and os.path.exists(target) and load(target).find("Game") is not None:
            # No game files found but LaunchBox already lists games: most likely the ROM folder or drive is missing
            # right now. Keep the existing list rather than replacing it with an empty one.
            print(f"{name}: no game files found in {', '.join(folders) or 'its folders'} - kept the existing game list "
                  "untouched (is the drive connected?)")
            continue
        kept = carry_over(root, target)
        write_xml(root, target)
        print(f"{name}: {n} games, {hit} matched to the LaunchBox database, {kept} player fields kept")
    write_xml(emus, os.path.join(DATA, "Emulators.xml"))
    write_xml(plats, os.path.join(DATA, "Platforms.xml"))
    write_xml(parents, os.path.join(DATA, "Parents.xml"))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["all"]:   # every platform with at least one game file on this machine (empty folders don't make empty platforms)
        def has_roms(folders, exts):
            for f in folders:
                for dp, dirs, files in os.walk(os.path.join(ROOT, f)):
                    dirs[:] = [d for d in dirs if not d.startswith("_")]
                    if any(os.path.splitext(x)[1].lower() in exts for x in files):
                        return True
            return False
        args = [k for k, v in PLATFORMS.items() if has_roms(v[2], v[3])]
        print("platforms with games:", " ".join(args))
    build(args)
