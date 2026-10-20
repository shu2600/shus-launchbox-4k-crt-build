"""Put the PC's bezel/CRT picks on the Steam Deck, using the lighter Mega Bezel STD presets (800p + battery).
Writes, over SSH, a core preset (config/<Core>/<Core>.slangp) and a content-folder preset (config/<Core>/<romfolder>.slangp,
which is what EmuDeck uses and which wins over the core preset) for every core ES-DE may use for that system.
Old presets are kept as .bak_emudeck. Also sets aspect to Full for those cores (Mega Bezel draws its own frame).
Usage: py -I deck_bezels.py [--dry]"""
import subprocess, sys
import os as _os, sys as _sys
_here = _os.path.dirname(_os.path.abspath(__file__))
_sys.path[:0] = [_here, _os.path.join(_here, "..", "lb_build")]   # lbconfig lives with the build tools
import lbconfig as C  # paths from lb_settings.json
DECK = C.DECK.get("host", "deck@steamdeck")
RA = "/home/deck/.var/app/org.libretro.RetroArch/config/retroarch"
SH = RA + "/shaders/Mega_Bezel_Packs/Duimon-Mega-Bezel/Presets/Standard"
BG = RA + "/shaders/Mega_Bezel_Packs/Duimon-Mega-Bezel/Graphics/_Backgrounds/PVM_background_03.jpg"
TV6 = [f'#reference "{SH}/TV/TV6-[STD]-[Guest].slangp"']
TV4 = [f'#reference "{SH}/TV/TV4-[STD]-[Guest].slangp"', 'HSM_VIEWPORT_ZOOM = "92.000000"', f'BackgroundImage = "{BG}"']
PICKS = {  # rom folder: ([cores], preset lines)
    "atari2600": (["Stella"], TV6),
    "atari5200": (["a5200", "Atari800"], TV6),
    "atari7800": (["ProSystem"], TV6),
    "colecovision": (["Gearcoleco", "blueMSX"], TV6),
    "intellivision": (["FreeIntv"], TV6),
    "zxspectrum": (["Fuse"], TV6),
    "atarijaguar": (["Virtual Jaguar"], [f'#reference "{RA}/shaders/shaders_slang/bezel/Mega_Bezel/Presets/Base_CRT_Presets/MBZ__3__STD__GDV.slangp"']),
    "atarilynx": (["Handy", "Beetle Lynx"], [f'#reference "{SH}/Atari_Lynx/Lynx_Alt-[STD]-[LCD-GRID].slangp"']),
    "atarist": (["Hatari"], [f'#reference "{SH}/Atari_ST/Atari_ST-[STD]-[Guest]-[Monitor].slangp"', 'HSM_BG_OPACITY = "0.000000"']),
    "amiga": (["PUAE"], [f'#reference "{RA}/shaders/Mega_Bezel_Packs/thenamec-commodore-pack/presets/Commodore_Amiga500Plus/Commodore_C1084S-D1/MBZ_SHARP_STD/FULLDEVICE_CURVED_DAY.slangp"', 'HSM_BG_OPACITY = "0.000000"']),
    "vectrex": (["vecx"], [f'#reference "{SH}/GCE_Vectrex/GCE_Vectrex-[STD]-[Guest].slangp"', 'HSM_TUBE_COLORED_GEL_IMAGE_FLIP_VERTICAL = "1.000000"']),
    "tg16": (["Beetle PCE", "Beetle PCE Fast"], TV4),
    "pcengine": (["Beetle PCE", "Beetle PCE Fast"], TV4),
    "megadrive": (["Genesis Plus GX", "PicoDrive"], TV4),
    "genesis": (["Genesis Plus GX", "PicoDrive"], TV4),
    "snes": (["Snes9x", "bsnes-hd beta"], TV4),
    "n64": (["Mupen64Plus-Next"], TV4),
    "neogeo": (["FinalBurn Neo"], TV4),
    "dreamcast": (["Flycast"], [f'#reference "{SH}/SEGA_Dreamcast/Dreamcast-[STD]-[Guest]-[Monitor].slangp"', 'HSM_BG_OPACITY = "0.000000"']),
    "ngpc": (["Beetle NeoPop"], [f'#reference "{SH}/Neo_Geo_Pocket_Color/NGPC-[STD]-[LCD-GRID].slangp"']),
}

lines = ["set -e"]
for folder, (cores, preset) in PICKS.items():
    body = ("\\n".join(preset + ['HSM_INTRO_WHEN_TO_SHOW = "0.000000"']) + "\\n").replace('"', '\\"')
    for core in cores:
        d = f'{RA}/config/{core}'
        for name in (core, folder):
            f = f'{d}/{name}.slangp'
            lines.append(f'mkdir -p "{d}"; [ -f "{f}" ] && [ ! -f "{f}.bak_emudeck" ] && cp "{f}" "{f}.bak_emudeck" || true')
            lines.append(f'printf "{body}" > "{f}"')
        cfg = f'{d}/{core}.cfg'
        lines.append(f'touch "{cfg}"; grep -q "^aspect_ratio_index" "{cfg}" && sed -i "s/^aspect_ratio_index.*/aspect_ratio_index = \\"24\\"/" "{cfg}" || echo "aspect_ratio_index = \\"24\\"" >> "{cfg}"')
script = "\n".join(lines) + "\necho done\n"
if "--dry" in sys.argv:
    print(script[:3000])
else:
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", DECK, "bash -s"], input=script.encode(), capture_output=True)
    print(r.stdout.decode()[-500:], r.stderr.decode()[-500:])
