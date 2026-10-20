"""Take a whole platform out of LaunchBox: its game list, its entries in Platforms.xml / Parents.xml and its playlists.
The removed XML is kept in <work_dir>/logs/removed_<platform>_<time>. Game files are not touched here.
LaunchBox must be closed. Usage: py -I lb_remove_platform.py "<LaunchBox platform name>" """
import os, sys, shutil, datetime, glob
import xml.etree.ElementTree as ET

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json
from lb_build import write_xml

name = sys.argv[1]
D = os.path.join(C.LB, "Data")
keep = os.path.join(C.LOGS, f"removed_{name}_{datetime.datetime.now():%Y%m%d_%H%M%S}".replace(" ", "_"))
os.makedirs(keep)
for f in ("Platforms.xml", "Parents.xml"):
    shutil.copy2(os.path.join(D, f), keep)
xml = os.path.join(D, "Platforms", name + ".xml")
if os.path.exists(xml):
    shutil.move(xml, keep)
plats = ET.parse(os.path.join(D, "Platforms.xml")).getroot()
n = 0
for el in list(plats):
    if (el.tag == "Platform" and el.findtext("Name") == name) or (el.tag == "PlatformFolder" and el.findtext("Platform") == name):
        plats.remove(el); n += 1
write_xml(plats, os.path.join(D, "Platforms.xml"))
parents = ET.parse(os.path.join(D, "Parents.xml")).getroot()
for el in list(parents):
    if el.findtext("PlatformName") == name:
        parents.remove(el); n += 1
write_xml(parents, os.path.join(D, "Parents.xml"))
for p in glob.glob(os.path.join(D, "Playlists", "*.xml")):
    if ET.parse(p).getroot().findtext("Playlist/Name") == f"Best of {name}":
        shutil.move(p, keep)
print(f"{name}: removed ({n} entries); kept in {keep}")
