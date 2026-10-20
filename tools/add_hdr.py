"""Add a second RetroArch emulator to LaunchBox for the HDR TV: same cores, HDR on, Mega Bezel Sony Megatron HDR CRT preset.
Non-default, so every RetroArch platform keeps the normal SDR setup and gets 'RetroArch TV HDR' as a Launch With choice."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import lb_build as B
import xml.etree.ElementTree as ET

RA = B.C.RA_DIR
cfg = os.path.join(RA, "hdr_tv.cfg")
preset = os.path.join(RA, r"shaders\shaders_slang\hdr\crt-sony-megatron-default-hdr.slangp")
assert os.path.exists(preset), preset
with open(cfg, "w", encoding="utf-8") as f:
    f.write('video_hdr_enable = "true"\n'
            'video_hdr_max_nits = "1000.000000"\n'
            'video_hdr_paper_white_nits = "200.000000"\n'
            'auto_shaders_enable = "false"\n'
            'video_shader_enable = "true"\n'
            f'video_shader = "{preset}"\n')

emus = B.load(os.path.join(B.DATA, "Emulators.xml"))
ra_id = B.gid("emulator", "RetroArch")
hdr_id = B.gid("emulator", "RetroArch TV HDR")
if not any(e.findtext("ID") == hdr_id for e in emus.findall("Emulator")):
    e = ET.SubElement(emus, "Emulator")
    for k, v in [("ApplicationPath", B.RA), ("CommandLine", f'-f --appendconfig "{cfg}"'), ("ID", hdr_id),
                 ("Title", "RetroArch TV HDR"), ("NoQuotes", "false"), ("NoSpace", "false"), ("HideConsole", "false"),
                 ("FileNameWithoutExtensionAndPath", "false"), ("AutoExtract", "false"), ("UseStartupScreen", "true"),
                 ("UsePauseScreen", "true")]:
        B.sub(e, k, v)
n = 0
for ep in list(emus.findall("EmulatorPlatform")):
    if ep.findtext("Emulator") != ra_id:
        continue
    plat = ep.findtext("Platform")
    if any(x.findtext("Emulator") == hdr_id and x.findtext("Platform") == plat for x in emus.findall("EmulatorPlatform")):
        continue
    x = ET.SubElement(emus, "EmulatorPlatform")
    B.sub(x, "Emulator", hdr_id)
    B.sub(x, "Platform", plat)
    B.sub(x, "CommandLine", ep.findtext("CommandLine") or "")
    B.sub(x, "Default", "false")
    B.sub(x, "M3uDiscLoadEnabled", "false")
    n += 1
B.write_xml(emus, os.path.join(B.DATA, "Emulators.xml"))
print("HDR emulator added to", n, "platforms;", cfg)
