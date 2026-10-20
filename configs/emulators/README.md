# Per-game 60 fps and widescreen settings

These small files switch on patches that already ship with each emulator (or its community patch list). They contain no game data. Copy each folder's contents into the matching folder of your emulator.

| Emulator | Copy to | What it does |
|---|---|---|
| PCSX2 (PS2) | `PCSX2\gamesettings\` | Black: widescreen + 60 fps + no reload blur. Red Dead Revolver: 60 fps, blur off, black bars off. Manhunt: widescreen + 60 fps + crane fix |
| RPCS3 (PS3) | `config\custom_configs\` | Red Dead Redemption GOTY (BLUS30758 v1.00): vblank 120 for the Unlock FPS patch; enable "Unlock FPS" and "Disable Motion Blur" in Manage Game Patches |
| Xenia Canary (360) | `config\` next to `xenia_canary.exe` | Fight Night Champion: 120 fps cap. Also enable "Unlock FPS" in its patch file, set `gpu = "vulkan"` and `readback_resolve = "fast"`, and put any file in `content\45410915\00000002\` (avoids the EA-logo freeze) |
| Dolphin (GameCube) | `User\GameSettings\` | Super Mario Sunshine and Melee: the widescreen Gecko codes Dolphin ships, at 16:9 |

File names carry the game's serial and disc checksum (PCSX2 `SERIAL_CRC.ini`), so they only affect that exact version.
