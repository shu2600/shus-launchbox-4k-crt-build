"""Combine a chosen bezel/TV preset with a different CRT style and add the result to that system's review page.
Duimon presets pull their CRT from zzz_global_params/Base_Shader/...; the combo copies the preset next to the
original and points it at a Local_Shader instead (01-14, e.g. 13 = super-xBR + Guest, 09 = NTSC composite).
Usage: py -I bezel_combo.py <system-key> <shot-number> <local-shader-number> [label]"""
import os, sys, json
sys.argv_saved = list(sys.argv)
sys.argv = [sys.argv[0]]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bezel_review as b

STYLE = {"01": "smooth Guest", "02": "smooth Guest + NTSC", "03": "smooth Megatron", "04": "smooth Megatron + NTSC",
         "05": "Easymode", "06": "Guest", "07": "Guest mini", "08": "Guest mini + NTSC", "09": "Guest + NTSC composite",
         "10": "Megatron", "11": "Megatron + NTSC", "12": "ReShade FX + Guest", "13": "super-xBR + Guest", "14": "super-xBR + Guest + NTSC"}


def combo(key, n, style):
    log = json.load(open(os.path.join(b.OUT, key, "log.json")))
    shot = next(s for s in log["shots"] if s["n"] == n)
    src = os.path.join(b.SH, shot["preset"])
    text = open(src, encoding="utf-8").read()
    old = '#reference "../../../zzz_global_params/Base_Shader/'
    if old not in text:
        raise SystemExit("this preset does not use the Duimon base-shader switch; pick a Duimon TV/system preset")
    lines = []
    for line in text.splitlines():
        if line.startswith(old):
            line = f'#reference "../../../zzz_global_params/Local_Shader/ADV_{style}.slangp"'
        lines.append(line)
    dst = src[:-7] + f"-[S{style}].slangp"
    open(dst, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    label = f"{b.nice(shot['label'])} + {STYLE[style]} (combo)"
    return dst, label, shot.get("extra", []), log


def render(key, preset, label, extra, log):
    plat, core, prefix, frames, _, _ = b.SYSTEMS[key]
    title, gpath = b.game_path(plat, prefix)
    d = os.path.join(b.OUT, key)
    n = max(s["n"] for s in log["shots"]) + 1
    w = b.wrapper(n, preset, extra)
    shot = os.path.join(b.TMP, f"shot_{key}.cfg")
    png = os.path.join(d, f"{n:02d}.png")
    args = ["--appendconfig", shot, "--set-shader", w, "-L", f"cores\\{core}_libretro.dll",
            f"--max-frames={frames if key in b.NOSTATE else 40}", "--max-frames-ss", f"--max-frames-ss-path={png}", gpath]
    b.run(args)
    ok = os.path.exists(png)
    if ok:
        b.thumb(png, os.path.join(d, f"{n:02d}.jpg"), 1280)
        b.thumb(png, os.path.join(d, f"{n:02d}_full.jpg"), 3840)
        os.remove(png)
    log["shots"].append({"n": n, "label": label, "preset": os.path.relpath(preset, b.SH), "extra": extra, "ok": ok,
                         "secs": 0, "crt": b.crt_name(preset)})
    json.dump(log, open(os.path.join(d, "log.json"), "w"), indent=1)
    b.write_page(key, log)
    return n, ok


if __name__ == "__main__":
    a = sys.argv_saved
    key, n, style = a[1], int(a[2]), a[3].zfill(2)
    preset, label, extra, log = combo(key, n, style)
    num, ok = render(key, preset, label, extra, log)
    print(f"{key}: new shot #{num} {'ok' if ok else 'FAILED'} - {label} | CRT: {b.crt_name(preset)}")
