"""Apply a pick from a review page: point that system's RetroArch core preset at the chosen look.
Usage: py -I apply_pick.py <system-key> <shot-number>"""
import os, sys, json, shutil
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

argv = list(sys.argv)
sys.argv = [sys.argv[0]]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bezel_review as b

key, n = argv[1], int(argv[2])
log = json.load(open(os.path.join(b.OUT, key, "log.json")))
shot = next(s for s in log["shots"] if s["n"] == n)
core = b.SYSTEMS[key][5]
cfgdir = os.path.join(b.RA, "config", core)
os.makedirs(cfgdir, exist_ok=True)
dst = os.path.join(cfgdir, core + ".slangp")
preset = os.path.normpath(os.path.join(b.SH, shot["preset"]))
if os.path.normcase(preset) == os.path.normcase(dst):   # "CURRENT" picked: nothing to change
    print(f"{key}: #{n} is what it already uses")
    sys.exit(0)
if os.path.exists(dst):
    shutil.copy2(dst, dst + ".bak_picks")
rel = os.path.relpath(preset, cfgdir).replace("\\", "/")
with open(dst, "w", encoding="utf-8") as f:
    f.write(f'#reference "{rel}"\n' + "".join(x + "\n" for x in shot.get("extra", [])))
with open(_os.path.join(C.WORK, r"BEZEL_PICKS.md"), "a", encoding="utf-8") as f:
    f.write(f"{log['system']}: #{n} = {b.nice(shot['label'])} | CRT: {shot.get('crt') or b.crt_name(preset)} (applied)\n")
print(f"{key}: applied #{n} {b.nice(shot['label'])} | CRT: {shot.get('crt') or b.crt_name(preset)}")
