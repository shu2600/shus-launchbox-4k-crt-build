"""Unpack Mr. RetroLust's Lights Out Revisited parts + update packs from Downloads into Mame/artwork_lightsout,
keeping only games in your ROM folders. Update packs are applied after the main parts, oldest first,
so newer art overwrites older. Usage: py -I lightsout_unpack.py"""
import os, re, zipfile, shutil, glob
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

DL = C.DOWNLOADS
OUT = _os.path.join(C.MAME_DIR, r"artwork_lightsout")
ROOTS = [_os.path.join(C.ROOT, r"Arcade\MAME 0.261 ROMs (non-merged)"), _os.path.join(C.ROOT, r"mame-0.261 roms"),
         _os.path.join(C.ROOT, r"NeoGeo"), _os.path.join(C.ROOT, r"Roms\Arcade"), _os.path.join(C.MAME_DIR, r"roms")]
have = {os.path.splitext(f)[0].lower() for r in ROOTS if os.path.isdir(r) for f in os.listdir(r)}
main = sorted(glob.glob(os.path.join(DL, "*_LightsOutRevisited*.zip")))
upd = sorted(glob.glob(os.path.join(DL, "UPDATE TO LIGHTS OUT*.zip")),
             key=lambda p: float(re.search(r"OUT ([\d.]+)", p).group(1)) if re.search(r"OUT ([\d.]+)", p) else 5.95)
os.makedirs(OUT, exist_ok=True)
kept = skipped = 0
def take(z, info, name):
    global kept
    with z.open(info) as s, open(os.path.join(OUT, name), "wb") as d:
        shutil.copyfileobj(s, d)
    kept += 1
for path in main + upd:
    z = zipfile.ZipFile(path)
    dirs = {}
    for info in z.infolist():
        if info.is_dir():
            continue
        parts = info.filename.replace("\\", "/").split("/")
        if parts[-1].lower().endswith(".zip"):
            g = parts[-1][:-4].lower()
            if g in have: take(z, info, parts[-1])
            else: skipped += 1
        elif len(parts) >= 2:   # loose artwork folder: <game>/<files>
            dirs.setdefault(parts[-2].lower(), []).append(info)
    for g, infos in dirs.items():   # repack loose folders as <game>.zip
        if g in have:
            with zipfile.ZipFile(os.path.join(OUT, g + ".zip"), "w", zipfile.ZIP_STORED) as w:
                for i in infos: w.writestr(os.path.basename(i.filename), z.read(i))
            kept += 1
    print(os.path.basename(path), "done", flush=True)
print(f"written {kept}, skipped (not in your set) {skipped}, now in folder {len(os.listdir(OUT))}")
