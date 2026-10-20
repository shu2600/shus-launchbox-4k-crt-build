# Guide

Every command runs from the `tools` folder. Close LaunchBox before any step that says so: LaunchBox rewrites its `Data` folder when it exits and would undo the change.

## 1. Settings

Copy `lb_settings.example.json` to `lb_settings.json` and fill it in:

| Key | What it is |
|---|---|
| `emulation_root` | The top folder that holds your ROM folders and emulators |
| `launchbox` | Your LaunchBox folder (the one with `LaunchBox.exe`) |
| `retroarch` | Your RetroArch folder |
| `mame` | Your MAME folder |
| `work_dir` | Where logs, backups and review renders go |
| `rom_folders` | Optional. Platform key to folders under `emulation_root`, if yours differ from the defaults in `lb_build.py` |
| `emulator_paths` | Optional. Emulator name to exe, if yours differ |
| `favourites` | Optional. LaunchBox platform name to a list of titles, for `fav_mark.py`. End a title with `*` to match every game that starts with it |
| `steam_deck` | Optional. `{"host": "deck@steamdeck", "roms": "/run/media/deck/<card>/Emulation/roms"}` |

## 2. Build the library (LaunchBox closed)

```
py lb_build.py all              # every platform that has games
py lb_build.py snes md arcade   # or just some (keys are listed in PLATFORMS in lb_build.py)
```

Your `Data` folder is backed up to `<work_dir>/logs/lb_data_backup_<time>` first. Run it again whenever you add games.

## 3. Artwork

```
py lb_art.py                    # LaunchBox's own images, every platform
py crc_thumbs.py                # covers + screenshots by checksum (cartridge systems)
py libretro_thumbs.py           # covers by name
py arcadedb_art.py              # arcade flyers, shots, marquees
py arcadedb_art.py --platform "Nintendo Game & Watch"
py zxdb_inlays.py --kind front|loading|running   # Spectrum (needs the ZXDB SQL dump in <work_dir>/zxdb)
py make_3dbox.py "<Platform>"   # 3D boxes from flat covers
py lb_audit.py                  # what's still missing
```

## 4. Manuals and favourites (LaunchBox closed)

```
py manuals_link.py atari2600 atari7800
py fav_mark.py
py lb_playlists.py
```

## 5. Pick the look

```
py bezel_review.py snes         # renders every candidate look for one system
```

Open `<review_dir>/index.html`, pick a look, then:

```
py apply_pick.py snes 22
py bezel_combo.py snes 22 13 "super-xBR + Guest"   # same frame, different CRT
```

For arcade cabinets: `py arcade_review.py`, then put your chosen artwork set first in MAME's `artpath`.

## 6. Steam Deck (EmuDeck)

Set `steam_deck` in `lb_settings.json` and make sure `ssh deck@<deck>` works with a key (no password prompt).

```
py deck_bezels.py --dry         # shows what it would write
py deck_bezels.py
py deck_sync_plan.py            # works out which games fit
py deck_sync_copy.py
```

## Notes
- Nothing here downloads games, BIOS or firmware.
- Image tools never overwrite a picture you already have.
- A game whose title changes on a rebuild (because it now matches the database) keeps its pictures, video and manual.
