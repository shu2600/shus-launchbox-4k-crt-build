# What's Changed

## 1.2.2 (23 October 2026)

- Added a line about me to the README, I'm an old school web developer and coder and this is how I build now.

## 1.2.1 (23 October 2026)

- Went back over the README and this changelog so they read more like me.

## 1.2 (23 October 2026)

- Your favourites always make the playlists now, tick a game as a favourite in LaunchBox and it goes straight to the top of that system's "Best of" list whatever the community rating says... Mr. Do! deserves better than its score.
- New "Top 100" playlists, your favourites first, then a proper researched top list for that system (in `tools/top_lists`), then the best-rated games to fill it up. Arcade uses the International Arcade Museum's top 100 plus their most popular and most collected lists, more systems coming.
- The same game under two set names (Pac-Man and Puckman, say) only shows once in a playlist now.
- New art gap filler (`art_fill.py`, runs in the wizard after the other art steps). It finds the covers and screenshots the others missed, matches games whose names don't quite line up with the LaunchBox database (typos, translated titles, "Khans" vs "Khan"), uses the flyer as the cover for arcade games that never had a box, and the title screen when there's no gameplay shot. Sequels never get mixed up, Turrican 2 won't get Turrican's box. On my own library it filled 610 missing covers and 283 screenshots.
- The wizard ticks your favourites before it builds the playlists now, so they're at the top from the very first run.

## 1.1.1 (23 October 2026)

- Rewrote the README in my own words, and added a bit on how it's made: Anima, my own AI setup, and its council of other AIs that review the work.

## 1.1 (22 October 2026)

I had the code properly reviewed and it turned up a couple of things I wasn't happy with, so these are sorted:

- The wizard used to say "All done" even when a step had gone wrong. Now it tells you which step failed and why. If the library build itself fails, it stops there instead of carrying on and piling more errors on top.
- If a games folder couldn't be found (a drive not plugged in, say), running the build again could leave that system empty in LaunchBox. Now it leaves your existing list alone and tells you what it couldn't find.
- The check at the end now properly flags a problem when it finds one, instead of just printing it.
- setup.bat now installs everything the tools need (PyYAML was missing) and tells you if the install didn't work, rather than opening the wizard anyway.

Still on my list: tidier default folders, the preview tool closing RetroArch windows it didn't open, checksums on the shader downloads, and some automatic tests.

## 1.0 (20 October 2026)

First release.
