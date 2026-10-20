"""Fill missing covers and screenshots by ROM checksum, for cartridge systems whose file names don't match
(GoodTools names, Japanese titles, unlicensed carts). CRC32 of the ROM (read from the zip directory, or computed,
with copier/console headers stripped) -> official No-Intro name from libretro-database -> libretro-thumbnails
Named_Boxarts / Named_Snaps. Saves as LaunchBox names it: Images/<platform>/<type>/<title>-01.png. Never overwrites.
Usage: py -I crc_thumbs.py [LaunchBox platform ...]   (default: every system in SYSTEMS)"""
import os, re, sys, zlib, zipfile, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

LB = C.LB
UA = {"User-Agent": "lb-build/1.0 (LaunchBox setup)"}
SYSTEMS = {  # LaunchBox platform -> libretro system name (database + thumbnails)
    "Sega Genesis": "Sega - Mega Drive - Genesis", "Sega 32X": "Sega - 32X", "Atari 2600": "Atari - 2600",
    "Atari 5200": "Atari - 5200", "Atari 7800": "Atari - 7800", "Atari Lynx": "Atari - Lynx",
    "ColecoVision": "Coleco - ColecoVision", "GCE Vectrex": "GCE - Vectrex", "Mattel Intellivision": "Mattel - Intellivision",
    "NEC TurboGrafx-16": "NEC - PC Engine - TurboGrafx 16", "Nintendo 64": "Nintendo - Nintendo 64",
    "Super Nintendo Entertainment System": "Nintendo - Super Nintendo Entertainment System",
    "SNK Neo Geo Pocket Color": "SNK - Neo Geo Pocket Color",
    "Nintendo Entertainment System": "Nintendo - Nintendo Entertainment System", "Nintendo Game Boy": "Nintendo - Game Boy",
    "Nintendo Game Boy Color": "Nintendo - Game Boy Color", "Nintendo Game Boy Advance": "Nintendo - Game Boy Advance",
    "Sega Master System": "Sega - Master System - Mark III", "Sega Game Gear": "Sega - Game Gear",
}
TOSEC = {  # systems whose libretro thumbnails are named after the TOSEC file name (database: metadat/tosec)
    "Atari ST": "Atari - ST",
}
HEADERS = {".a78": 128, ".lnx": 64, ".nes": 16, ".smc": 512, ".sfc": 512, ".fig": 512}
ROM_EXT = (".bin", ".a26", ".a52", ".a78", ".lnx", ".col", ".rom", ".vec", ".int", ".pce", ".z64", ".n64", ".v64",
           ".sfc", ".smc", ".fig", ".ngc", ".ngp", ".md", ".gen", ".smd", ".32x", ".nes", ".gb", ".gbc", ".gba", ".sms", ".gg",
           ".st", ".stx", ".msa")


def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 3 * i)
        except Exception:
            time.sleep(2 + 3 * i)
    return None


def dat(system, tosec=False):
    """crc (8 hex, lower) -> the name libretro-thumbnails uses: the No-Intro game name, or for TOSEC systems the
    TOSEC file name without its extension."""
    raw = get("https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/"
              + ("tosec/" if tosec else "no-intro/") + urllib.parse.quote(system + ".dat"))
    out = {}
    if not raw:
        return out
    text = raw.decode("utf-8", "replace")
    if tosec:
        for name, c in re.findall(r'rom \( name "((?:[^"\\]|\\.)*)" size \d+ crc ([0-9A-Fa-f]{8})', text):
            out.setdefault(c.lower(), os.path.splitext(name)[0])
        return out
    for m in re.finditer(r'game \(\s*name "((?:[^"\\]|\\.)*)"(.*?)\n\)', text, re.S):
        for c in re.findall(r"crc ([0-9A-Fa-f]{8})", m.group(2)):
            out.setdefault(c.lower(), m.group(1))
    return out


def smd_to_bin(data):
    """Super Magic Drive copier format: 512-byte header, then 16 KB blocks with odd bytes first, even bytes second."""
    data = data[512:]
    out = bytearray(len(data))
    for b in range(0, len(data) - 16383, 16384):
        blk = data[b:b + 16384]
        out[b + 1:b + 16384:2] = blk[:8192]
        out[b:b + 16384:2] = blk[8192:]
    return bytes(out)


def swap(data, ext):
    if ext == ".smd" and len(data) % 16384 == 512:
        return smd_to_bin(data)
    if ext == ".v64":     # byte-swapped N64 -> big-endian .z64, which No-Intro lists
        return bytes(b for i in range(0, len(data) - 1, 2) for b in (data[i + 1], data[i]))
    if ext == ".n64":     # little-endian N64
        return b"".join(data[i:i + 4][::-1] for i in range(0, len(data), 4))
    return data


def crcs(path):
    """Possible CRC32s for the ROM: as stored, and with the console/copier header removed."""
    out = []
    try:
        if path.lower().endswith(".zip"):
            z = zipfile.ZipFile(path)
            infos = [i for i in z.infolist() if os.path.splitext(i.filename)[1].lower() in ROM_EXT] or z.infolist()[:1]
            if not infos:
                return out
            i = infos[0]
            out.append(f"{i.CRC:08x}")
            ext = os.path.splitext(i.filename)[1].lower()
            if ext in HEADERS or ext in (".v64", ".n64", ".smd") or i.file_size % 1024 == 512:
                data = z.read(i)
            else:
                return out
        else:
            ext = os.path.splitext(path)[1].lower()
            data = open(path, "rb").read()
            out.append(f"{zlib.crc32(data) & 0xffffffff:08x}")
        data = swap(data, ext)
        out.append(f"{zlib.crc32(data) & 0xffffffff:08x}")
        h = HEADERS.get(ext) or (512 if len(data) % 1024 == 512 else 0)
        if h:
            out.append(f"{zlib.crc32(data[h:]) & 0xffffffff:08x}")
    except Exception:
        pass
    return out


def safe(t):
    return re.sub(r"[:/\\?*\"<>|']", "_", t)


def thumb_name(n):   # libretro-thumbnails replaces &*/:`<>?\| with _
    return re.sub(r'[&*/:`<>?\\|"]', "_", n) + ".png"


def have(folder):
    names = set()
    for dp, _d, fs in os.walk(folder):
        for f in fs:
            m = re.match(r"^(.*)-0\d+\.[^.]+$", f)
            if m:
                names.add(m.group(1).lower())
    return names


for plat in (sys.argv[1:] or list(SYSTEMS) + list(TOSEC)):
    xml = os.path.join(LB, "Data", "Platforms", plat + ".xml")
    if plat not in SYSTEMS and plat not in TOSEC or not os.path.exists(xml):
        continue
    system = SYSTEMS.get(plat) or TOSEC[plat]
    table = dat(system, tosec=plat in TOSEC)
    kinds = {"Box - Front": "Named_Boxarts", "Screenshot - Gameplay": "Named_Snaps"}
    folders = {k: os.path.join(LB, "Images", plat, k) for k in kinds}
    present = {k: have(f) for k, f in folders.items()}
    got = {k: 0 for k in kinds}; matched = 0
    for g in ET.parse(xml).getroot().findall("Game"):
        t = g.findtext("Title") or ""
        need = [k for k in kinds if safe(t).lower() not in present[k]]
        if not need:
            continue
        name = next((table[c] for c in crcs(g.findtext("ApplicationPath") or "") if c in table), None)
        if not name:
            continue
        matched += 1
        for k in need:
            base = f"{system}/{kinds[k]}/{thumb_name(name)}"
            data = get("https://thumbnails.libretro.com/" + urllib.parse.quote(base)) or get(
                f"https://raw.githubusercontent.com/libretro-thumbnails/{system.replace(' ', '_')}/master/{kinds[k]}/"
                + urllib.parse.quote(thumb_name(name)))
            if data and data[:4] == b"\x89PNG":
                os.makedirs(folders[k], exist_ok=True)
                p = os.path.join(folders[k], safe(t) + "-01.png")
                if not os.path.exists(p):
                    open(p, "wb").write(data); got[k] += 1; present[k].add(safe(t).lower())
        time.sleep(0.1)
    print(f"{plat}: {len(table)} checksums in database, {matched} games matched by checksum, {got}", flush=True)
