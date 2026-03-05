import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttb

from src.hilan import ConfirmAction, ReportType

REPORT_TYPE_VALUES = [member.value for member in ReportType]


def _center_and_show(dialog: ttb.Toplevel):
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    dialog.lift()
    dialog.attributes("-topmost", True)


class TkCallbacks:
    def __init__(self, parent: tk.Tk):
        self.parent = parent

    def on_manual_action(self, date_str: str, report_type: str) -> None:
        """Blocks until the user finishes handling the site popup and clicks Continue."""
        dialog = ttb.Toplevel(master=self.parent, title="Action Required")
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=(20, 16))
        frame.pack()

        ttk.Label(
            frame,
            text=f"Date: {date_str}  |  Type: {report_type}",
            font=("", 13),
        ).pack(pady=(0, 8))
        ttk.Label(
            frame,
            text=(
                "This report type requires your attention.\n"
                "Handle the message shown on the site,\n"
                "then click Continue to let the automation proceed."
            ),
            justify="center",
        ).pack(pady=(0, 12))
        ttk.Label(
            frame,
            text='Do NOT press "שמור וסגור" yourself.',
            bootstyle="danger",
            font=("", 11, "bold"),
        ).pack(pady=(0, 12))

        ttk.Button(
            frame,
            text="Continue",
            width=12,
            bootstyle="success",
            command=dialog.destroy,
        ).pack()

        _center_and_show(dialog)
        dialog.wait_window()

    def on_confirm(self, date_str: str, report_type: str) -> tuple[ConfirmAction, str | None]:
        """Returns (action, new_type). new_type is set only for CHANGE."""
        result_action = ConfirmAction.EXIT
        result_type: str | None = None

        dialog = ttb.Toplevel(master=self.parent, title="Confirm Report")
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=(20, 16))
        frame.pack()

        ttk.Label(frame, text=f"Date: {date_str}\nType: {report_type}", font=("", 13), justify="left").pack(pady=(0, 8))
        ttk.Label(frame, text="Review the report in the browser.").pack(pady=(0, 12))

        change_frame = ttk.Frame(frame)
        change_frame.pack(pady=(0, 12))

        type_combo = ttk.Combobox(change_frame, values=REPORT_TYPE_VALUES, state="readonly", width=20)
        type_combo.pack(side="left", padx=(0, 4))

        def choose(action: str):
            nonlocal result_action, result_type
            if action == ConfirmAction.CHANGE and not type_combo.get():
                error_label.config(text="Please select a type first.")
                return
            result_action = action
            if action == ConfirmAction.CHANGE:
                result_type = type_combo.get()
            dialog.destroy()

        ttk.Button(change_frame, text="Change type", bootstyle="info", command=lambda: choose(ConfirmAction.CHANGE)).pack(side="left")

        error_label = ttk.Label(frame, text="", bootstyle="danger")
        error_label.pack()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack()

        save_cmd = lambda: choose(ConfirmAction.SAVE)  # noqa: E731
        exit_cmd = lambda: choose(ConfirmAction.EXIT)  # noqa: E731
        ttk.Button(btn_frame, text="Save", width=10, bootstyle="success", command=save_cmd).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Exit run", width=10, bootstyle="danger", command=exit_cmd).pack(side="left", padx=4)

        _center_and_show(dialog)
        dialog.wait_window()
        return result_action, result_type
