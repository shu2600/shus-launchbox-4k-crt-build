"""Arcade cabinet review: render your arcade favourites in each MAME artwork set (realistic cabinets,
Lights Out, Bezel Project) as 4K snapshots, headless (-video none, so nothing opens on screen),
and build bezel_review/arcade.html with the same full-screen viewer as the console pages.
Usage: py -I arcade_review.py [game ...]"""
import os, sys, json, html, subprocess
from PIL import Image

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

MAME = C.MAME_DIR
OUT = C.REVIEW
DIR = os.path.join(OUT, "arcade")
SETS = [("R", "artwork_realistic", "Realistic cabinet (OrionsAngel / estefan3112)"),
        ("L", "artwork_lightsout", "Lights Out Revisited"),
        ("B", "artwork_bezelproject", "Bezel Project (converted)")]
GAMES = [("pacman", "Pac-Man"), ("mspacman", "Ms. Pac-Man"), ("galaga", "Galaga"), ("invaders", "Space Invaders"),
         ("mrdo", "Mr. Do!"), ("docastle", "Mr. Do's Castle"), ("dkong", "Donkey Kong"), ("1942", "1942"),
         ("asteroid", "Asteroids"), ("arkanoid", "Arkanoid"), ("altbeast", "Altered Beast"), ("bublbobl", "Bubble Bobble"),
         ("apb", "APB"), ("outrun", "Out Run"), ("robocop", "RoboCop"), ("mainevt", "The Main Event"),
         ("ssprint", "Super Sprint"), ("offroad", "Ironman Ivan Stewart's Super Off-Road"), ("mk2", "Mortal Kombat II"),
         ("mslug", "Metal Slug")]
SECONDS = {"mk2": 120, "mslug": 45, "outrun": 40, "apb": 40}


def has_art(folder, game):
    p = os.path.join(MAME, folder, game)
    return os.path.isdir(p) or os.path.exists(p + ".zip")


def render(game, code, folder):
    snap = os.path.join(DIR, "_snap")
    os.makedirs(snap, exist_ok=True)
    png = os.path.join(snap, f"{game}_{code}.png")
    if os.path.exists(png):
        os.remove(png)
    subprocess.run([os.path.join(MAME, "mame.exe"), game, "-artpath", folder, "-video", "none", "-sound", "none",
                    "-nothrottle", "-seconds_to_run", str(SECONDS.get(game, 30)), "-snapsize", "3840x2160",
                    "-snapview", "auto", "-snapshot_directory", snap, "-snapname", f"{game}_{code}", "-skip_gameinfo"],
                   cwd=MAME, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    if not os.path.exists(png):
        return False
    im = Image.open(png).convert("RGB")
    im.save(os.path.join(DIR, f"{game}_{code}_full.jpg"), quality=90)
    im.resize((1280, 720), Image.LANCZOS).save(os.path.join(DIR, f"{game}_{code}.jpg"), quality=85)
    os.remove(png)
    return True


def write_page(log):
    data, rows = [], []
    for game, title in GAMES:
        shots = [s for s in log.get(game, []) if s["ok"]]
        if not shots:
            continue
        figs = []
        for s in shots:
            i = len(data)
            data.append({"label": f"{title}: {s['set']}", "full": f"arcade/{game}_{s['code']}_full.jpg"})
            figs.append(f'<figure onclick="openV({i})"><figcaption>{html.escape(s["set"])}</figcaption>'
                        f'<img src="arcade/{game}_{s["code"]}.jpg" loading="lazy"></figure>')
        rows.append(f'<h2>{html.escape(title)} <span>({game})</span></h2><div class="grid">{"".join(figs)}</div>')
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arcade Cabinets</title><style>
:root{{--bg:#111;--fg:#eee;--mut:#a0a0a0;--card:#1c1c1c;--acc:#ffc861}}
body{{background:var(--bg);color:var(--fg);font:16px system-ui,sans-serif;margin:0;padding:16px}}
h1{{font-size:24px;margin:0 0 4px}} h2{{font-size:20px;margin:24px 0 8px}} h2 span{{color:var(--mut);font-size:15px;font-weight:400}}
p{{color:var(--mut);margin:0 0 16px}} a{{color:#8cf}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:16px}}
figure{{margin:0;background:var(--card);padding:8px;border-radius:6px;cursor:zoom-in}} figcaption{{margin-bottom:6px;font-size:15px}}
img{{width:100%;display:block;border-radius:4px}}
#v{{position:fixed;inset:0;background:#000;display:none;z-index:9}} #v img{{width:100vw;height:100vh;object-fit:contain;border-radius:0}}
#cap{{position:fixed;left:0;right:0;bottom:0;padding:10px 16px;background:rgba(0,0,0,.65);font-size:18px;transition:opacity .3s}}
@media (max-width:560px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><p><a href="index.html">All systems</a></p>
<h1>Arcade cabinets</h1><p>Each favourite in every artwork set we have for it. MAME uses the first set that has the game, in this order: realistic, Lights Out, Bezel Project. To change the order, edit artpath in mame.ini. Click for full screen; arrows step, H hides the caption, Esc goes back.</p>
{''.join(rows)}
<div id="v" onclick="step(1)"><img id="vi"><div id="cap"></div></div>
<script>
const D={json.dumps(data)};let i=0;
function show(){{document.getElementById('vi').src=D[i].full;document.getElementById('cap').textContent=D[i].label+'  ('+(i+1)+'/'+D.length+')';}}
function openV(n){{i=n;show();const v=document.getElementById('v');v.style.display='block';if(v.requestFullscreen)v.requestFullscreen().catch(()=>{{}});}}
function closeV(){{document.getElementById('v').style.display='none';if(document.fullscreenElement)document.exitFullscreen();}}
function step(k){{i=(i+k+D.length)%D.length;show();}}
document.addEventListener('keydown',e=>{{if(document.getElementById('v').style.display!=='block')return;
 if(e.key==='ArrowRight'||e.key===' ')step(1);else if(e.key==='ArrowLeft')step(-1);else if(e.key==='Escape')closeV();
 else if(e.key==='h'||e.key==='H'){{const c=document.getElementById('cap');c.style.opacity=c.style.opacity==='0'?'1':'0';}}}});
document.addEventListener('fullscreenchange',()=>{{if(!document.fullscreenElement)document.getElementById('v').style.display='none';}});
</script></body></html>"""
    open(os.path.join(OUT, "arcade.html"), "w", encoding="utf-8").write(page)


if __name__ == "__main__":
    os.makedirs(DIR, exist_ok=True)
    logp = os.path.join(DIR, "log.json")
    log = json.load(open(logp)) if os.path.exists(logp) else {}
    only = sys.argv[1:]
    for game, title in GAMES:
        if only and game not in only:
            continue
        log[game] = []
        for code, folder, name in SETS:
            if not has_art(folder, game):
                continue
            ok = render(game, code, folder)
            log[game].append({"code": code, "set": name, "ok": ok})
            print(f"{game} {code} {'ok' if ok else 'FAILED'}", flush=True)
        json.dump(log, open(logp, "w"), indent=1)
        write_page(log)
