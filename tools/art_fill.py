"""Fill the art gaps lb_art.py leaves. For every game with no cover or no gameplay screenshot:
1. Use its LaunchBox database match, or find one by a looser name match (same platform, names compared without
   punctuation or spacing, plus alternate titles and a close-spelling check), e.g. "Jahangir Khans ..." -> "Jahangir Khan ...".
2. Cover: the first the database has of Box - Front, Box - Front - Reconstructed, Fanart - Box - Front, Box - 3D,
   Advertisement Flyer - Front (arcade games mostly never had boxes; the flyer is the cover).
3. Screenshot: Screenshot - Gameplay, then Screenshot - Game Title, then Screenshot - Game Select.
Images only, named the way LaunchBox looks them up, so LaunchBox can stay open. Never overwrites existing art.
Usage: py -I art_fill.py [--apply] [platform ...]   (dry run without --apply)"""
import difflib
import os
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbconfig as C  # noqa: E402
import lb_art as ART  # noqa: E402

LB = C.LB
COVER = ["Box - Front", "Box - Front - Reconstructed", "Fanart - Box - Front", "Box - 3D", "Advertisement Flyer - Front"]
SHOT = ["Screenshot - Gameplay", "Screenshot - Game Title", "Screenshot - Game Select"]


def norm(t: str) -> str:
    t = t.lower().replace("&", "and")
    t = re.sub(r"\(.*?\)|\[.*?\]", "", t)
    t = re.sub(r",\s*the$", "", t.strip())
    t = re.sub(r"^the\s+", "", t)
    return re.sub(r"[^a-z0-9]", "", t)


ROMAN = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}


def numbers(t: str) -> set:
    """Sequel numbers in a title, Roman or Arabic: 'Football Director II v2' -> {'2'}."""
    words = re.findall(r"[a-z0-9]+", re.sub(r"\(.*?\)|\[.*?\]", "", t.lower()))
    return {ROMAN.get(w, w) for w in words if w.isdigit() or w in ROMAN}


def has(plat, kind, title):
    folder = os.path.join(LB, "Images", plat, kind)
    stem = ART.safe(title) + "-"
    for dp, _d, fs in os.walk(folder):
        if any(f.startswith(stem) for f in fs):
            return True
    return False


class Matcher:
    def __init__(self, c, plat):
        self.c, self.by = c, {}
        rows = c.execute("select DatabaseID, Name from Games where Platform=?", (plat,)).fetchall()
        rows += c.execute("select a.DatabaseID, a.AlternateName from GameAlternateTitles a join Games g "
                          "on g.DatabaseID=a.DatabaseID where g.Platform=?", (plat,)).fetchall()
        for dbid, name in rows:
            self.by.setdefault(norm(name or ""), dbid)
        self.keys = list(self.by)

    def find(self, title):
        k = norm(title)
        if not k:
            return None, ""
        if k in self.by:
            return self.by[k], "name"
        for cand in difflib.get_close_matches(k, self.keys, n=3, cutoff=0.92):
            # a close spelling must carry the same numbers, so sequels never swap (Turrican 2 is not Turrican)
            name = self.c.execute("select Name from Games where DatabaseID=?", (self.by[cand],)).fetchone()
            if name and numbers(title) == numbers(name[0]):
                return self.by[cand], "close"
        return None, ""


def pick(c, dbid, types):
    imgs = c.execute("select FileName, Type, Region from GameImages where DatabaseId=?", (int(dbid),)).fetchall()
    for t in types:
        cands = sorted([i for i in imgs if i[1] == t], key=lambda i: ART.region_rank(i[2]))
        if cands:
            return cands[0][0], t
    return None, None


def main():
    apply = "--apply" in sys.argv
    plats = [a for a in sys.argv[1:] if a != "--apply"] or \
        [os.path.splitext(f)[0] for f in os.listdir(os.path.join(LB, "Data", "Platforms"))]
    c = sqlite3.connect(f"file:{ART.DB}?mode=ro", uri=True)
    jobs, total = [], {"cover": 0, "shot": 0, "matched_now": 0, "no_match": 0, "no_art": 0}
    for plat in plats:
        root = ET.parse(os.path.join(LB, "Data", "Platforms", f"{plat}.xml")).getroot()
        m, pc, ps = None, 0, 0
        for g in root.findall("Game"):
            title = g.findtext("Title") or ""
            need_cover = not (has(plat, "Box - Front", title) or has(plat, "Box - 3D", title))
            need_shot = not has(plat, "Screenshot - Gameplay", title)
            if not (need_cover or need_shot):
                continue
            dbid = g.findtext("DatabaseID")
            if not dbid:
                m = m or Matcher(c, plat)
                dbid, how = m.find(title)
                if not dbid:
                    total["no_match"] += 1
                    continue
                total["matched_now"] += 1
            for need, types, folder, key in ((need_cover, COVER, "Box - Front", "cover"),
                                             (need_shot, SHOT, "Screenshot - Gameplay", "shot")):
                if not need:
                    continue
                fn, _t = pick(c, dbid, types)
                if not fn:
                    total["no_art"] += 1
                    continue
                dest = os.path.join(LB, "Images", plat, folder, f"{ART.safe(title)}-01{os.path.splitext(fn)[1]}")
                jobs.append((ART.URL + fn, dest))
                total[key] += 1
                if key == "cover":
                    pc += 1
                else:
                    ps += 1
        if pc or ps:
            print(f"{plat}: {pc} covers, {ps} screenshots to fetch", flush=True)
    print(f"TOTAL: {total['cover']} covers + {total['shot']} screenshots; {total['matched_now']} games newly matched by name, "
          f"{total['no_match']} still unmatched, {total['no_art']} gaps the database has no art for", flush=True)
    if not apply:
        print("DRY RUN: nothing downloaded. Add --apply.")
        return
    import queue
    import threading
    import time
    q, lock, stats = queue.Queue(), threading.Lock(), {"ok": 0, "bad": 0, "err": 0, "bytes": 0}
    ts = [threading.Thread(target=ART.worker, args=(q, stats, lock), daemon=True) for _ in range(12)]
    for t in ts:
        t.start()
    for j in jobs:
        q.put(j)
    while q.unfinished_tasks:
        time.sleep(10)
    for _ in ts:
        q.put(None)
    print(f"DONE: {stats['ok']} saved, {stats['err']} errors, {stats['bad']} not images", flush=True)


if __name__ == "__main__":
    main()
