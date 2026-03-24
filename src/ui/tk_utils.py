import sys

import ttkbootstrap as ttb

RETINA_SCALE = 2.0


def fix_retina_scaling(window: ttb.Window) -> None:
    """Fix Tk DPI scaling for PyInstaller bundles on macOS Retina displays.

    Bundled Tk may not detect the backing scale factor, causing the UI
    to render at 1x.  When the reported scaling is suspiciously low on
    a Mac (all modern Macs are Retina / 2x), double it.
    """
    if sys.platform != "darwin" or not getattr(sys, "_MEIPASS", None):
        return
    try:
        current = float(window.tk.call("tk", "scaling"))
        if current < 1.5:
            window.tk.call("tk", "scaling", current * RETINA_SCALE)
    except Exception:
        pass


def suppress_bgerror(window: ttb.Window) -> None:
    """Replace Tcl's bgerror with a no-op.

    ttkbootstrap and macOS Tk schedule background events that can
    produce noisy stderr messages.  Call once on the root window at
    creation time; the override covers all Toplevel children sharing
    the same Tcl interpreter.
    """
    try:
        window.tk.eval("proc bgerror {msg} {}")
    except Exception:
        pass
