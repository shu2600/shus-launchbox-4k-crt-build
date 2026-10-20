"""Fetch artwork for every game in your LaunchBox library from LaunchBox's own image server
(images.launchbox-app.com, the same place LaunchBox's "Download Media" uses), named the way LaunchBox looks them up:
Images\\<Platform>\\<Media Type>\\<Title with illegal characters as _>-01.<ext>.
Skips any game/type that already has an image (your existing art). LaunchBox must be CLOSED while this runs? No: images only.
Usage: py lb_art.py [platform name ...]   (default: every platform file in Data\\Platforms)
"""
import os, re, sys, sqlite3, threading, queue, urllib.request, time
import xml.etree.ElementTree as ET

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

LB = C.LB
DB = os.path.join(LB, r"Metadata\LaunchBox.Metadata.db")
LOG = _os.path.join(C.LOGS, r"lb_art.log")
URL = "https://images.launchbox-app.com/"
TYPES = {  # media type: how many to keep
    "Box - Front": 1, "Box - Back": 1, "Box - 3D": 1, "Clear Logo": 1, "Screenshot - Gameplay": 2,
    "Screenshot - Game Title": 1, "Fanart - Background": 1, "Cart - Front": 1, "Disc": 1, "Banner": 1,
    "Arcade - Marquee": 1, "Arcade - Cabinet": 1, "Arcade - Controls Information": 1,
}
REGIONS = ["North America", "World", "United Kingdom", "Europe", "", None]


def safe(title):
    return re.sub(r"[\\/:*?\"<>|']", "_", title)


def region_rank(r):
    return REGIONS.index(r) if r in REGIONS else len(REGIONS)


def jobs_for(platform, c):
    root = ET.parse(os.path.join(LB, "Data", "Platforms", f"{platform}.xml")).getroot()
    out = []
    for g in root.findall("Game"):
        dbid, title = g.findtext("DatabaseID"), g.findtext("Title")
        if not dbid or not title:
            continue
        imgs = c.execute("select FileName,Type,Region from GameImages where DatabaseId=?", (int(dbid),)).fetchall()
        for mtype, keep in TYPES.items():
            cands = sorted([i for i in imgs if i[1] == mtype], key=lambda i: region_rank(i[2]))[:keep]
            if not cands:
                continue
            folder = os.path.join(LB, "Images", platform, mtype)
            stem = safe(title)
            if os.path.isdir(folder) and any(f.startswith(stem + "-") for f in os.listdir(folder)):
                continue
            for k, (fn, _t, _r) in enumerate(cands, 1):
                out.append((URL + fn, os.path.join(folder, f"{stem}-{k:02d}{os.path.splitext(fn)[1]}")))
    return out


def worker(q, stats, lock):
    while True:
        item = q.get()
        if item is None:
            return
        url, dest = item
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "LaunchBox-art-sync (personal library)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if data[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1", b"\xff\xd8\xff\xdb") or data[:3] == b"\xff\xd8\xff":
                with open(dest + ".part", "wb") as f:
                    f.write(data)
                os.replace(dest + ".part", dest)
                with lock:
                    stats["ok"] += 1; stats["bytes"] += len(data)
            else:
                with lock:
                    stats["bad"] += 1
        except Exception as e:
            with lock:
                stats["err"] += 1
                with open(LOG, "a", encoding="utf-8") as f:
                    f.write(f"ERR {url} -> {dest}: {e}\n")
        finally:
            q.task_done()


def main():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    plats = sys.argv[1:] or [os.path.splitext(f)[0] for f in os.listdir(os.path.join(LB, "Data", "Platforms"))]
    jobs = []
    for p in plats:
        j = jobs_for(p, c)
        print(f"{p}: {len(j)} images to fetch", flush=True)
        jobs += j
    q, lock, stats = queue.Queue(), threading.Lock(), {"ok": 0, "bad": 0, "err": 0, "bytes": 0}
    ts = [threading.Thread(target=worker, args=(q, stats, lock), daemon=True) for _ in range(12)]
    for t in ts:
        t.start()
    for j in jobs:
        q.put(j)
    t0 = time.time()
    while q.unfinished_tasks:
        time.sleep(30)
        print(f"  {stats['ok']} saved, {stats['err']} errors, {stats['bad']} not images, "
              f"{stats['bytes']/1024**3:.1f} GB, {time.time()-t0:.0f}s", flush=True)
    for _ in ts:
        q.put(None)
    print(f"DONE: {stats['ok']} saved, {stats['err']} errors, {stats['bad']} not images, {stats['bytes']/1024**3:.2f} GB", flush=True)


if __name__ == "__main__":
    main()
