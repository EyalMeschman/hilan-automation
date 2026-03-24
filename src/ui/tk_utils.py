import sys

import ttkbootstrap as ttb


def fix_retina_scaling(window: ttb.Window) -> None:
    """Fix Tk DPI scaling for PyInstaller bundles on macOS Retina displays.

    Bundled Tk may not detect the backing scale factor, causing the UI
    to render at 1x.  Uses the ObjC runtime to read the real factor and
    adjusts Tk's scaling when it appears too low.
    """
    if sys.platform != "darwin" or not getattr(sys, "_MEIPASS", None):
        return
    try:
        from ctypes import c_double, c_void_p, cdll  # noqa: PLC0415

        objc = cdll.LoadLibrary("/usr/lib/libobjc.dylib")
        objc.objc_getClass.restype = c_void_p
        objc.sel_registerName.restype = c_void_p
        objc.objc_msgSend.restype = c_void_p

        ns_screen = objc.objc_getClass(b"NSScreen")
        main_screen = objc.objc_msgSend(ns_screen, objc.sel_registerName(b"mainScreen"))

        objc.objc_msgSend.restype = c_double
        scale = objc.objc_msgSend(main_screen, objc.sel_registerName(b"backingScaleFactor"))

        if scale > 1.0:
            current = float(window.tk.call("tk", "scaling"))
            if current < 1.5:
                window.tk.call("tk", "scaling", current * scale)
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
