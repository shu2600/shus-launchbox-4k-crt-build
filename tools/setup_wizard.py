"""Shu's LaunchBox 4K CRT Build - setup wizard.
A guided window: what you need (with links to the official download pages), where your folders are,
which systems and how much detail, then it runs the build and shows a live log.
Nothing here downloads games, BIOS or firmware. Run with setup.bat, or: py tools/setup_wizard.py"""
import os, sys, json, glob, shutil, threading, queue, subprocess, webbrowser, importlib, string, ctypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "lb_settings.json")
EXAMPLE = os.path.join(HERE, "lb_settings.example.json")
CONFIGS = os.path.join(os.path.dirname(HERE), "configs")
PY = sys.executable
# repo layout: <repo>/tools/setup_wizard.py + <repo>/assets; dev layout: lb_build/ + release/repo_docs/assets
ASSETS = next((d for d in (os.path.join(os.path.dirname(HERE), "assets"),
                           os.path.join(os.path.dirname(HERE), "release", "repo_docs", "assets")) if os.path.isdir(d)),
              os.path.join(os.path.dirname(HERE), "assets"))

NAME = "Shu's LaunchBox 4K CRT Build"
VERSION = "1.1"   # bump on every change and add a line to CHANGELOG.md
TITLE = NAME + " - Setup  (v" + VERSION + ")"
BG, PANEL, FG, MUTED, ACCENT, OK, BAD = "#14161a", "#1d2026", "#e9e6df", "#9a9a94", "#d9a441", "#7fbf6a", "#d0675b"


def load_settings():
    for p in (SETTINGS, EXAMPLE):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return {}


def P(s, key):
    v = s.get(key) or ""
    return os.path.normpath(os.path.expandvars(v)) if v else ""


# ---- what you need -------------------------------------------------------------------------------------------
def have_module(name):
    try:
        importlib.import_module(name); return True
    except Exception:
        return False


def shaders(s):
    return os.path.join(P(s, "retroarch"), "shaders")


_EXES = {}


def find_exe(s, name):
    """True if <name> sits anywhere under the emulation folder. One walk per folder, cached, exe names only."""
    root = P(s, "emulation_root")
    if root not in _EXES:
        found = set()
        for dp, dirs, files in os.walk(root):
            if dp.count(os.sep) - root.count(os.sep) >= 5:
                dirs[:] = []
            found.update(f.lower() for f in files if f.lower().endswith(".exe"))
        _EXES[root] = found
    return name.lower() in _EXES[root]


PARTS = [  # (name, why, link, check(settings) -> bool, required)
    ("LaunchBox", "The front end everything is built into. Free version is fine; Big Box is optional.",
     "https://www.launchbox-app.com/download", lambda s: os.path.exists(os.path.join(P(s, "launchbox"), "LaunchBox.exe")), True),
    ("RetroArch", "Runs most of the consoles and computers. After installing, use Online Updater > Core Downloader for the cores.",
     "https://www.retroarch.com/?page=platforms", lambda s: os.path.exists(os.path.join(P(s, "retroarch"), "retroarch.exe")), True),
    ("Mega Bezel shader", "The CRT + bezel engine. In RetroArch: Online Updater > Update Slang Shaders installs it.",
     "https://github.com/HyperspaceMadness/Mega_Bezel", lambda s: os.path.isdir(os.path.join(shaders(s), "shaders_slang", "bezel", "Mega_Bezel")), True),
    ("Duimon Mega Bezel packs", "The period TVs, monitors and handheld shells. Unzip into RetroArch\\shaders\\Mega_Bezel_Packs.",
     "https://duimon.github.io/Gallery-Guides/", lambda s: os.path.isdir(os.path.join(shaders(s), "Mega_Bezel_Packs", "Duimon-Mega-Bezel")), True),
    ("TheNamec Commodore pack", "The Commodore 1084S monitor for the Amiga. Unzip into RetroArch\\shaders\\Mega_Bezel_Packs.",
     "https://github.com/TheNamec/megabezel-commodore-pack", lambda s: os.path.isdir(os.path.join(shaders(s), "Mega_Bezel_Packs", "thenamec-commodore-pack")), False),
    ("MAME", "Arcade. Use the 64-bit Windows binary.", "https://www.mamedev.org/release.html",
     lambda s: os.path.exists(os.path.join(P(s, "mame"), "mame.exe")), False),
    ("Lights Out arcade cabinets", "Mr. RetroLust's full-cabinet artwork for MAME (LaunchBox forum account needed).",
     "https://forums.launchbox-app.com/files/file/3927-mr-retrolusts-mame-lights-out-bezels-revisited/",
     lambda s: os.path.isdir(os.path.join(P(s, "mame"), "artwork_lightsout")), False),
    ("Realistic arcade bezels", "OrionsAngel / estefan3112 cabinet artwork for MAME.",
     "https://github.com/estefan3112/MAME-Realistic-Bezel-Artwork", lambda s: os.path.isdir(os.path.join(P(s, "mame"), "artwork_realistic")), False),
    ("The Bezel Project (MAME)", "Arcade bezels; bezelproject_to_mame.py turns them into MAME artwork.",
     "https://github.com/thebezelproject/bezelproject-MAME", lambda s: os.path.isdir(os.path.join(P(s, "mame"), "artwork_bezelproject")), False),
    ("PCSX2", "PlayStation 2.", "https://pcsx2.net/downloads", lambda s: find_exe(s, "pcsx2-qt.exe"), False),
    ("Dolphin", "GameCube and Wii.", "https://dolphin-emu.org/download/", lambda s: find_exe(s, "Dolphin.exe"), False),
    ("RPCS3", "PlayStation 3 (you need the official PS3 firmware from Sony's site).", "https://rpcs3.net/download",
     lambda s: find_exe(s, "rpcs3.exe"), False),
    ("Xenia Canary", "Xbox 360. Canary supports per-game 60 fps patches.", "https://github.com/xenia-canary/xenia-canary-releases/releases",
     lambda s: find_exe(s, "xenia_canary.exe"), False),
    ("Cemu", "Wii U.", "https://cemu.info/", lambda s: find_exe(s, "Cemu.exe"), False),
    ("Hypseus Singe", "Laserdisc games (Dragon's Lair, Space Ace) - you supply the video.", "https://github.com/DirtBagXon/hypseus-singe/releases",
     lambda s: find_exe(s, "hypseus.exe"), False),
    ("Python add-ons", "Pillow and numpy: run  py -m pip install pillow numpy", "https://pypi.org/project/pillow/",
     lambda s: have_module("PIL") and have_module("numpy"), True),
    ("GitHub CLI", "Used to list libretro cover art. Install, then run  gh auth login  once.", "https://cli.github.com/",
     lambda s: bool(shutil.which("gh")), False),
]

# packs the wizard can fetch itself, unchanged, from their creators' own download pages:
# part name -> (url, folder under RetroArch\shaders to unpack into, top folder in the zip to rename to (or None), size note)
DOWNLOADS = {
    "Mega Bezel shader": ("https://buildbot.libretro.com/assets/frontend/shaders_slang.zip", "shaders_slang", None, "54 MB, libretro"),
    "Duimon Mega Bezel packs": ("https://github.com/Duimon/Duimon-Mega-Bezel/releases/download/v1.1.7.0/Duimon-Mega-Bezel_v1.1.7.0.zip",
                                "Mega_Bezel_Packs", None, "910 MB, Duimon's GitHub release"),
    "TheNamec Commodore pack": ("https://github.com/TheNamec/megabezel-commodore-pack/archive/refs/heads/main.zip",
                                "Mega_Bezel_Packs", "thenamec-commodore-pack", "about 330 MB, TheNamec's GitHub"),
}


def fetch_pack(s, part, log, progress, stop):
    """Download one pack to the work folder, then unpack it into RetroArch\\shaders. Returns True when done."""
    import urllib.request, zipfile, tempfile
    url, sub, rename, _note = DOWNLOADS[part]
    dest = os.path.join(shaders(s), sub)
    work = P(s, "work_dir") or tempfile.gettempdir()
    os.makedirs(work, exist_ok=True)
    tmp = os.path.join(work, "download_" + part.replace(" ", "_") + ".zip")
    log(f"{part}: downloading from {url.split('/')[2]}")
    req = urllib.request.Request(url, headers={"User-Agent": "LaunchBox-4K-CRT-Build-setup"})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total, got = int(r.headers.get("Content-Length") or 0), 0
        while True:
            if stop():
                log(f"{part}: cancelled"); f.close(); os.remove(tmp); return False
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b); got += len(b)
            progress(f"{part}: {got >> 20} MB" + (f" of {total >> 20} MB" if total else ""))
    log(f"{part}: unpacking into {dest}")
    os.makedirs(dest, exist_ok=True)
    root = os.path.realpath(dest)
    with zipfile.ZipFile(tmp) as z:
        names = z.namelist()
        top = names[0].split("/")[0] if rename else None
        for n in names:
            out = n
            if rename and out.split("/")[0] == top:
                out = rename + out[len(top):]
            target = os.path.realpath(os.path.join(dest, out))
            if not target.startswith(root + os.sep):      # never write outside the shaders folder
                continue
            if n.endswith("/"):
                os.makedirs(target, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(n) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    os.remove(tmp)
    log(f"{part}: done")
    return True


# build key -> preview key (bezel_review.py) for the systems that have a choice of looks
LOOK_KEYS = {"a2600": "2600", "a5200": "5200", "a7800": "7800", "jaguar": "jaguar", "lynx": "lynx", "st": "st", "coleco": "coleco",
             "amiga": "amiga", "vectrex": "vectrex", "intv": "intv", "pce": "pce", "3ds": "3ds", "n64": "n64", "nds": "ds",
             "dc": "dc", "md": "md", "zx": "zx", "neogeo": "neogeo", "ngp": "ngpc", "psp": "psp", "snes": "snes"}
# RetroArch core (as lb_build names it) -> the config folder RetroArch keeps its presets in
CORE_DIRS = {"stella": ["Stella"], "a5200": ["a5200"], "prosystem": ["ProSystem"], "virtualjaguar": ["Virtual Jaguar"],
             "handy": ["Handy"], "gearcoleco": ["Gearcoleco"], "freeintv": ["FreeIntv"], "vecx": ["vecx"],
             "mednafen_pce": ["Beetle PCE", "Beetle PCE Fast"], "snes9x": ["Snes9x"], "mupen64plus_next": ["Mupen64Plus-Next"],
             "melonds": ["melonDS"], "ppsspp": ["PPSSPP"], "fbneo": ["FinalBurn Neo"], "mednafen_ngp": ["Beetle NeoPop"],
             "citra": ["Citra"], "puae": ["PUAE"], "fuse": ["Fuse"], "genesis_plus_gx": ["Genesis Plus GX"], "hatari": ["hatari"],
             "flycast": ["Flycast"], "picodrive": ["PicoDrive"]}

# folder names people use for each system (compared lower case, letters and digits only)
ALIASES = {
    "a2600": ["atari2600", "2600", "vcs"], "a5200": ["atari5200", "5200"], "a7800": ["atari7800", "7800"],
    "jaguar": ["atarijaguar", "jaguar"], "lynx": ["atarilynx", "lynx"], "coleco": ["colecovision", "coleco"],
    "intv": ["intellivision", "mattelintellivision"], "vectrex": ["vectrex", "gcevectrex"],
    "pce": ["pcengine", "turbografx16", "turbografx", "tg16", "pce"], "snes": ["snes", "supernintendo", "superfamicom", "sfc"],
    "n64": ["n64", "nintendo64"], "nds": ["nds", "nintendods", "ds"], "psp": ["psp", "sonypsp", "playstationportable"],
    "neogeo": ["neogeo", "neogeoaes", "aes"], "arcade": ["mame", "arcade", "fbneo", "finalburnneo"], "gnw": ["gameandwatch", "gamewatch"],
    "ps2": ["ps2", "playstation2", "sonyplaystation2"], "ngp": ["ngpc", "ngp", "neogeopocket", "neogeopocketcolor", "neopocket"],
    "3ds": ["3ds", "nintendo3ds"], "wiiu": ["wiiu", "nintendowiiu"], "amiga": ["amiga", "commodoreamiga", "whdload"],
    "x360": ["xbox360", "x360"], "ps3": ["ps3", "playstation3", "sonyplaystation3"], "vpx": ["vpx", "visualpinball", "visualpinballx"],
    "zx": ["zxspectrum", "spectrum", "sinclairzxspectrum", "zx"], "switch": ["switch", "nintendoswitch"],
    "md": ["megadrive", "genesis", "segagenesis", "segamegadrive", "md"], "st": ["atarist"], "dc": ["dreamcast", "segadreamcast"],
    "nes": ["nes", "famicom", "nintendoentertainmentsystem"], "gb": ["gb", "gameboy", "nintendogameboy"],
    "gbc": ["gbc", "gameboycolor", "gameboycolour"], "gba": ["gba", "gameboyadvance"], "sms": ["mastersystem", "segamastersystem", "sms"],
    "gg": ["gamegear", "segagamegear", "gg"], "scd": ["megacd", "segacd"], "32x": ["32x", "sega32x"], "saturn": ["saturn", "segasaturn"],
    "ps1": ["ps1", "psx", "playstation", "playstation1", "sonyplaystation"], "c64": ["c64", "commodore64"],
    "cpc": ["amstradcpc", "cpc", "amstrad"], "dos": ["dos", "msdos", "pcdos"], "wii": ["wii", "nintendowii"],
    "gc": ["gamecube", "nintendogamecube", "ngc", "gc"]}
_FILLER = ("games", "roms", "rom", "collection", "set", "isos", "iso", "nointro", "fullset", "")


def _norm(name):
    return "".join(c for c in name.lower() if c.isalnum())


def guess_folders(root, platforms, depth=3):
    """{system key: folder relative to root} for folders whose name looks like a system and that hold its game files."""
    import re
    dirs = []
    for dp, ds, _f in os.walk(root):
        ds[:] = [d for d in ds if not d.startswith((".", "_"))]
        if dp.count(os.sep) - root.count(os.sep) >= depth:
            ds[:] = []
        dirs += [os.path.join(dp, d) for d in ds]
    def score(n, a):
        if n == a:
            return 30 + len(a)
        rest = n[len(a):]
        if n.startswith(a) and re.sub(r"\d+", "", rest) in _FILLER and not rest.isdigit():
            return 20 + len(a)
        if len(a) >= 6 and a in n:
            return 10 + len(a)          # longer names win: 'gameboyadvance' beats 'gameboy' inside the same folder name
        return 0
    owner = {}                          # each folder goes to the system it matches best
    for d in dirs:
        n = _norm(os.path.basename(d))
        ranked = sorted(((max(score(n, a) for a in al), k) for k, al in ALIASES.items() if k in platforms), reverse=True)
        if ranked and ranked[0][0]:
            owner[d] = ranked[0]
    out = {}
    for k in ALIASES:
        if k not in platforms:
            continue
        exts = platforms[k][3]
        best = None
        for d, (sc, kk) in owner.items():
            if kk != k:
                continue
            score_ = sc
            files = 0
            for dp, ds, fs in os.walk(d):
                files += sum(1 for f in fs if os.path.splitext(f)[1].lower() in exts)
                if files > 50:
                    break
            if files and (best is None or (score_, files) > best[:2]):
                best = (score_, files, os.path.relpath(d, root))
        if best:
            out[k] = best[2]
    return out


TV_LABELS = {"TV1": "Late-80s Toshiba, Grey", "TV2": "Late-80s Toshiba, Dark", "TV3": "Early-90s Grey TV",
             "TV4": "90s Samsung, Silver", "TV5": "80s RCA Wood Cabinet, US", "TV6": "70s HMV Wood Cabinet, UK",
             "TV6 alt": "70s HMV, Other Room"}
STYLE_LABELS = {"sony megatron": "Sony Megatron, Needs HDR", "composite tv": "Composite TV", "easymode": "Easymode, Crisp",
                "glass frame": "Glass Frame", "smooth": "Smoothed", "super-xbr": "Super-xBR Smoothing"}


def shu_case(s):
    """Every word capitalised; words with capitals or digits (TV, 3DS, 1084S, xBR) are left as they are."""
    return " ".join(w if any(c.isupper() or c.isdigit() for c in w) else w[:1].upper() + w[1:] for w in s.split(" "))


def look_label(raw):
    """One consistent, readable name for every look in the gallery, whatever the preset file is called."""
    import re
    s = raw.strip()
    if s.startswith(("CURRENT", "APPLIED")):
        return "Your Current Look"
    if s.startswith("Plain CRT frame"):
        return "Plain CRT"
    m = re.match(r"Plain frame, style: (.*)", s)
    if m:
        st = m.group(1).lower()
        return "Plain CRT: " + next((v for k, v in STYLE_LABELS.items() if st.startswith(k)), shu_case(m.group(1)))
    m = re.match(r"(TV\d(?: alt)?): (.*)", s)
    if m:
        rest = m.group(2)
        extras = [p for p in re.findall(r"\(([^)]*)\)", rest) if p.lower() not in ("uk", "us", "grey", "dark", "combo")]
        if " - " in rest:
            extras.append(rest.split(" - ", 1)[1])
        if "super-xBR" in rest:
            extras.append("Super-xBR Combo")
        return f"{m.group(1).replace(' alt', ' Alt')}: {TV_LABELS.get(m.group(1), shu_case(rest))}" + "".join(f", {shu_case(x)}" for x in extras)
    m = re.match(r"(Commodore 1084S?|Philips TV)(?: monitor)?,? (.*)", s)
    if m:
        kind = "ScaleFX" if "ScaleFX" in s else "Smoothed" if "smooth" in s else "Sharp"
        return f"{m.group(1)}{' Monitor' if 'Commodore' in m.group(1) else ''}, {kind}"
    if ":" in s:
        system, look = [x.strip() for x in s.split(":", 1)]
        system = system.replace(" DREZ", "")
        if look.startswith(("Bezel", "Monitor")):
            return f"{system}: {look.split(',')[0]}"
        tokens = re.findall(r"\[([^\]]+)\]", look)
        base = look.split("-[")[0].replace("_", " ").split()
        sys_words = system.lower().split(); sys_flat = system.lower().replace(" ", "")
        initials = "".join(x[0] for x in sys_words)
        variant = [w for w in base if w.lower() not in sys_words and w.lower() not in sys_flat
                   and w.lower() != initials]   # drop the system's own name or initials (NGPC)
        kind = "Handheld, LCD Screen" if "LCD-GRID" in tokens else "Mono Monitor" if "Monochrome_Monitor" in tokens else \
               "Monitor" if "Monitor" in tokens else "Console Frame"
        parts = [kind] + ([" ".join(variant)] if variant else [])
        if "DREZ" in tokens:
            parts.append("Hi-Res" + "".join(f" {t}" for t in tokens if re.match(r"\d+[pX]$", t)))
        if "flipped" in look:
            parts.append("Flipped")
        return f"{system}: " + ", ".join(shu_case(p) for p in parts)
    return shu_case(s)


LEVELS = {
    "Lite": "Library + LaunchBox's own artwork + the CRT/TV looks.",
    "Standard": "Lite, plus extra covers and screenshots from libretro and ArcadeDB, 3D boxes, playlists, menu icons.",
    "Ultimate": "Standard, plus ZX Spectrum inlays, loading and in-game screens (needs the ZXDB dump in your work folder).",
}


# ---- the looks: our per-emulator presets, combos generated from the user's own Duimon install ------------------
def install_looks(s, log, cores=None):
    """cores: RetroArch config folder names to install for (None = all)."""
    src_root = os.path.join(CONFIGS, "retroarch")
    ra_cfg = os.path.join(P(s, "retroarch"), "config")
    sh = shaders(s)
    if not os.path.isdir(src_root):
        log("No configs/retroarch folder in this copy - skipping the looks."); return
    made = 0
    for core in sorted(os.listdir(src_root)):
        if cores is not None and core.lower() not in {c.lower() for c in cores}:
            continue
        for f in glob.glob(os.path.join(src_root, core, "*.slangp")):
            text = open(f, encoding="utf-8").read()
            ok = True
            for line in text.splitlines():
                if line.startswith("#reference"):
                    ref = line.split('"')[1]
                    target = os.path.normpath(os.path.join(ra_cfg, core, ref))
                    if not os.path.exists(target) and not make_combo(target, log):
                        log(f"  {core}: needs {os.path.relpath(target, sh)} - install that pack first"); ok = False
            if ok:
                dst = os.path.join(ra_cfg, core, os.path.basename(f))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst) and not os.path.exists(dst + ".bak_wizard"):
                    shutil.copy2(dst, dst + ".bak_wizard")
                shutil.copy2(f, dst); made += 1
    log(f"Looks installed for {made} emulator cores (old presets kept as .bak_wizard).")


def light_variant(ref):
    """The lighter (Mega Bezel STANDARD) version of an ADVANCED preset path, or None if the pack has none."""
    import re
    cands = []
    if "/Presets/Advanced/" in ref or "[ADV]" in ref:
        std = ref.replace("/Presets/Advanced/", "/Presets/Standard/").replace("[ADV]", "[STD]")
        cands += [std, re.sub(r"-\[S\d+\]", "", std)]                      # our super-xBR combos have no STD twin: plain STD TV
    for heavy in ("MBZ_SHARP_ADV", "MBZ_SHARP_SMOOTH", "NMC_SHARP_SMOOTH-SCALEFX"):   # TheNamec Commodore pack
        if heavy in ref:
            cands.append(ref.replace(heavy, "MBZ_SHARP_STD"))
    m = re.search(r"MBZ__\d__[A-Z0-9-]*ADV[A-Z0-9-]*__([A-Z-]+)\.slangp", ref)
    if m:
        cands.append(ref[:m.start()] + f"MBZ__3__STD__{m.group(1)}.slangp")
    return cands


def apply_light(s, cores, log):
    """Point each installed core preset at the STANDARD version of its look (lighter on the graphics card)."""
    ra_cfg = os.path.join(P(s, "retroarch"), "config"); done = 0
    for core in cores:
        p = os.path.join(ra_cfg, core, core + ".slangp")
        if not os.path.exists(p):
            continue
        lines = open(p, encoding="utf-8").read().splitlines(); changed = False
        for i, l in enumerate(lines):
            if l.startswith("#reference"):
                ref = l.split('"')[1]
                for c in light_variant(ref):
                    if os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), c))):
                        lines[i] = f'#reference "{c}"'; changed = True; break
        if changed:
            open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n"); done += 1
        else:
            log(f"  {core}: no lighter version of this look, kept as is")
    log(f"Light mode: {done} looks switched to Mega Bezel Standard.")


def detect_gpu():
    """'Light' on built-in graphics (Intel, AMD Radeon Graphics APUs), 'Full' otherwise or if unknown."""
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_VideoController).Name"],
                             capture_output=True, text=True, timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except Exception:
        return "Full", ""
    names = [n.strip() for n in out.splitlines() if n.strip()]
    dedicated = [n for n in names if any(x in n for x in ("NVIDIA", "GeForce", "RTX", "GTX", "Radeon RX", "Arc A", "Arc B"))]
    return ("Full" if dedicated or not names else "Light"), ", ".join(names)


def set_artpath(s, log):
    """Arcade cabinets: MAME uses the first artwork folder that has a game, so order them best first."""
    mame = P(s, "mame"); ini = os.path.join(mame, "mame.ini")
    if not os.path.exists(ini):
        log("No mame.ini yet - run MAME once (or 'mame -createconfig') and run the build again."); return
    order = [d for d in ("artwork_lightsout", "artwork_realistic", "artwork_bezelproject") if os.path.isdir(os.path.join(mame, d))]
    order.append("artwork")
    lines = open(ini, encoding="utf-8", errors="replace").read().splitlines()
    if not os.path.exists(ini + ".bak_wizard"):
        shutil.copy2(ini, ini + ".bak_wizard")
    out = [f"{'artpath':<26}{';'.join(order)}" if l.startswith("artpath ") else l for l in lines]
    open(ini, "w", encoding="utf-8").write("\n".join(out) + "\n")
    log("MAME artwork order: " + " > ".join(order))


def make_combo(target, log):
    """'TV4-[ADV]-[Guest]-[S13].slangp' = Duimon's TV4-[ADV]-[Guest] with its CRT switched to local shader 13
    (super-xBR + Guest). Made here from your own copy of the pack; Duimon's licence does not allow us to ship it."""
    name = os.path.basename(target)
    if "-[S" not in name:
        return False
    base = name[:name.rindex("-[S")] + ".slangp"
    num = name[name.rindex("-[S") + 3:name.rindex("]")]
    src = os.path.join(os.path.dirname(target), base)
    if not os.path.exists(src):
        return False
    old = '#reference "../../../zzz_global_params/Base_Shader/'
    lines = [f'#reference "../../../zzz_global_params/Local_Shader/ADV_{num}.slangp"' if l.startswith(old) else l
             for l in open(src, encoding="utf-8").read().splitlines()]
    open(target, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    log(f"  made {name} from your Duimon {base}")
    return True


# ---- the window ------------------------------------------------------------------------------------------------
class Wizard(tk.Tk):
    def __init__(self):
        try:   # crisp on 4K / high-DPI screens instead of Windows stretching a blurry bitmap
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        super().__init__()
        self.title(TITLE); self.configure(bg=BG)
        scale = self.winfo_fpixels("1i") / 96.0
        self.geometry(f"{int(1100 * scale)}x{int(800 * scale)}"); self.minsize(int(900 * scale), int(660 * scale))
        self.ui = scale
        self.s = load_settings()
        st = ttk.Style(self); st.theme_use("clam")
        st.configure(".", background=BG, foreground=FG, font=("Segoe UI", 11))
        st.configure("TFrame", background=BG); st.configure("Panel.TFrame", background=PANEL)
        st.configure("TLabel", background=BG, foreground=FG); st.configure("Muted.TLabel", foreground=MUTED)
        st.configure("Panel.TLabel", background=PANEL); st.configure("H.TLabel", font=("Segoe UI Semibold", 20), foreground=ACCENT)
        st.configure("TButton", padding=(18, 8), background=PANEL, foreground=FG, bordercolor="#3a3f48", focuscolor=PANEL)
        st.map("TButton", background=[("active", "#2a2f37"), ("disabled", BG)], foreground=[("disabled", "#555a61")])
        st.configure("Accent.TButton", background=ACCENT, foreground="#14161a", bordercolor=ACCENT)
        st.map("Accent.TButton", background=[("active", "#e8b65a")])
        st.configure("TEntry", fieldbackground=PANEL, foreground=FG, insertcolor=FG, bordercolor="#3a3f48")
        st.configure("TCheckbutton", background=BG, foreground=FG)
        st.configure("TRadiobutton", background=BG, foreground=FG); st.configure("Horizontal.TProgressbar", background=ACCENT)
        self.imgs = {}
        self.body = ttk.Frame(self, padding=24); self.body.pack(fill="both", expand=True)
        nav = ttk.Frame(self, padding=(24, 0, 24, 18)); nav.pack(fill="x")
        self.back = ttk.Button(nav, text="Back", command=lambda: self.go(-1)); self.back.pack(side="left")
        credit = ttk.Frame(nav); credit.pack(side="left", padx=30)   # small logos + link on every page
        for name, h in (("shu_logo.png", 30), ("anima_logo.png", 22)):
            im = self.logo(name, h)
            if im:
                tk.Label(credit, image=im, bg=BG).pack(side="left", padx=6)
        ttk.Label(credit, text="Built by Shu and Anima", style="Muted.TLabel").pack(side="left", padx=8)
        link = tk.Label(credit, text="shuhq.com", fg=ACCENT, bg=BG, cursor="hand2", font=("Segoe UI", 10, "underline"))
        link.pack(side="left"); link.bind("<Button-1>", lambda e: webbrowser.open("https://shuhq.com"))
        self.next = ttk.Button(nav, text="Next", style="Accent.TButton", command=lambda: self.go(1)); self.next.pack(side="right")
        self.step = ttk.Label(nav, style="Muted.TLabel"); self.step.pack(side="right", padx=16)
        self.pages = [self.p_welcome, self.p_folders, self.p_parts, self.p_systems, self.p_looks, self.p_build, self.p_done]
        self.i = 0; self.show()

    def logo(self, name, height):
        """Logo from assets/, scaled to a height; None if the file or Pillow is missing."""
        key = (name, height)
        if key not in self.imgs:
            try:
                from PIL import Image, ImageTk
                im = Image.open(os.path.join(ASSETS, name)).convert("RGBA")
                height = int(height * self.ui)
                im = im.resize((max(1, int(im.width * height / im.height)), height), Image.LANCZOS)
                self.imgs[key] = ImageTk.PhotoImage(im)
            except Exception:
                self.imgs[key] = None
        return self.imgs[key]

    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def header(self, title, sub):
        ttk.Label(self.body, text=title, style="H.TLabel").pack(anchor="w")
        ttk.Label(self.body, text=sub, style="Muted.TLabel", wraplength=int(1000 * self.ui), justify="left").pack(anchor="w", pady=(4, 16))

    def show(self):
        self.clear(); self.pages[self.i]()
        self.back.state(["!disabled"] if 0 < self.i < len(self.pages) - 1 else ["disabled"])
        self.next.configure(text="Finish" if self.i == len(self.pages) - 1 else "Next")
        self.step.configure(text=f"Step {self.i + 1} of {len(self.pages)}")

    def go(self, d):
        if d > 0 and self.i == 0:
            if not self.agree.get():
                messagebox.showwarning(TITLE, "Please tick the box to confirm you'll use your own games and BIOS files."); return
            self.s["_agreed"] = True
        if d > 0 and self.i == 1 and not self.save_folders():
            return
        if self.i == len(self.pages) - 1 and d > 0:
            self.destroy(); return
        self.i = max(0, min(len(self.pages) - 1, self.i + d)); self.show()

    # 1 -------------------------------------------------------------------------------------------------------
    def banner_source(self):
        """(image path, credit line). Once the user has rendered previews, their own game on the HMV TV6 is used;
        before that, the shipped picture (Pressure Cooker on Duimon's TV6)."""
        rd = self.review_dir() if self.s.get("work_dir") or self.s.get("review_dir") else ""
        logs = sorted(glob.glob(os.path.join(rd, "*", "log.json"))) if rd else []
        logs.sort(key=lambda p: os.path.basename(os.path.dirname(p)) != "2600")       # an Atari 2600 render first
        for lp in logs:
            try:
                log = json.load(open(lp, encoding="utf-8"))
            except Exception:
                continue
            for sh in log.get("shots", []):
                if sh.get("ok") and sh.get("label") == "Duimon TV6":
                    f = os.path.join(os.path.dirname(lp), f"{sh['n']:02d}_full.jpg")
                    if os.path.exists(f):
                        return f, f"Your {log.get('game', 'game')} ({log.get('system', '')}) on Duimon's TV6 HMV cabinet"
        f = os.path.join(ASSETS, "welcome_tv.jpg")
        return (f, "Pressure Cooker (Activision, 1983) on Duimon's TV6 HMV cabinet") if os.path.exists(f) else (None, "")

    def banner(self, width, height):
        """Close in on the TV glass, title on its lower edge, fading into the page so the words can sit underneath."""
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageTk
        except Exception:
            return None, ""
        path, credit = self.banner_source()
        if not path:
            return None, ""
        src = Image.open(path).convert("RGB")
        W, H = src.size
        cw = W * 0.79                                   # crop: the glass plus the inside edge of the cabinet
        ch = cw * height / width
        cx, cy = W * 0.50, H * 0.475                    # centre of the TV6 screen
        box = (int(cx - cw / 2), int(max(0, cy - ch / 2)), int(cx + cw / 2), int(min(H, cy + ch / 2)))
        im = src.crop(box).resize((width, height), Image.LANCZOS)
        bg = tuple(int(BG[i:i + 2], 16) for i in (1, 3, 5))
        fade = Image.new("L", (1, height))               # bottom 45% fades into the window colour
        for y in range(height):
            t = max(0.0, (y / (height - 1) - 0.55) / 0.45)
            fade.putpixel((0, y), int(255 * min(1.0, t ** 1.4)))
        im = Image.composite(Image.new("RGB", im.size, bg), im, fade.resize(im.size))
        d = ImageDraw.Draw(im)
        def font(name, size):
            for f in (name, "segoeuib.ttf", "segoeui.ttf"):
                try:
                    return ImageFont.truetype(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", f), size)
                except Exception:
                    continue
            return ImageFont.load_default()
        k = self.ui
        f = font("segoeuib.ttf", int(54 * k))
        x, y = int(36 * k), height - int(78 * k)
        first, gold = NAME[:NAME.index("4K")], NAME[NAME.index("4K"):]
        d.text((x, y), first, font=f, fill=(233, 230, 223))
        d.text((x + d.textlength(first, font=f), y), gold, font=f, fill=(217, 164, 65))
        self.imgs["banner"] = ImageTk.PhotoImage(im)
        return self.imgs["banner"], credit

    def p_welcome(self):
        k = self.ui
        pic, credit = self.banner(int(1100 * k) - 48, int(590 * k))
        if pic:
            tk.Label(self.body, image=pic, bg=BG, bd=0).pack(anchor="w")
        else:
            ttk.Label(self.body, text="Shu's LaunchBox 4K CRT Build", style="H.TLabel").pack(anchor="w")
        under = tk.Frame(self.body, bg=BG); under.pack(fill="x", padx=int(36 * k))
        tk.Label(under, text="Builds your LaunchBox library from your own games, with each system shown on a period TV or monitor.",
                 bg=BG, fg="#c9c4b8", font=("Segoe UI", 13), wraplength=int(980 * k), justify="left").pack(anchor="w", pady=(2, 16))
        agree = tk.Frame(under, bg=BG); agree.pack(fill="x")
        self.agree = tk.BooleanVar(value=self.s.get("_agreed", False))
        tk.Checkbutton(agree, variable=self.agree, bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG, activeforeground=FG,
                       font=("Segoe UI", 11), text="I'll only use games and BIOS files I own and dumped myself, or that are legally free."
                       ).pack(side="left")
        disc = os.path.join(os.path.dirname(HERE), "DISCLAIMER.md")
        lk = tk.Label(agree, text="Read the disclaimer", fg=ACCENT, bg=BG, cursor="hand2", font=("Segoe UI", 10, "underline"))
        lk.pack(side="left", padx=16); lk.bind("<Button-1>", lambda e: os.startfile(disc) if os.path.exists(disc) else None)
        foot = tk.Frame(under, bg=BG); foot.pack(fill="x", pady=(12, 0))
        tk.Label(foot, text="Close LaunchBox before the build step. It rewrites its data when it exits.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(side="left")
        if credit:
            tk.Label(foot, text=credit, bg=BG, fg="#6f6e69", font=("Segoe UI", 9)).pack(side="right")

    # 2 -------------------------------------------------------------------------------------------------------
    def p_folders(self):
        self.header("Your folders", "Point at your own folders. Auto-find looks in the usual places on every drive.")
        self.vars = {}
        rows = [("emulation_root", "Emulation folder (holds your ROM folders)"), ("launchbox", "LaunchBox folder (has LaunchBox.exe)"),
                ("retroarch", "RetroArch folder (has retroarch.exe)"), ("mame", "MAME folder (has mame.exe)"),
                ("work_dir", "Work folder (logs, backups, previews)")]
        grid = ttk.Frame(self.body); grid.pack(fill="x")
        for r, (k, label) in enumerate(rows):
            ttk.Label(grid, text=label).grid(row=r, column=0, sticky="w", pady=6)
            v = tk.StringVar(value=self.s.get(k, "")); self.vars[k] = v
            ttk.Entry(grid, textvariable=v, width=70).grid(row=r, column=1, padx=8)
            ttk.Button(grid, text="Browse", command=lambda v=v: v.set(filedialog.askdirectory() or v.get())).grid(row=r, column=2)
        ttk.Button(self.body, text="Auto-find", command=self.autofind).pack(anchor="w", pady=14)

    def autofind(self):
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        found = {}
        for d in drives:
            for pat, key, up in (("LaunchBox.exe", "launchbox", 0), ("retroarch.exe", "retroarch", 0), ("mame.exe", "mame", 0)):
                for depth in ("*", "*/*", "*/*/*", "*/*/*/*"):
                    hits = glob.glob(os.path.join(d, depth, pat))
                    if hits and key not in found:
                        found[key] = os.path.dirname(hits[0]); break
        for k, v in found.items():
            if not self.vars[k].get():
                self.vars[k].set(v)
        if found.get("launchbox") and not self.vars["emulation_root"].get():
            self.vars["emulation_root"].set(os.path.dirname(found["launchbox"]))
        messagebox.showinfo(TITLE, "Found: " + (", ".join(found) or "nothing - use Browse"))

    def save_folders(self):
        for k, v in self.vars.items():
            self.s[k] = v.get().strip()
        if not self.s.get("launchbox") or not os.path.isdir(self.s["launchbox"]):
            messagebox.showwarning(TITLE, "Please set your LaunchBox folder."); return False
        self.s.setdefault("work_dir", os.path.join(self.s.get("emulation_root") or HERE, "_build"))
        json.dump(self.s, open(SETTINGS, "w", encoding="utf-8"), indent=2)
        return True

    # 3 -------------------------------------------------------------------------------------------------------
    def p_parts(self):
        self.header("What you need", "Ticks show what's already installed. Open each page to download it from the official source, "
                    "install it, then press Refresh. Starred items are needed; the rest add systems or extras.")
        canvas = tk.Canvas(self.body, bg=BG, highlightthickness=0); sb = ttk.Scrollbar(self.body, command=canvas.yview)
        inner = ttk.Frame(canvas); inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw"); canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        for r, (name, why, url, check, req) in enumerate(PARTS):
            try:
                ok = check(self.s)
            except Exception:
                ok = False
            tk.Label(inner, text="✓" if ok else "✗", fg=OK if ok else BAD, bg=BG, font=("Segoe UI", 14, "bold")).grid(row=r, column=0, padx=(0, 10), pady=5)
            ttk.Label(inner, text=name + (" *" if req else ""), font=("Segoe UI Semibold", 11)).grid(row=r, column=1, sticky="w")
            ttk.Label(inner, text=why, style="Muted.TLabel", wraplength=int(560 * self.ui), justify="left").grid(row=r, column=2, sticky="w", padx=12)
            ttk.Button(inner, text="Open page", command=lambda u=url: webbrowser.open(u)).grid(row=r, column=3)
            if name in DOWNLOADS and not ok:
                b = ttk.Button(inner, text="Download", style="Accent.TButton", command=lambda n=name: self.download(n))
                b.grid(row=r, column=4, padx=(8, 0))
                ttk.Label(inner, text=DOWNLOADS[name][3], style="Muted.TLabel").grid(row=r, column=5, padx=(8, 0), sticky="w")
        self.dl_status = ttk.Label(self.body, style="Muted.TLabel"); self.dl_status.place(relx=0.0, rely=1.0, anchor="sw")
        ttk.Button(self.body, text="Refresh", command=lambda: (_EXES.clear(), self.show())).place(relx=1.0, rely=0.0, anchor="ne")

    def download(self, part):
        if getattr(self, "_dl_busy", False):
            messagebox.showinfo(TITLE, "One download at a time - wait for the current one to finish."); return
        if not os.path.isdir(P(self.s, "retroarch")):
            messagebox.showwarning(TITLE, "Set your RetroArch folder on the Folders page first."); return
        self._dl_busy = True; page = self.i

        def status(text):
            self.after(0, lambda: self.dl_status.configure(text=text) if self.dl_status.winfo_exists() else None)

        def work():
            try:
                ok = fetch_pack(self.s, part, status, status, lambda: self.i != page)
            except Exception as e:
                ok = False; status(f"{part}: download failed ({e}). Use Open page to get it by hand.")
            self._dl_busy = False
            if ok:
                self.after(0, lambda: self.show() if self.i == page else None)
        threading.Thread(target=work, daemon=True).start()

    # 4 -------------------------------------------------------------------------------------------------------
    def p_systems(self):
        self.header("Systems, folders and detail", "Systems with games in their folder are ticked. If a system shows no files, "
                    "press Change and pick the folder that holds its games. Untick any system you don't want.")
        sys.path.insert(0, HERE)
        for m in ("lbconfig", "lb_build"):
            sys.modules.pop(m, None)
        argv = sys.argv; sys.argv = [argv[0]]
        try:
            import lb_build
        finally:
            sys.argv = argv
        self.lb = lb_build
        lv = ttk.Frame(self.body); lv.pack(side="bottom", fill="x", pady=(14, 0))
        canvas = tk.Canvas(self.body, bg=BG, highlightthickness=0); sb = ttk.Scrollbar(self.body, command=canvas.yview)
        grid = ttk.Frame(canvas); grid.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid, anchor="nw"); canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units") if canvas.winfo_exists() else None)
        self.sysvars, self.sysrows = {}, {}
        for r, (k, (name, cat, folders, exts, emu, core)) in enumerate(lb_build.PLATFORMS.items()):
            v = tk.BooleanVar(); self.sysvars[k] = v
            ttk.Checkbutton(grid, text=name, variable=v).grid(row=r, column=0, sticky="w", pady=1)
            cnt = ttk.Label(grid, style="Muted.TLabel"); cnt.grid(row=r, column=1, sticky="e", padx=(16, 16))
            ttk.Button(grid, text="Change", command=lambda k=k: self.pick_rom_folder(k)).grid(row=r, column=2, padx=(0, 16), pady=1)
            fol = ttk.Label(grid, style="Muted.TLabel"); fol.grid(row=r, column=3, sticky="w")
            self.sysrows[k] = (cnt, fol)
            self.refresh_system(k, folders, tick=True)
        self.level = tk.StringVar(value=self.s.get("_level", "Standard"))
        for name, desc in LEVELS.items():
            ttk.Radiobutton(lv, text=f"{name} - {desc}", value=name, variable=self.level).pack(anchor="w", pady=2)
        if "_gpu" not in self.s:
            self.s["_gpu"], self.gpu_name = detect_gpu()
        gp = ttk.Frame(lv); gp.pack(anchor="w", pady=(8, 0))
        self.gpu = tk.StringVar(value=self.s["_gpu"])
        ttk.Label(gp, text="Graphics:").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(gp, text="Full looks (gaming graphics card)", value="Full", variable=self.gpu).pack(side="left")
        ttk.Radiobutton(gp, text="Light looks (laptops and built-in graphics)", value="Light", variable=self.gpu).pack(side="left", padx=14)
        if getattr(self, "gpu_name", ""):
            ttk.Label(gp, text=f"found: {self.gpu_name}", style="Muted.TLabel").pack(side="left", padx=10)

    def count_files(self, folders, exts):
        count = 0
        for f in folders:
            for dp, dirs, files in os.walk(os.path.join(self.lb.ROOT, f)):
                dirs[:] = [d for d in dirs if not d.startswith("_")]
                count += sum(1 for x in files if os.path.splitext(x)[1].lower() in exts)
                if count > 999:
                    return count
        return count

    def refresh_system(self, k, folders, tick=False):
        exts = self.lb.PLATFORMS[k][3]
        n = self.count_files(folders, exts)
        auto = False
        if not n and tick and k not in self.s.get("rom_folders", {}):
            if getattr(self, "_guess", None) is None:
                self._guess = guess_folders(self.lb.ROOT, self.lb.PLATFORMS) if self.lb.ROOT and os.path.isdir(self.lb.ROOT) else {}
            g = self._guess.get(k)
            if g:
                folders = [g]; n = self.count_files(folders, exts); auto = n > 0
                if auto:
                    self.s.setdefault("rom_folders", {})[k] = [g]
                    p = self.lb.PLATFORMS[k]; self.lb.PLATFORMS[k] = p[:2] + ([g],) + p[3:]
                    json.dump(self.s, open(SETTINGS, "w", encoding="utf-8"), indent=2)
        cnt, fol = self.sysrows[k]
        cnt.configure(text=("1000+" if n > 999 else str(n)) + " files", foreground=FG if n else MUTED)
        shown = [f for f in folders if os.path.isdir(os.path.join(self.lb.ROOT, f))] or folders
        fol.configure(text=("; ".join(shown) + ("   (found automatically)" if auto else "")) if n else "no games found in " + "; ".join(shown))
        if tick or n:
            self.sysvars[k].set(n > 0)

    def pick_rom_folder(self, k):
        """Point a system at the folder holding its games. Saved straight away as rom_folders in lb_settings.json:
        relative to the emulation folder when it sits inside it, otherwise the full path."""
        d = filedialog.askdirectory(title=f"Folder with your {self.lb.PLATFORMS[k][0]} games", initialdir=self.lb.ROOT or None)
        if not d:
            return
        d = os.path.normpath(d)
        root = os.path.normpath(self.lb.ROOT) if self.lb.ROOT else ""
        rel = os.path.relpath(d, root) if root and os.path.splitdrive(d)[0].lower() == os.path.splitdrive(root)[0].lower() else d
        if rel.startswith(".."):
            rel = d
        self.s.setdefault("rom_folders", {})[k] = [rel]
        p = self.lb.PLATFORMS[k]
        self.lb.PLATFORMS[k] = p[:2] + ([rel],) + p[3:]
        json.dump(self.s, open(SETTINGS, "w", encoding="utf-8"), indent=2)
        self.refresh_system(k, [rel])

    # 5 -------------------------------------------------------------------------------------------------------
    def p_looks(self):
        self.header("Pick your looks", "Every system can sit in its own TV, monitor or handheld. Press Render and the wizard boots "
                    "one game per system from your collection and pictures it in every look. Then press Choose next to a system "
                    "and click the look you want. Systems you leave alone get Anima's pick. Rendering needs the shader packs "
                    "from step 3 and takes a few minutes per system.")
        bar = ttk.Frame(self.body); bar.pack(fill="x")
        self.rbtn = ttk.Button(bar, text="Render previews from my games", command=self.render_previews); self.rbtn.pack(side="left")
        self.cancel_btn = ttk.Button(bar, text="Cancel", command=self.cancel); self.cancel_btn.pack(side="left", padx=(10, 0))
        self.cancel_btn.state(["disabled"])
        ttk.Button(bar, text="Open previews in browser", command=self.open_previews).pack(side="left", padx=10)
        self.logbox = tk.Text(self.body, bg=PANEL, fg=FG, font=("Consolas", 10), wrap="word", relief="flat", height=6)
        self.logbox.pack(side="bottom", fill="x", pady=(10, 0))
        self.looks_frame = ttk.Frame(self.body); self.looks_frame.pack(fill="both", expand=True, pady=(12, 0))
        self.fill_looks()
        self.q = queue.Queue(); self.after(150, self.pump)

    def selected(self):
        return [k for k, v in getattr(self, "sysvars", {}).items() if v.get()]

    def review_log(self, rk):
        try:
            return json.load(open(os.path.join(self.review_dir(), rk, "log.json"), encoding="utf-8"))
        except Exception:
            return None

    def anima_pick(self, rk, shots):
        """Shot number of the look the build installs for this system: the candidate whose preset is the one in our
        shipped configs (our super-xBR combos count as their plain TV). Falls back to bezel_review's PICKS list."""
        import re
        br = self.bezel()
        core = br.SYSTEMS.get(rk, (None,) * 6)[5]
        f = os.path.join(CONFIGS, "retroarch", core or "", f"{core}.slangp")
        if core and os.path.exists(f):
            ref = next((l.split('"')[1] for l in open(f, encoding="utf-8") if l.startswith("#reference")), "")
            want = re.sub(r"-\[S\d+\]", "", os.path.basename(ref)).lower()
            folder = os.path.basename(os.path.dirname(ref)).lower()   # e.g. TheNamec's NMC_SHARP_SMOOTH-SCALEFX vs MBZ_SHARP_ADV
            hits = [s for s in shots if os.path.basename(s["preset"]).lower() == want]
            if len(hits) > 1:
                hits = [s for s in hits if folder in s["preset"].lower().replace("\\", "/")] or hits
            if hits:
                return hits[0]["n"]
        pk = br.PICKS.get(rk, "")
        return next((s["n"] for s in shots if pk and pk in s["label"]), None)

    def look_choice(self, rk, log):
        """(shot number, label, is_user_pick) for a system: the user's pick if made, else Anima's pick."""
        br = self.bezel()
        shots = [s for s in log.get("shots", []) if s.get("ok")]
        mine = self.s.get("looks", {}).get(rk)
        for s in shots:
            if s["n"] == mine:
                return s["n"], look_label(br.nice(s["label"])), True
        n = self.anima_pick(rk, shots)
        for s in shots:
            if s["n"] == n:
                return s["n"], look_label(br.nice(s["label"])), False
        return None, "its standard look", False

    def bezel(self):
        if getattr(self, "_br", None) is None:
            sys.path.insert(0, HERE)
            argv = sys.argv; sys.argv = [argv[0]]
            try:
                import bezel_review as br
            finally:
                sys.argv = argv
            self._br = br
        return self._br

    def thumb(self, path, width):
        from PIL import Image, ImageTk
        key = (path, width, os.path.getmtime(path))
        if key not in self.imgs:
            im = Image.open(path).convert("RGB"); w = int(width * self.ui)
            self.imgs[key] = ImageTk.PhotoImage(im.resize((w, int(im.height * w / im.width)), Image.LANCZOS))
        return self.imgs[key]

    def fill_looks(self):
        """One row per ticked system: its current look (thumbnail + name) and a Choose button once previews exist."""
        if not getattr(self, "looks_frame", None) or not self.looks_frame.winfo_exists():
            return
        for w in self.looks_frame.winfo_children():
            w.destroy()
        canvas = tk.Canvas(self.looks_frame, bg=BG, highlightthickness=0); sb = ttk.Scrollbar(self.looks_frame, command=canvas.yview)
        inner = ttk.Frame(canvas); inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw"); canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units") if canvas.winfo_exists() else None)
        names = self.lb.PLATFORMS if getattr(self, "lb", None) else {}
        rows = [(k, LOOK_KEYS[k]) for k in self.selected() if k in LOOK_KEYS]
        if not rows:
            ttk.Label(inner, text="None of the systems you ticked has a choice of looks.", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        for r, (k, rk) in enumerate(rows):
            name = names[k][0] if k in names else k
            log = self.review_log(rk)
            ttk.Label(inner, text=name, font=("Segoe UI Semibold", 11)).grid(row=r, column=0, sticky="w", pady=6, padx=(0, 18))
            if not log:
                ttk.Label(inner, text="Anima's Pick (Render To See And Change It)", style="Muted.TLabel").grid(row=r, column=2, sticky="w")
                continue
            n, label, mine = self.look_choice(rk, log)
            img = os.path.join(self.review_dir(), rk, f"{n:02d}.jpg") if n else ""
            if img and os.path.exists(img):
                tk.Label(inner, image=self.thumb(img, 150), bg=BG, bd=0).grid(row=r, column=1, padx=(0, 14), pady=4)
            ttk.Label(inner, text=("Your Pick: " if mine else "Anima's Pick: ") + label,
                      style="TLabel" if mine else "Muted.TLabel").grid(row=r, column=2, sticky="w")
            ttk.Button(inner, text="Choose", command=lambda k=k, rk=rk: self.choose_look(k, rk)).grid(row=r, column=3, padx=(18, 0))

    def choose_look(self, k, rk):
        """Gallery of every look rendered for this system; click one to pick it."""
        log = self.review_log(rk)
        if not log:
            return
        br = self.bezel()
        cur, _, _ = self.look_choice(rk, log)
        top = tk.Toplevel(self); top.configure(bg=BG); top.title(f"{log.get('system', k)} - pick a look")
        top.geometry(f"{int(1240 * self.ui)}x{int(820 * self.ui)}"); top.transient(self); top.grab_set()
        ttk.Label(top, text=f"{log.get('system', k)}: {log.get('game', '')} in every look. Click the one you want.",
                  font=("Segoe UI Semibold", 13), foreground=ACCENT, background=BG).pack(anchor="w", padx=20, pady=(16, 8))
        canvas = tk.Canvas(top, bg=BG, highlightthickness=0); sb = ttk.Scrollbar(top, command=canvas.yview)
        inner = ttk.Frame(canvas); inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw"); canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=(0, 16)); sb.pack(side="right", fill="y")
        top.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        def pick(n):
            self.s.setdefault("looks", {})[rk] = n
            json.dump(self.s, open(SETTINGS, "w", encoding="utf-8"), indent=2)
            top.destroy(); self.fill_looks()
        shots = [s for s in log.get("shots", []) if s.get("ok")]
        anima_n = self.anima_pick(rk, shots)
        for i, s in enumerate(shots):
            img = os.path.join(self.review_dir(), rk, f"{s['n']:02d}.jpg")
            if not os.path.exists(img):
                continue
            cell = tk.Frame(inner, bg=PANEL if s["n"] == cur else BG, padx=6, pady=6, cursor="hand2")
            cell.grid(row=i // 3, column=i % 3, padx=6, pady=6, sticky="n")
            pic = tk.Label(cell, image=self.thumb(img, 360), bg=cell["bg"], bd=0); pic.pack()
            tag = ("Anima's Pick  ·  " if s["n"] == anima_n else "") + look_label(br.nice(s["label"]))
            cap = tk.Label(cell, text=tag, bg=cell["bg"], fg=ACCENT if s["n"] == cur else FG, font=("Segoe UI", 10),
                           wraplength=int(360 * self.ui), justify="left"); cap.pack(anchor="w", pady=(4, 0))
            for wdg in (cell, pic, cap):
                wdg.bind("<Button-1>", lambda e, n=s["n"]: pick(n))

    def review_dir(self):
        return P(self.s, "review_dir") or os.path.join(P(self.s, "work_dir"), "bezel_review")

    def open_previews(self):
        idx = os.path.join(self.review_dir(), "index.html")
        if os.path.exists(idx):
            os.startfile(idx)
        else:
            messagebox.showinfo(TITLE, "No previews yet - press Render first.")

    def render_previews(self):
        sel = self.selected()
        keys = [LOOK_KEYS[k] for k in sel if k in LOOK_KEYS]
        self.rbtn.state(["disabled"]); self.cancel_btn.state(["!disabled"]); self.cancelled = False

        def work():
            self.log("Rendering previews (one game per system, from your own folders)...")
            if keys:
                self.call(["bezel_review.py"] + keys)
            self.after(0, self.fill_looks)
            if self.cancelled:
                self.log("Cancelled. Previews already rendered are kept.")
                self.after(0, lambda: self.rbtn.state(["!disabled"])); return
            if "arcade" in sel:
                self.log("Rendering arcade cabinets (well-known games you have, in each cabinet set you've installed)...")
                self.call(["arcade_review.py"])
            self.after(0, lambda: (self.rbtn.state(["!disabled"]), self.cancel_btn.state(["disabled"])))
            self.log("Done. Press Choose next to a system to pick its look.")
        threading.Thread(target=work, daemon=True).start()

    # 6 -------------------------------------------------------------------------------------------------------
    def p_build(self):
        self.header("Build", "Close LaunchBox, then press Start. This can take a while on big collections; the log shows each step.")
        bar = ttk.Frame(self.body); bar.pack(fill="x")
        self.start = ttk.Button(bar, text="Start", command=self.run); self.start.pack(side="left")
        self.cancel_btn = ttk.Button(bar, text="Cancel", command=self.cancel); self.cancel_btn.pack(side="left", padx=(10, 0))
        self.cancel_btn.state(["disabled"])
        self.prog = ttk.Progressbar(bar, mode="determinate", length=600); self.prog.pack(side="left", padx=16)
        self.logbox = tk.Text(self.body, bg=PANEL, fg=FG, insertbackground=FG, font=("Consolas", 10), wrap="word", relief="flat")
        self.logbox.pack(fill="both", expand=True, pady=(14, 0))
        self.q = queue.Queue(); self.after(150, self.pump)

    def log(self, line):
        self.q.put(line)

    def pump(self):
        try:
            while True:
                item = self.q.get_nowait()
                if isinstance(item, tuple):
                    self.prog.configure(value=item[1])
                else:
                    self.logbox.insert("end", item + "\n"); self.logbox.see("end")
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(150, self.pump)

    def run(self):
        running = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
        if "launchbox.exe" in running or "bigbox.exe" in running:
            messagebox.showwarning(TITLE, "Please close LaunchBox / Big Box first."); return
        looks_keys = [k for k, v in getattr(self, "sysvars", {}).items() if v.get() and k in LOOK_KEYS]
        duimon = os.path.isdir(os.path.join(shaders(self.s), "Mega_Bezel_Packs", "Duimon-Mega-Bezel"))
        if looks_keys and not duimon and not messagebox.askyesno(TITLE,
                "The Duimon Mega Bezel packs aren't installed, so your systems won't get their TV looks.\n\n"
                "Go back to 'What you need' and press Download next to them, or press Yes to build without the looks."):
            return
        self.start.state(["disabled"]); self.cancel_btn.state(["!disabled"]); self.cancelled = False
        keys = [k for k, v in getattr(self, "sysvars", {}).items() if v.get()]
        level = self.level.get() if hasattr(self, "level") else "Standard"
        self.s["_level"] = level
        if hasattr(self, "gpu"):
            self.s["_gpu"] = self.gpu.get()
        json.dump(self.s, open(SETTINGS, "w", encoding="utf-8"), indent=2)
        names = [self.lb.PLATFORMS[k][0] for k in keys]
        steps = [("Build the library", ["lb_build.py"] + keys), ("LaunchBox artwork", ["lb_art.py"] + names), ("The CRT looks", None)]
        if "arcade" in keys:
            steps.append(("Arcade cabinets", "artpath"))
        if level in ("Standard", "Ultimate"):
            steps.append(("Covers by checksum", ["crc_thumbs.py"] + names))
            if "arcade" in keys:
                steps.append(("Arcade art (ArcadeDB)", ["arcadedb_art.py"]))
            if shutil.which("gh"):
                steps.append(("Covers by name (libretro)", ["libretro_thumbs.py"] + names))
            steps += [("3D boxes", ("3d", names)), ("Playlists", ["lb_playlists.py"]), ("Menu icons", ["menu_icons.py"])]
            if self.s.get("favourites"):
                steps.append(("Favourites", ["fav_mark.py"]))
        if level == "Ultimate" and os.path.exists(os.path.join(P(self.s, "work_dir"), "zxdb", "ZXDB_mysql.sql")):
            steps += [(f"ZX Spectrum {k}", ["zxdb_inlays.py", "--kind", k]) for k in ("front", "loading", "running")]
        steps.append(("Check everything", ["lb_validate.py"]))
        threading.Thread(target=self.worker, args=(steps,), daemon=True).start()

    def worker(self, steps):
        failed = []   # (step label, reason) for every step that did not finish cleanly
        for n, (label, cmd) in enumerate(steps, 1):
            if self.cancelled:
                break
            self.log(f"\n== {n}/{len(steps)}  {label}")
            try:
                if cmd is None:
                    keys = self.selected()
                    cores = [d for k in keys for d in CORE_DIRS.get(self.lb.PLATFORMS[k][5] or "", [])]
                    install_looks(self.s, self.log, cores)
                    for k in keys:   # the looks the user chose on the previews page
                        shot = self.s.get("looks", {}).get(LOOK_KEYS.get(k, ""))
                        if shot and not self.cancelled:
                            self.call(["apply_pick.py", LOOK_KEYS[k], str(shot)])
                    if self.s.get("_gpu") == "Light":
                        apply_light(self.s, cores, self.log)
                elif cmd == "artpath":
                    set_artpath(self.s, self.log)
                elif isinstance(cmd, tuple):
                    for name in cmd[1]:
                        if self.cancelled:
                            break
                        self.call(["make_3dbox.py", name])
                else:
                    self.call(cmd)
            except Exception as e:
                self.log(f"   step failed: {e}")
                failed.append((label, str(e)))
                if cmd and isinstance(cmd, list) and cmd[0] == "lb_build.py":
                    # Everything after this works on the library it builds, so carrying on would only stack errors.
                    self.log("   The library build failed, so the remaining steps were skipped. Your previous LaunchBox"
                             " data is backed up in the logs folder (lb_data_backup_<date>).")
                    break
            self.q.put(("p", 100 * n / len(steps)))
        if self.cancelled:
            self.log("\nCancelled. Steps already finished are kept, and the build is safe to run again.")
            self.after(0, lambda: (self.start.state(["!disabled"]), self.cancel_btn.state(["disabled"])))
            return
        self.after(0, lambda: (self.start.state(["!disabled"]), self.cancel_btn.state(["disabled"])))
        if failed:
            self.log(f"\nFinished with {len(failed)} problem(s):")
            for label, why in failed:
                self.log(f"   - {label}: {why}")
            self.log("Fix those and run the build again; finished steps are kept.")
        else:
            self.log("\nAll done. Open LaunchBox.")

    def call(self, cmd):
        p = subprocess.Popen([PY, "-I", os.path.join(HERE, cmd[0])] + cmd[1:], cwd=HERE, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.proc = p
        for line in p.stdout:
            self.log("   " + line.rstrip())
        code = p.wait(); self.proc = None
        if code != 0 and not self.cancelled:
            raise RuntimeError(f"{cmd[0]} stopped with an error (exit code {code})")

    def cancel(self):
        """Stop the running step (and anything it started) and skip the rest."""
        self.cancelled = True
        self.cancel_btn.state(["disabled"])
        self.log("\nCancelling...")
        p = getattr(self, "proc", None)
        if p and p.poll() is None:
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    # 6 -------------------------------------------------------------------------------------------------------
    def p_done(self):
        self.header("Finished", "Open LaunchBox. Each system now has its look, art and playlists.")
        repo = os.path.dirname(HERE)
        for text, target in (("See every look side by side (previews)", os.path.join(self.review_dir(), "index.html")),
                             ("Change a system's look: docs/GUIDE.md", os.path.join(repo, "docs", "GUIDE.md")),
                             ("Credits - the people whose work this uses", os.path.join(repo, "CREDITS.md"))):
            ttk.Button(self.body, text=text, command=lambda t=target: os.startfile(t) if os.path.exists(t) else None).pack(anchor="w", pady=4)


if __name__ == "__main__":
    Wizard().mainloop()
