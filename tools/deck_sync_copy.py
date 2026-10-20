"""Stream the files in deck_sync_list.json to the Deck's EmuDeck roms folder as one tar over SSH.
Existing files with the same name and size on the Deck are skipped."""
import json, os, subprocess, tarfile, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = os.path.expanduser(r"~\.ssh\id_ed25519")
import os as _os, sys as _sys
_here = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:0] = [_here, _os.path.join(_here, "..", "lb_build")]   # lbconfig lives with the build tools
import lbconfig as C  # paths from lb_settings.json
HOST = C.DECK.get("host", "deck@steamdeck")
ROMS = C.DECK.get("roms", "/home/deck/Emulation/roms")
SSH = ["ssh", "-i", KEY, "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=30", HOST]

items = json.load(open(os.path.join(HERE, "deck_sync_list.json")))
have = {}
out = subprocess.run(SSH + [f"cd {ROMS} && find . -type f -printf '%P\\t%s\\n'"], capture_output=True, text=True).stdout
for line in out.splitlines():
    p, s = line.rsplit("\t", 1)
    have[p.lower()] = int(s)
todo = [it for it in items if have.get(it["dst"].lower()) != it["size"]]
total = sum(it["size"] for it in todo)
print(f"{len(todo)} files to send, {total/1e9:.1f} GB ({len(items)-len(todo)} already there)", flush=True)

proc = subprocess.Popen(SSH + [f"cd {ROMS} && tar -xf -"], stdin=subprocess.PIPE)
sent, t0 = 0, time.time()
with tarfile.open(fileobj=proc.stdin, mode="w|") as tar:
    for i, it in enumerate(todo, 1):
        tar.add(it["src"], arcname=it["dst"], recursive=False)
        sent += it["size"]
        if i % 200 == 0 or it["size"] > 500e6:
            rate = sent / max(1, time.time() - t0) / 1e6
            print(f"{i}/{len(todo)} {sent/1e9:.1f}/{total/1e9:.1f} GB {rate:.0f} MB/s  {it['dst']}", flush=True)
proc.stdin.close()
rc = proc.wait()
print("done rc", rc, f"{sent/1e9:.1f} GB in {(time.time()-t0)/60:.0f} min", flush=True)
