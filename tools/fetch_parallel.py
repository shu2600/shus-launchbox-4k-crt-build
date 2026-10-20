"""Download one file in N parallel byte ranges (archive.org throttles each connection), then join.
Usage: py -I fetch_parallel.py <url> <out> [parts=8]"""
import sys, os, urllib.request, concurrent.futures as cf

url, out = sys.argv[1], sys.argv[2]
parts = int(sys.argv[3]) if len(sys.argv) > 3 else 8
req = urllib.request.Request(url, method="HEAD")
size = int(urllib.request.urlopen(req, timeout=60).headers["Content-Length"])
step = size // parts + 1


def get(i):
    import time
    for attempt in range(8):   # archive.org throws the odd 500; retry the piece, keeping what arrived
        try:
            return get_once(i)
        except Exception:
            time.sleep(5 * (attempt + 1))
    return get_once(i)


def get_once(i):
    a, b = i * step, min(size - 1, (i + 1) * step - 1)
    part = f"{out}.part{i}"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if have >= b - a + 1:
        return part
    r = urllib.request.Request(url, headers={"Range": f"bytes={a + have}-{b}"})
    with urllib.request.urlopen(r, timeout=120) as resp, open(part, "ab") as f:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return part


with cf.ThreadPoolExecutor(parts) as ex:
    names = list(ex.map(get, range(parts)))
with open(out, "wb") as o:
    for n in names:
        o.write(open(n, "rb").read()); os.remove(n)
print(f"{os.path.basename(out)} {os.path.getsize(out) == size} {size/1e6:.0f} MB")
