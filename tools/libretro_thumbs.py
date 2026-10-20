"""Fill missing LaunchBox Box - Front images from libretro-thumbnails (github.com/libretro-thumbnails, free).
Lists each system's Named_Boxarts via the GitHub API, matches games that have no front cover by ROM file name
(No-Intro style) then by title, and downloads only those from thumbnails.libretro.com.
Usage: py -I libretro_thumbs.py [lb platform ...]   (default: all in REPOS)"""
import os, re, sys, json, time, subprocess, urllib.request, urllib.parse, xml.etree.ElementTree as ET
args = sys.argv[1:]; sys.argv = [sys.argv[0]]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lb_build import compare, clean_name, LB

REPOS = {"Sega Genesis": "Sega - Mega Drive - Genesis", "Atari 2600": "Atari - 2600", "ColecoVision": "Coleco - ColecoVision",
         "Super Nintendo Entertainment System": "Nintendo - Super Nintendo Entertainment System", "Nintendo 64": "Nintendo - Nintendo 64",
         "Atari 7800": "Atari - 7800", "Sega Dreamcast": "Sega - Dreamcast", "Commodore Amiga": "Commodore - Amiga",
         "Atari ST": "Atari - ST", "Sinclair ZX Spectrum": "Sinclair - ZX Spectrum", "NEC TurboGrafx-16": "NEC - PC Engine - TurboGrafx 16",
         "Mattel Intellivision": "Mattel - Intellivision", "GCE Vectrex": "GCE - Vectrex", "Atari Lynx": "Atari - Lynx",
         "Atari 5200": "Atari - 5200", "Nintendo GameCube": "Nintendo - GameCube", "SNK Neo Geo AES": "SNK - Neo Geo"}


def safe(t):
    return re.sub(r"[:/\\?*\"<>|']", "_", t)


def names(system):
    repo = system.replace(" ", "_")
    sha = subprocess.run(["gh", "api", f"repos/libretro-thumbnails/{repo}/git/trees/master", "--jq",
                          '.tree[] | select(.path=="Named_Boxarts") | .sha'], capture_output=True, text=True).stdout.strip()
    if not sha:
        return []
    out = subprocess.run(["gh", "api", f"repos/libretro-thumbnails/{repo}/git/trees/{sha}", "--jq", ".tree[].path"],
                         capture_output=True, text=True, encoding="utf-8").stdout
    return [x for x in out.splitlines() if x.lower().endswith(".png")]


def norm_file(n):   # libretro replaces &*/:`<>?\| with _ in file names
    return re.sub(r'[&*/:`<>?\\|"]', "_", n).lower()


for plat in (args or list(REPOS)):
    if plat not in REPOS:
        print(f"{plat}: no libretro cover list for this system, skipped")
        continue
    system = REPOS[plat]
    files = names(system)
    by_file = {os.path.splitext(f)[0].lower(): f for f in files}
    by_title = {}
    for f in files:
        k = compare(clean_name(f))
        by_title.setdefault(k, f) if "(USA" in f or "(Europe" in f or "(World" in f else None
    for f in files:
        by_title.setdefault(compare(clean_name(f)), f)
    img = os.path.join(LB, "Images", plat, "Box - Front"); os.makedirs(img, exist_ok=True)
    # compare the saved file names the way they were written (safe()), so titles with ' are not fetched again every run
    have = {re.sub(r"-\d\d$", "", os.path.splitext(x)[0]).lower() for dp, _, fs in os.walk(img) for x in fs}
    games = ET.parse(os.path.join(LB, "Data", "Platforms", plat + ".xml")).getroot().findall("Game")
    got = tried = 0
    for g in games:
        t = g.findtext("Title", "")
        if safe(t).lower() in have:
            continue
        rom = os.path.splitext(os.path.basename(g.findtext("ApplicationPath", "")))[0]
        hit = by_file.get(norm_file(rom)) or by_title.get(compare(t)) or by_title.get(compare(clean_name(rom)))
        if not hit:
            continue
        tried += 1
        urls = ["https://thumbnails.libretro.com/" + urllib.parse.quote(f"{system}/Named_Boxarts/{hit}"),
                f"https://raw.githubusercontent.com/libretro-thumbnails/{system.replace(' ', '_')}/master/Named_Boxarts/" + urllib.parse.quote(hit)]
        try:
            data = None
            for url in urls:   # the thumbnail server misses some names that the GitHub repo has
                try:
                    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "LaunchBoxBuild/1.0"}), timeout=30).read()
                    break
                except Exception:
                    continue
            if data is None:
                raise IOError("not on either server")
            open(os.path.join(img, safe(t) + "-01.png"), "wb").write(data)
            have.add(safe(t).lower()); got += 1
        except Exception as e:
            print(f"  {t}: {e}", flush=True)
        time.sleep(0.2)
    print(f"{plat}: {len(files)} boxarts listed, {tried} matched, {got} downloaded", flush=True)
