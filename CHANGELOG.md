# What's Changed

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
