"""Turn The Bezel Project's RetroArch arcade overlays into native MAME artwork (one zip per game: bezel.png + default.lay).
The screen sits in the bezel's transparent hole, found from the PNG's alpha channel. Only games in your LaunchBox
Arcade library are converted. Output goes to Mame\\artwork_bezelproject so it can sit behind Lights Out in artpath."""
import os, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

SRC = _os.path.join(C.DOWNLOADS, r"_bezels\bezelproject-MAME\retroarch\overlay\ArcadeBezels")
OUT = _os.path.join(C.MAME_DIR, r"artwork_bezelproject")
ARCADE_XML = _os.path.join(C.LB, r"Data\Platforms\Arcade.xml")

LAY = """<?xml version="1.0"?>
<mamelayout version="2">
  <element name="bezel"><image file="bezel.png"/></element>
  <view name="Bezel Project">
    <screen index="0"><bounds x="{x}" y="{y}" width="{w}" height="{h}"/></screen>
    <element ref="bezel"><bounds x="0" y="0" width="{W}" height="{H}"/></element>
  </view>
</mamelayout>
"""


def hole(im):
    """Bounding box of the fully transparent screen hole."""
    a = im.getchannel("A")
    mask = a.point(lambda v: 255 if v < 8 else 0)
    return mask.getbbox()


def main():
    games = {os.path.splitext(os.path.basename(g.findtext("ApplicationPath") or ""))[0].lower()
             for g in ET.parse(ARCADE_XML).getroot().findall("Game")}
    os.makedirs(OUT, exist_ok=True)
    done = skipped = bad = 0
    for f in sorted(os.listdir(SRC)):
        name, ext = os.path.splitext(f)
        if ext.lower() != ".png" or name.lower() not in games:
            continue
        dst = os.path.join(OUT, name.lower() + ".zip")
        if os.path.exists(dst):
            skipped += 1
            continue
        p = os.path.join(SRC, f)
        im = Image.open(p).convert("RGBA")
        box = hole(im)
        if not box or (box[2] - box[0]) < 100 or (box[3] - box[1]) < 100:
            bad += 1
            print("no screen hole:", f)
            continue
        x0, y0, x1, y1 = box
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as z:
            z.write(p, "bezel.png")
            z.writestr("default.lay", LAY.format(x=x0, y=y0, w=x1 - x0, h=y1 - y0, W=im.width, H=im.height))
        done += 1
        if done % 250 == 0:
            print(done, "converted", flush=True)
    print(f"converted {done}, already there {skipped}, no hole {bad}")


if __name__ == "__main__":
    main()
