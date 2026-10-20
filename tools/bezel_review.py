"""Bezel review: for each RetroArch system, boot one well-known game to past loading (unthrottled), freeze it in a
save state, then render every candidate bezel/monitor/TV look from that same frame with RetroArch's own GPU
screenshot (no desktop capture). Writes <review_dir>\\<system>.html to pick from.

Usage: py -I bezel_review.py [system-key ...]   (no keys = all, alphabetical)
"""
import os, sys, glob, json, shutil, subprocess, time, html, xml.etree.ElementTree as ET
from PIL import Image

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

LB = C.LB
RA = C.RA_DIR
SH = os.path.join(RA, "shaders")
DUI = os.path.join(SH, r"Mega_Bezel_Packs\Duimon-Mega-Bezel\Presets\Advanced")
NAMEC = os.path.join(SH, r"Mega_Bezel_Packs\thenamec-commodore-pack\presets")
GENERIC = os.path.join(SH, r"shaders_slang\bezel\Mega_Bezel\Presets\MBZ__1__ADV.slangp")
WRAP = os.path.join(SH, "_review")          # wrapper presets live here (relative #reference works from here)
OUT = C.REVIEW
TMP = _os.path.join(C.REVIEW, r"_tmp")

NOSTATE = {"vectrex", "ds"}   # vecx crashes loading its own state: render straight from boot
HANDHELD = {"lynx", "ngpc", "ds", "3ds", "psp"}
# key: (LaunchBox platform, core dll, game title prefix, warm-up frames, Duimon folders, current core folder name)
SYSTEMS = {
    "2600":   ("Atari 2600", "stella", "River Raid", 1800, ["Atari_2600"], "Stella"),
    "5200":   ("Atari 5200", "a5200", "Pac-Man", 1800, ["Atari_5200"], "a5200"),
    "7800":   ("Atari 7800", "prosystem", "Asteroids", 1800, ["Atari_7800"], "ProSystem"),
    "jaguar": ("Atari Jaguar", "virtualjaguar", "Tempest 2000", 2400, ["Atari_Jaguar"], "Virtual Jaguar"),
    "lynx":   ("Atari Lynx", "handy", "RoadBlasters", 1800, ["Atari_Lynx"], "Handy"),
    "st":     ("Atari ST", "hatari", "Speedball 2", 4000, ["Atari_ST"], "hatari"),
    "coleco": ("ColecoVision", "gearcoleco", "Galaxian", 1800, ["ColecoVision"], "Gearcoleco"),
    "amiga":  ("Commodore Amiga", "puae", "Lemmings", 5000, ["Amiga_A500_Plus"], "PUAE"),
    "vectrex": ("GCE Vectrex", "vecx", "Scramble", 1500, ["GCE_Vectrex"], "VecX"),
    "intv":   ("Mattel Intellivision", "freeintv", "BurgerTime", 1800, ["Mattel_Intellivision"], "FreeIntv"),
    "pce":    ("NEC TurboGrafx-16", "mednafen_pce", "Bonk's Adventure", 2400, ["NEC_TurboGrafx_16", "NEC_PC_Engine"], "Beetle PCE"),
    "3ds":    ("Nintendo 3DS", "citra", "Super Mario 3D Land", 3600, ["Nintendo_3DS", "Nintendo_3DS_DREZ"], "Citra"),
    "n64":    ("Nintendo 64", "mupen64plus_next", "Mario Kart 64", 2400, ["Nintendo_N64", "Nintendo_N64_DREZ"], "Mupen64Plus-Next"),
    "ds":     ("Nintendo DS", "melonds", "New Super Mario Bros", 2400, ["Nintendo_NDS", "Nintendo_NDS_DREZ"], "melonDS"),
    "dc":     ("Sega Dreamcast", "flycast", "Crazy Taxi", 3000, ["SEGA_Dreamcast"], "Flycast"),
    "md":     ("Sega Genesis", "genesis_plus_gx", "Sonic the Hedgehog 2", 1500, ["SEGA_Genesis"], "Genesis Plus GX"),
    "zx":     ("Sinclair ZX Spectrum", "fuse", "Bomb Jack", 16000, ["Sinclair_ZX_Spectrum"], "Fuse"),
    "neogeo": ("SNK Neo Geo AES", "fbneo", "Metal Slug", 2400, ["Neo_Geo_AES"], "FinalBurn Neo"),
    "ngpc":   ("SNK Neo Geo Pocket Color", "mednafen_ngp", "Pac-Man", 1500, ["Neo_Geo_Pocket_Color"], "Beetle NeoPop"),
    "psp":    ("Sony PSP", "ppsspp", "Dante", 2400, ["SONY_PSP", "SONY_PSP_DREZ"], "PPSSPP"),
    "snes":   ("Super Nintendo Entertainment System", "snes9x", "Super Mario World", 1500, ["Nintendo_SNES", "Nintendo_Super_Famicom"], "Snes9x"),
}


def game_path(plat, prefix):
    root = ET.parse(os.path.join(LB, "Data", "Platforms", plat + ".xml")).getroot()
    for g in root.findall("Game"):
        if (g.findtext("Title") or "").lower().startswith(prefix.lower()):
            return g.findtext("Title"), g.findtext("ApplicationPath")
    g = root.find("Game")
    return g.findtext("Title"), g.findtext("ApplicationPath")


def candidates(key):
    """(label, preset path, extra param lines) in display order."""
    _, _, _, _, folders, core = SYSTEMS[key]
    c = []
    cur = os.path.join(RA, "config", core, core + ".slangp")
    if os.path.exists(cur):
        c.append(("CURRENT (what it uses now)", cur, []))
    c.append(("Plain CRT frame (the original generic)", GENERIC, []))
    if key not in HANDHELD:
        for tv in ["TV1", "TV2", "TV3", "TV4", "TV5", "TV6", "TV6_Alt"]:
            c.append((f"Duimon {tv}", os.path.join(DUI, "TV", f"{tv}-[ADV]-[Guest].slangp"), []))
    NOBG = ['HSM_BG_OPACITY = "0.000000"']
    for fo in folders:
        for p in sorted(glob.glob(os.path.join(DUI, fo, "*.slangp"))):
            n = os.path.basename(p)
            # picks: no Sony PVM, no console/keyboard backdrops; monitors and bezels only with the backdrop removed
            if "[Night]" in n or "Custom-Bezel" in n or "PVM20" in n:
                continue
            if "[Monitor]" in n or "[Bezel]" in n:
                c.append((f"{fo.replace('_', ' ')}: {n[:-7].split('[Guest]-')[-1].strip('[]')}, backdrop removed", p, NOBG))
            else:
                c.append((f"{fo.replace('_', ' ')}: {n[:-7]}", p, []))
    if key == "amiga":
        base = os.path.join(NAMEC, "Commodore_Amiga500Plus")
        for mon, nice in [("Commodore_C1084S-D1", "Commodore 1084S monitor"), ("Commodore_C1084", "Commodore 1084 monitor"),
                          ("Philips_21PT3326V7", "Philips TV")]:
            for flav, f in [("MBZ_SHARP_ADV", "FULLDEVICE_CURVED_DAY"), ("MBZ_SHARP_SMOOTH", "FULLDEVICE_CURVED_DAY")]:
                p = os.path.join(base, mon, flav, f + ".slangp")
                if os.path.exists(p):
                    c.append((f"{nice}, backdrop removed ({'sharp' if flav.endswith('ADV') else 'smoothed'})", p, NOBG))
        for f in glob.glob(os.path.join(base, "Commodore_C1084S-D1", "NMC_SHARP_SMOOTH-SCALEFX", "FULLDEVICE_CURVED_DAY.slangp")):
            c.append(("Commodore 1084S, ScaleFX smoothing (looks higher-res), backdrop removed", f, NOBG))
    base = os.path.join(SH, r"shaders_slang\bezel\Mega_Bezel\Presets\Base_CRT_Presets")
    for lab, f in [("STYLE: composite TV (blends dither like a real telly)", "MBZ__1__ADV__GDV-NTSC.slangp"),
                   ("STYLE: smooth (looks higher-res)", "MBZ__0__SMOOTH-ADV__GDV.slangp"),
                   ("STYLE: super-xBR edge smoothing", "MBZ__1__ADV-SUPER-XBR__GDV.slangp"),
                   ("STYLE: easymode crisp CRT", "MBZ__1__ADV__EASYMODE.slangp"),
                   ("STYLE: Sony Megatron (full effect needs HDR on the TV)", "MBZ__1__ADV__MEGATRON.slangp"),
                   ("STYLE: glass frame with reflections", "MBZ__2__ADV-GLASS__GDV.slangp")]:
        c.append((lab, os.path.join(base, f), []))
    seen, out = set(), []
    for lab, p, extra in c:
        k = (os.path.normcase(p), tuple(extra))
        if os.path.exists(p) and k not in seen:
            seen.add(k)
            out.append((lab, p, extra))
    return out


CRT_NAMES = {"GDV": "Guest Advanced CRT", "GDV-NTSC": "Guest Advanced CRT + NTSC composite", "GDV-MINI": "Guest Advanced CRT (mini)",
             "GDV-MINI-NTSC": "Guest Advanced CRT (mini) + NTSC composite", "EASYMODE": "Easymode CRT", "MEGATRON": "Sony Megatron CRT",
             "MEGATRON-NTSC": "Sony Megatron CRT + NTSC composite", "LCD-GRID": "LCD grid (handheld screen)"}


def crt_name(path, depth=0):
    """Follow a preset's #reference chain down to the Mega Bezel base preset and name its CRT effect."""
    import re
    if depth > 12 or not os.path.exists(path):
        return "unknown"
    b = os.path.basename(path)
    m = re.match(r"MBZ__(\d)__([A-Z0-9-]+?)__([A-Z-]+)\.slangp$", b)
    if m:
        frame, crt = m.group(2), m.group(3)
        extra = []
        if "SMOOTH" in frame: extra.append("smoothing")
        if "SUPER-XBR" in frame: extra.append("super-xBR")
        if "GLASS" in frame: extra.append("glass")
        if "RESHADE" in frame: extra.append("ReShade FX")
        return CRT_NAMES.get(crt, crt) + (" + " + ", ".join(extra) if extra else "")
    if b == "MBZ__1__ADV.slangp" or b == "MBZ__2__ADV-GLASS.slangp":
        return "Guest Advanced CRT" + (" + glass" if "GLASS" in b else "")
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if line.startswith("#reference") and line.endswith('.slangp"'):
            ref = line.split('"')[1]
            r = crt_name(os.path.normpath(os.path.join(os.path.dirname(path), ref)), depth + 1)
            if r != "unknown":
                return r
    return "unknown"


def wrapper(i, path, extra):
    os.makedirs(WRAP, exist_ok=True)
    rel = os.path.relpath(path, WRAP).replace("\\", "/")
    w = os.path.join(WRAP, f"w{i:03d}.slangp")
    with open(w, "w", encoding="utf-8") as f:
        f.write(f'#reference "{rel}"\nHSM_INTRO_WHEN_TO_SHOW = "0.000000"\n' + "".join(x + "\n" for x in extra))
    return w


def cfg(name, lines):
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write("".join(f'{k} = "{v}"\n' for k, v in lines.items()))
    return p


def run(args, timeout=240):
    t = time.time()
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 4          # SW_SHOWNOACTIVATE: draw the window but never take focus from whatever you're doing
        subprocess.run([os.path.join(RA, "retroarch.exe")] + args, cwd=RA, timeout=timeout, startupinfo=si,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/IM", "retroarch.exe", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return time.time() - t


def thumb(src, dst, w=960):
    im = Image.open(src).convert("RGB")
    im.thumbnail((w, w))
    im.save(dst, quality=88)
    return im.size


def do_system(key):
    plat, core, prefix, frames, _, corename = SYSTEMS[key]
    title, gpath = game_path(plat, prefix)
    d = os.path.join(OUT, key)
    redo = os.environ.get("REDO_ALL") == "1"
    if redo:
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    st = os.path.join(TMP, "states", key)
    shutil.rmtree(st, ignore_errors=True)
    os.makedirs(st)
    common = {"video_vsync": "false", "audio_sync": "false", "vrr_runloop_enable": "false", "run_ahead_enabled": "false",
              "savestate_directory": st, "savefile_directory": os.path.join(TMP, "saves"), "video_font_enable": "false",
              "savestates_in_content_dir": "false", "sort_savestates_enable": "false", "sort_savestates_by_content_enable": "false",
              "video_fullscreen": "false", "video_windowed_fullscreen": "false", "video_window_save_positions": "true",
              "video_window_custom_size_enable": "true", "window_position_x": "3900", "window_position_y": "0",
              "window_position_width": "3840", "window_position_height": "2160", "video_windowed_position_x": "3900", "video_windowed_position_y": "0", "video_windowed_position_width": "3840", "video_windowed_position_height": "2160", "video_window_show_decorations": "false", "auto_shaders_enable": "false", "config_save_on_exit": "false",
              "video_gpu_screenshot": "true", "audio_enable": "false", "pause_nonactive": "false"}
    warm = cfg(f"warm_{key}.cfg", {**common, "video_shader_enable": "false", "savestate_auto_save": "true", "savestate_auto_load": "false"})
    shot = cfg(f"shot_{key}.cfg", {**common, "video_shader_enable": "true", "savestate_auto_save": "false", "savestate_auto_load": "false" if key in NOSTATE else "true"})
    raw = cfg(f"raw_{key}.cfg", {**common, "video_shader_enable": "false", "video_gpu_screenshot": "false",
                                    "savestate_auto_save": "false", "savestate_auto_load": "true"})
    L = ["-L", f"cores\\{core}_libretro.dll"]
    t = run(["--appendconfig", warm] + L + [f"--max-frames={frames}", gpath])
    states = glob.glob(os.path.join(st, "**", "*.state*"), recursive=True)
    log = {"system": plat, "game": title, "path": gpath, "warm_seconds": round(t, 1), "state": bool(states), "shots": []}
    rawpng = os.path.join(d, "raw.png")
    run(["--appendconfig", raw] + L + ["--max-frames=30", "--max-frames-ss", f"--max-frames-ss-path={rawpng}", gpath])
    if os.path.exists(rawpng):
        log["raw_size"] = Image.open(rawpng).size
        thumb(rawpng, os.path.join(d, "raw.jpg"), 640)
    for i, (lab, p, extra) in enumerate(candidates(key), 1):
        w = wrapper(i, p, extra)
        png = os.path.join(d, f"{i:02d}.png")
        if os.path.exists(os.path.join(d, f"{i:02d}.jpg")) and not redo:
            log["shots"].append({"n": i, "label": lab, "preset": os.path.relpath(p, SH), "extra": extra, "ok": True, "secs": 0, "crt": crt_name(p)})
            continue
        t = run(["--appendconfig", shot, "--set-shader", w] + L +
                [f"--max-frames={frames if key in NOSTATE else 40}", "--max-frames-ss", f"--max-frames-ss-path={png}", gpath])
        ok = os.path.exists(png)
        if ok:
            thumb(png, os.path.join(d, f"{i:02d}.jpg"), 1280)
            thumb(png, os.path.join(d, f"{i:02d}_full.jpg"), 3840)
            os.remove(png)
        log["shots"].append({"n": i, "label": lab, "preset": os.path.relpath(p, SH), "extra": extra, "ok": ok, "secs": round(t, 1), "crt": crt_name(p)})
        print(f"  {key} {i:02d} {'ok ' if ok else 'FAIL'} {t:5.1f}s {lab}", flush=True)
    json.dump(log, open(os.path.join(d, "log.json"), "w"), indent=1)
    write_page(key, log)
    return log


TV_NAMES = {"TV1": "TV1: late-80s Toshiba (grey)", "TV2": "TV2: late-80s Toshiba (dark)", "TV3": "TV3: early-90s grey TV",
            "TV4": "TV4: 90s Samsung silver", "TV5": "TV5: 80s RCA wood cabinet (US)", "TV6": "TV6: 70s HMV wood cabinet (UK)",
            "TV6_Alt": "TV6 alt: HMV cabinet, alternative room"}


def nice(label):
    if label.startswith("Duimon TV"):
        return TV_NAMES.get(label.split()[-1], label)
    return label.replace("STYLE: ", "Plain frame, style: ")


PICK_BADGE = "<em>ANIMA’S PICK</em> "
PICKS = {  # the build's pick per system (frame); the CRT style gets tuned on the favourite afterwards
    "dc": "Duimon TV4",
    "2600": "Duimon TV6", "5200": "Duimon TV5", "7800": "Duimon TV5", "coleco": "Duimon TV5", "intv": "Duimon TV5",
    "zx": "Duimon TV6", "amiga": "Commodore 1084S monitor, backdrop removed (sharp)", "st": "Monitor, backdrop removed",
    "md": "Duimon TV2", "pce": "Duimon TV2", "snes": "Duimon TV2", "neogeo": "Duimon TV3", "n64": "Duimon TV4",
    "jaguar": "Duimon TV4", "vectrex": "GCE Vectrex", "lynx": "Lynx-[ADV]-[LCD-GRID]", "ngpc": "NGPC", "ds": "NDS",
    "3ds": "3DS", "psp": "PSP"}


def write_page(key, log):
    shots = [s for s in log["shots"] if s["ok"]]
    pick = PICKS.get(key, "")
    pick_n = next((s["n"] for s in shots if pick and pick in s["label"]), None)
    data = [{"n": s["n"], "label": nice(s["label"]), "crt": s.get("crt", ""),
             "full": f"{key}/{s['n']:02d}_full.jpg", "thumb": f"{key}/{s['n']:02d}.jpg"} for s in shots]
    import json as _json
    cards = "".join(f'''<figure onclick="openV({i})"><figcaption><b>{d["n"]}</b> {PICK_BADGE if d["n"] == pick_n else ''}{html.escape(d["label"])}<br><span>CRT: {html.escape(d["crt"])}</span></figcaption><img src="{d["thumb"]}" loading="lazy"></figure>''' for i, d in enumerate(data))
    raw = f'<figure class="raw"><figcaption><b>Raw game picture</b>, nothing cropped: compare the edges {log.get("raw_size", "")}</figcaption><img src="{key}/raw.jpg"></figure>' if os.path.exists(os.path.join(OUT, key, "raw.jpg")) else ""
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(log['system'])} Bezels</title><style>
:root{{--bg:#111;--fg:#eee;--mut:#a0a0a0;--card:#1c1c1c;--acc:#ffc861}}
body{{background:var(--bg);color:var(--fg);font:16px system-ui,sans-serif;margin:0;padding:16px}}
h1{{font-size:24px;margin:0 0 4px}} p{{color:var(--mut);margin:0 0 16px}} a{{color:#8cf}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:16px}}
figure{{margin:0;background:var(--card);padding:8px;border-radius:6px;cursor:zoom-in}} figcaption{{margin-bottom:6px;font-size:15px}}
figcaption b{{display:inline-block;min-width:28px;color:var(--acc);font-size:18px}} figcaption span{{color:var(--mut);font-size:14px}} em{{font-style:normal;background:var(--acc);color:#111;padding:1px 6px;border-radius:4px;font-size:13px;margin-right:6px}}
img{{width:100%;display:block;border-radius:4px}} .raw{{cursor:default}} .raw img{{width:auto;max-width:100%;image-rendering:pixelated}}
#v{{position:fixed;inset:0;background:#000;display:none;z-index:9}} #v img{{width:100vw;height:100vh;object-fit:contain;border-radius:0}}
#cap{{position:fixed;left:0;right:0;bottom:0;padding:10px 16px;background:rgba(0,0,0,.65);font-size:18px;transition:opacity .3s}}
#cap b{{color:var(--acc);font-size:22px;margin-right:10px}}
@media (max-width:560px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><p><a href="index.html">All systems</a></p>
<h1>{html.escape(log['system'])}</h1><p>Game: {html.escape(log['game'])}. Click a picture to see it full screen, exactly as on the TV. Arrow keys step through, H hides the caption, Esc goes back. To use one: py apply_pick.py &lt;system&gt; &lt;number&gt;.</p>
{raw}<div class="grid">{cards}</div>
<div id="v" onclick="step(1)"><img id="vi"><div id="cap"></div></div>
<script>
const D={_json.dumps(data)};let i=0;
function show(){{const d=D[i];document.getElementById('vi').src=d.full;document.getElementById('cap').innerHTML='<b>'+d.n+'</b>'+d.label+'  |  CRT: '+d.crt+'  ('+(i+1)+'/'+D.length+')';}}
function openV(n){{i=n;show();const v=document.getElementById('v');v.style.display='block';if(v.requestFullscreen)v.requestFullscreen().catch(()=>{{}});}}
function closeV(){{document.getElementById('v').style.display='none';if(document.fullscreenElement)document.exitFullscreen();}}
function step(k){{i=(i+k+D.length)%D.length;show();}}
document.addEventListener('keydown',e=>{{if(document.getElementById('v').style.display!=='block')return;
 if(e.key==='ArrowRight'||e.key===' ')step(1);else if(e.key==='ArrowLeft')step(-1);else if(e.key==='Escape')closeV();
 else if(e.key==='h'||e.key==='H'){{const c=document.getElementById('cap');c.style.opacity=c.style.opacity==='0'?'1':'0';}}}});
document.addEventListener('fullscreenchange',()=>{{if(!document.fullscreenElement)document.getElementById('v').style.display='none';}});
</script></body></html>"""
    open(os.path.join(OUT, f"{key}.html"), "w", encoding="utf-8").write(page)
    index()


def index():
    items = []
    for k, v in SYSTEMS.items():
        f = os.path.join(OUT, f"{k}.html")
        items.append(f'<li><a href="{k}.html">{html.escape(v[0])}</a></li>' if os.path.exists(f) else f'<li class="todo">{html.escape(v[0])} (rendering)</li>')
    if os.path.exists(os.path.join(OUT, "arcade.html")):
        items.append('<li><a href="arcade.html">Arcade cabinets (MAME)</a></li>')
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Bezel Review</title><style>
body{{background:#111;color:#eee;font:18px system-ui,sans-serif;padding:16px}} a{{color:#8cf}} .todo{{color:#777}} li{{margin:8px 0}}
</style></head><body><h1>Bezel review</h1><p>Alphabetical. Reload this page as systems finish.</p><ol>{''.join(items)}</ol></body></html>""")


if __name__ == "__main__":
    os.makedirs(TMP, exist_ok=True)
    keys = sys.argv[1:] or list(SYSTEMS)
    index()
    for k in keys:
        print(f"== {k}", flush=True)
        try:
            do_system(k)
        except Exception as e:
            print(f"  {k} ERROR {e!r}", flush=True)
