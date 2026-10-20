"""Boot-test every Dreamcast disc in Flycast (RetroArch), minimised and never taking focus, and move the ones that
crash or will not load into Dreamcast\\_broken (kept, not deleted). Usage: py -I dc_test.py"""
import os, subprocess, time, shutil
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lbconfig as C  # paths from lb_settings.json

RA = C.RA_DIR
DC = _os.path.join(C.ROOT, r"Dreamcast")
BAD = os.path.join(DC, "_broken")
LOG = _os.path.join(C.LOGS, r"dc_test")
os.makedirs(BAD, exist_ok=True); os.makedirs(LOG, exist_ok=True)
cfg = os.path.join(LOG, "test.cfg")
open(cfg, "w").write('audio_enable = "false"\nconfig_save_on_exit = "false"\npause_nonactive = "false"\n'
                     'video_fullscreen = "false"\nvideo_shader_enable = "false"\nsavestate_auto_save = "false"\n'
                     'video_window_custom_size_enable = "true"\nvideo_windowed_position_width = "640"\nvideo_windowed_position_height = "480"\n')
FATAL = ("Fatal", "Failed to load content", "Cannot get attributes", "SH4 exception")
good = bad = 0
for f in sorted(os.listdir(DC)):
    if not f.lower().endswith((".cdi", ".chd", ".gdi")):
        continue
    log = os.path.join(LOG, f + ".log")
    si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = 7   # minimised, no focus
    p = subprocess.Popen([os.path.join(RA, "retroarch.exe"), "--appendconfig", cfg, "-L", r"cores\flycast_libretro.dll",
                          "-v", f"--log-file={log}", os.path.join(DC, f)], cwd=RA, startupinfo=si,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time(); died = False
    while time.time() - t0 < 30:
        if p.poll() is not None:
            died = True; break
        time.sleep(1)
    if not died:
        p.kill(); p.wait()
    text = open(log, encoding="utf-8", errors="replace").read() if os.path.exists(log) else ""
    broken = died or any(x in text for x in FATAL)
    if broken:
        shutil.move(os.path.join(DC, f), os.path.join(BAD, f)); bad += 1
    else:
        good += 1
    print(f"{'BROKEN' if broken else 'ok    '} {f}", flush=True)
print(f"done: {good} boot, {bad} moved to _broken")
