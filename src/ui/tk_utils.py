import ttkbootstrap as ttb


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
