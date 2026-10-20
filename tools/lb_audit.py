"""Audit the LaunchBox library: per platform, game count, missing ROM file, no emulator, missing box front,
missing clear logo / screenshot. Usage: py -I lb_audit.py [--list PLATFORM]"""
import os, re, sys, glob
import xml.etree.ElementTree as E

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

LB = C.LB


def clean(t):
    return re.sub(r"[:/\?*\"<>|']", "_", t)


_CACHE = {}


def has_img(plat, kind, title):
    """True when Images/<plat>/<kind> (any region subfolder) holds '<title>-0N.*'. Folder listed once, then cached."""
    k = (plat, kind)
    if k not in _CACHE:
        names = set()
        for dp, _d, fs in os.walk(os.path.join(LB, "Images", plat, kind)):
            for f in fs:
                m = re.match(r"^(.*)-0\d+\.[^.]+$", f)
                if m:
                    names.add(m.group(1).lower())
        _CACHE[k] = names
    return clean(title).lower() in _CACHE[k]


def main():
    only = sys.argv[sys.argv.index("--list") + 1] if "--list" in sys.argv else None
    tot = [0] * 5
    print(f"{'platform':45} games  norom noemu nobox noshot")
    for f in sorted(glob.glob(os.path.join(LB, "Data", "Platforms", "*.xml"))):
        plat = os.path.basename(f)[:-4]
        games = E.parse(f).getroot().findall("Game")
        if not games:
            continue
        c = [len(games), 0, 0, 0, 0]
        for g in games:
            t = g.findtext("Title") or ""
            ap = g.findtext("ApplicationPath") or ""
            full = ap if os.path.isabs(ap) else os.path.normpath(os.path.join(LB, ap))
            miss = []
            if ap and "://" not in ap and not os.path.exists(full):
                c[1] += 1; miss.append("rom")
            if not (g.findtext("Emulator") or "").strip() and "://" not in ap and not ap.lower().endswith((".exe", ".lnk", ".url", ".bat")):
                c[2] += 1; miss.append("emu")
            if not has_img(plat, "Box - Front", t) and not has_img(plat, "Box - 3D", t):
                c[3] += 1; miss.append("box")
            if not has_img(plat, "Screenshot - Gameplay", t):
                c[4] += 1; miss.append("shot")
            if only and plat == only and miss:
                print("   ", t, miss, ap)
        tot = [a + b for a, b in zip(tot, c)]
        print(f"{plat:45} {c[0]:5}  {c[1]:5} {c[2]:5} {c[3]:5} {c[4]:6}")
    print(f"{'TOTAL':45} {tot[0]:5}  {tot[1]:5} {tot[2]:5} {tot[3]:5} {tot[4]:6}")


main()
