"""Make LaunchBox-style 3D boxes (334x551 RGBA, like the DB's) from a flat front cover: the cover is
perspective-warped onto the front face, and the spine is built from a blurred, darkened slice of the cover's
left edge with a clear plastic case edge. Usage: make_3dbox.py <platform> [--limit N] [--sample]"""
import os, sys, glob
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

LB = C.LB
W, H = 334, 551
FRONT = [(50, 16), (330, 34), (330, 520), (50, 538)]   # TL, TR, BR, BL
SPINE = [(8, 6), (50, 16), (50, 538), (8, 546)]


def coeffs(dst, src):
    """PIL PERSPECTIVE coefficients mapping output (dst quad) back to input (src rect)."""
    import numpy as np
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def warp(img, quad):
    w, h = img.size
    c = coeffs(quad, [(0, 0), (w, 0), (w, h), (0, h)])
    out = img.transform((W, H), Image.PERSPECTIVE, c, Image.BICUBIC)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(quad, fill=255)
    out.putalpha(mask)
    return out


FONT = r"C:\Windows\Fonts\impact.ttf"
BANDS = {  # system band at the top of the spine: label, band colour, text colour, rainbow stripe
    "Sinclair ZX Spectrum": ("SPECTRUM", (20, 20, 20), (255, 255, 255), True),
    "Atari ST": ("ATARI ST", (200, 30, 30), (255, 255, 255), False),
    "Commodore Amiga": ("AMIGA", (30, 60, 160), (255, 255, 255), False),
}


def spine_image(cov, title, platform):
    """Flat spine (portrait, 120 x cover height): cover's main colour, system band on top, title running up."""
    from PIL import ImageFont, ImageStat
    h = cov.height
    base = tuple(int(c * 0.6) for c in ImageStat.Stat(cov.resize((32, 32))).median)
    sp = Image.new("RGB", (120, h), base)
    d = ImageDraw.Draw(sp)
    label, bcol, tcol, rainbow = BANDS.get(platform, (platform.upper(), (25, 25, 25), (255, 255, 255), False))
    band_h = int(h * 0.16)
    d.rectangle([0, 0, 120, band_h], fill=bcol)
    if rainbow:
        for i, c in enumerate([(220, 30, 30), (240, 200, 0), (40, 170, 60), (30, 120, 220)]):
            d.rectangle([0, band_h - 28 + i * 7, 120, band_h - 22 + i * 7], fill=c)
    # system label, rotated, inside the band
    lab = Image.new("RGBA", (band_h - 34, 120), (0, 0, 0, 0))
    f = ImageFont.truetype(FONT, 46)
    while f.getlength(label) > lab.width - 8 and f.size > 14:
        f = ImageFont.truetype(FONT, f.size - 2)
    ImageDraw.Draw(lab).text((lab.width / 2, 60), label, font=f, fill=tcol, anchor="mm")
    sp.paste(lab.rotate(90, expand=True), (0, 4), lab.rotate(90, expand=True))
    # game title running up the spine, white with a dark outline so it reads on any colour
    room = h - band_h - 30
    t = Image.new("RGBA", (room, 120), (0, 0, 0, 0))
    f = ImageFont.truetype(FONT, 78)
    while f.getlength(title) > room - 20 and f.size > 18:
        f = ImageFont.truetype(FONT, f.size - 2)
    ImageDraw.Draw(t).text((room / 2, 60), title, font=f, fill=(255, 255, 255), anchor="mm",
                           stroke_width=3, stroke_fill=(0, 0, 0))
    t = t.rotate(90, expand=True)
    sp.paste(t, (0, band_h + 15), t)
    return sp


def make(front_path, out_path, title="", platform=""):
    cov = Image.open(front_path).convert("RGB")
    cov = cov.resize((600, int(600 * cov.height / cov.width)), Image.LANCZOS)
    box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sl = ImageEnhance.Brightness(spine_image(cov, title, platform)).enhance(0.92)
    box.alpha_composite(warp(sl, SPINE))
    box.alpha_composite(warp(cov, FRONT))
    d = ImageDraw.Draw(box)
    # clear plastic case: thin light edges and a soft glare down the hinge
    d.line([FRONT[0], FRONT[1]], fill=(255, 255, 255, 120), width=2)
    d.line([FRONT[3], FRONT[2]], fill=(0, 0, 0, 140), width=3)
    d.line([SPINE[0], SPINE[1]], fill=(255, 255, 255, 90), width=2)
    d.line([FRONT[0], FRONT[3]], fill=(255, 255, 255, 110), width=2)
    glare = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glare).polygon([(52, 18), (70, 21), (70, 535), (52, 536)], fill=(255, 255, 255, 45))
    box.alpha_composite(glare.filter(ImageFilter.GaussianBlur(3)))
    box.save(out_path)


def main():
    plat = sys.argv[1]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    base = os.path.join(LB, "Images", plat)
    fronts = {os.path.basename(p).rsplit("-", 1)[0]: p for p in glob.glob(os.path.join(base, "Box - Front", "*"))}
    have = {os.path.basename(p).rsplit("-", 1)[0] for p in glob.glob(os.path.join(base, "Box - 3D", "*"))}
    todo = sorted(set(fronts) - have)[:limit]
    os.makedirs(os.path.join(base, "Box - 3D"), exist_ok=True)
    out_dir = os.path.join(base, "Box - 3D") if "--sample" not in sys.argv else _os.path.join(C.LOGS, r"3dbox_sample")
    os.makedirs(out_dir, exist_ok=True)
    import re, xml.etree.ElementTree as ET
    titles = {}
    for g in ET.parse(os.path.join(LB, "Data", "Platforms", plat + ".xml")).getroot().findall("Game"):
        t = g.findtext("Title") or ""
        titles[re.sub(r"[\\/:*?\"<>|']", "_", t)] = t
    n = 0
    for name in todo:
        try:
            make(fronts[name], os.path.join(out_dir, name + "-01.png"), titles.get(name, name), plat)
            n += 1
        except Exception as e:
            print("skip", name, e)
    print(plat, "made", n, "of", len(todo))


if __name__ == "__main__":
    main()
