"""List (and optionally enable) RPCS3 patches for the PS3 games you have, matched by title ID + game version.
Reads <PS3>/patches/patch.yml (from rpcs3.net) and the PARAM.SFO of each game folder; writes
<PS3>/config/patch_config.yml (backup .bak first). Usage: py -I rpcs3_patches.py [--enable "Patch name" ...]"""
import os, sys, struct, glob, shutil
import yaml

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C

PS3 = os.path.join(C.ROOT, "PS3")


class Loader(yaml.SafeLoader):   # patch.yml reuses anchor names; RPCS3's own parser allows it, PyYAML does not
    def compose_node(self, parent, index):
        if self.check_event(yaml.events.AliasEvent):
            return super().compose_node(parent, index)
        ev = self.peek_event()
        if getattr(ev, "anchor", None) in self.anchors:
            del self.anchors[ev.anchor]
        return super().compose_node(parent, index)


def sfo(path):
    d = open(path, "rb").read()
    _m, _v, kt, dt, n = struct.unpack("<4sIIII", d[:20])
    out = {}
    for i in range(n):
        ko, fmt, ln, _mx, do = struct.unpack("<HHIII", d[20 + i * 16:36 + i * 16])
        k = d[kt + ko:d.index(b"\0", kt + ko)].decode()
        v = d[dt + do:dt + do + ln]
        out[k] = v.rstrip(b"\0").decode("utf-8", "replace") if fmt != 0x0404 else struct.unpack("<I", v)[0]
    return out


games = {}
for p in glob.glob(os.path.join(PS3, "ROMS", "*", "PS3_GAME", "PARAM.SFO")):
    s = sfo(p)
    games[s["TITLE_ID"]] = (s.get("APP_VER") or s.get("VERSION") or "01.00", s.get("TITLE"))
for tid, (ver, title) in list(games.items()):   # installed updates raise the version
    up = os.path.join(PS3, "dev_hdd0", "game", tid, "PARAM.SFO")
    if os.path.exists(up):
        u = sfo(up)
        if u.get("APP_VER") and u["APP_VER"] > ver:
            games[tid] = (u["APP_VER"], title)

db = yaml.load(open(os.path.join(PS3, "patches", "patch.yml"), encoding="utf-8"), Loader=Loader)
found = []
for h, patches in db.items():
    if not str(h).startswith("PPU-") or not isinstance(patches, dict):
        continue
    for name, p in patches.items():
        for gtitle, sers in ((p or {}).get("Games") or {}).items():
            for sid, vers in (sers or {}).items():
                # YAML reads 01.00 as the number 1.0: compare as '01.00' strings
                vers = ["%05.2f" % v if isinstance(v, float) else str(v) for v in (vers or [])]
                if sid in games and (games[sid][0] in vers or "All" in vers):
                    found.append((h, name, gtitle, sid, games[sid][0]))
for tid, (ver, title) in sorted(games.items()):
    names = [f[1] for f in found if f[3] == tid]
    print(f"{tid} v{ver} {title}: {names or 'no patches for this version'}")

if "--enable" in sys.argv:
    want = set(sys.argv[sys.argv.index("--enable") + 1:])
    cfg_path = os.path.join(PS3, "config", "patch_config.yml")
    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else None
    cfg = cfg or {}
    if os.path.exists(cfg_path):
        shutil.copy2(cfg_path, cfg_path + ".bak")
    for h, name, gtitle, sid, ver in found:
        if name in want:
            cfg.setdefault(h, {}).setdefault(name, {}).setdefault(gtitle, {}).setdefault(sid, {})[ver] = {"Enabled": True}
            print("enabled:", sid, ver, name)
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    yaml.safe_dump(cfg, open(cfg_path, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
