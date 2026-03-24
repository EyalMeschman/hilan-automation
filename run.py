import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

import keyring
import ttkbootstrap as ttb
from ttkbootstrap.widgets import DateEntry

from src.automation import run as run_automation
from src.config import ConfigKey, clear_fields, load_config, update_config
from src.credentials import KEYRING_SERVICE, ensure_credentials
from src.hilan import ReportType
from src.tutorial import show_tutorial_if_needed
from src.ui.tk_utils import fix_retina_scaling, suppress_bgerror

REPORT_TYPE_VALUES = [member.value for member in ReportType]
CHROME_APP_PATH = Path("/Applications/Google Chrome.app")


class HilanLauncher:
    def __init__(self, root: tk.Tk, credentials: tuple[str, str]):
        self.root = root
        self.root.title("Hilan Automation")
        self.root.resizable(False, False)
        self.username, self.password = credentials
        self.overrides: dict[str, ReportType] = {}

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.grid(sticky="nsew")

        override_frame = ttk.LabelFrame(main, text="Date Overrides", padding=8)
        override_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(override_frame, text="From:").grid(row=0, column=0, padx=(0, 4))
        self.from_date = DateEntry(override_frame, dateformat="%d/%m/%Y", width=12)
        self.from_date.grid(row=0, column=1, padx=(0, 12))
        self.from_date.button.pack_configure(padx=(4, 0))
        self.from_date.bind("<<DateEntrySelected>>", lambda _: self._sync_to_date())

        ttk.Label(override_frame, text="To:").grid(row=0, column=2, padx=(0, 4))
        self.to_date = DateEntry(override_frame, dateformat="%d/%m/%Y", width=12)
        self.to_date.grid(row=0, column=3, padx=(0, 12))
        self.to_date.button.pack_configure(padx=(4, 0))
        self.to_date.bind("<<DateEntrySelected>>", lambda _: self._clamp_from_date())

        ttk.Label(override_frame, text="Report Type:").grid(row=1, column=0, padx=(0, 4), pady=(8, 0))
        self.type_combo = ttk.Combobox(
            override_frame,
            values=REPORT_TYPE_VALUES,
            state="readonly",
            width=24,
        )
        self.type_combo.grid(row=1, column=1, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Button(override_frame, text="Add", command=self._add_override).grid(row=1, column=3, sticky="e", pady=(8, 0))

        table_frame = ttk.Frame(main)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        self.tree = ttk.Treeview(table_frame, columns=("date", "type"), show="headings", height=6)
        self.tree.heading("date", text="Date")
        self.tree.heading("type", text="Report Type")
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("type", width=260, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=2, column=0, sticky="ew")

        saved_confirm = load_config().get(ConfigKey.CONFIRM_BEFORE_SAVE, True)
        self.confirm_var = tk.BooleanVar(value=saved_confirm)
        self.confirm_var.trace_add("write", lambda *_: update_config(**{ConfigKey.CONFIRM_BEFORE_SAVE: self.confirm_var.get()}))
        ttk.Checkbutton(btn_frame, text="Confirm before saving", variable=self.confirm_var).pack(side="left")

        ttk.Button(btn_frame, text="Remove Selected", command=self._remove_selected).pack(side="left", padx=(8, 0))
        ttk.Button(btn_frame, text="Logout", command=self._logout).pack(side="left", padx=(8, 0))
        ttk.Button(btn_frame, text="Exit", command=self.root.destroy).pack(side="left", padx=(8, 0))
        ttk.Button(btn_frame, text="Run", command=self._run).pack(side="right")

        self.root.eval("tk::PlaceWindow . center")
        show_tutorial_if_needed(self.root, ConfigKey.SHOW_MAIN_TUTORIAL)

    def _sync_to_date(self):
        self.to_date.set_date(self.from_date.get_date())

    def _clamp_from_date(self):
        if self.to_date.get_date() < self.from_date.get_date():
            self.from_date.set_date(self.to_date.get_date())

    def _add_override(self):
        fmt = "%d/%m/%Y"
        from_str = self.from_date.entry.get().strip()
        to_str = self.to_date.entry.get().strip()

        try:
            start = datetime.strptime(from_str, fmt)
            end = datetime.strptime(to_str, fmt)
        except ValueError:
            messagebox.showwarning("Invalid date", "Please select valid dates.")
            return

        if start > end:
            messagebox.showwarning("Invalid range", "'From' date must be before or equal to 'To' date.")
            return

        selected = self.type_combo.get()
        if not selected:
            messagebox.showwarning("No type", "Please select a report type.")
            return

        current = start
        while current <= end:
            self.overrides[current.strftime("%d/%m")] = ReportType(selected)
            current += timedelta(days=1)

        self._refresh_tree()

    def _remove_selected(self):
        selection = self.tree.selection()
        if not selection:
            return
        for item in selection:
            date = self.tree.item(item, "values")[0]
            self.overrides.pop(date, None)
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for date, report_type in sorted(self.overrides.items()):
            self.tree.insert("", "end", values=(date, report_type))

    def _logout(self):
        keyring.delete_password(KEYRING_SERVICE, self.username)
        clear_fields(ConfigKey.USERNAME)

        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.withdraw()

        credentials = ensure_credentials(self.root)
        if credentials is None:
            self.root.destroy()
            return

        self.username, self.password = credentials
        self.overrides.clear()
        self._build_ui()
        self.root.deiconify()
        self.root.eval("tk::PlaceWindow . center")

    def _run(self):
        if not CHROME_APP_PATH.exists():
            messagebox.showerror(
                "Chrome not found",
                "Google Chrome is required.\nPlease install it from google.com/chrome",
            )
            return

        confirm = self.confirm_var.get()

        self.root.withdraw()
        try:
            result = run_automation(
                self.root,
                self.overrides,
                username=self.username,
                password=self.password,
                confirm_before_save=confirm,
            )
        except Exception as exc:
            self.root.deiconify()
            messagebox.showerror("Automation Error", f"Failed to start automation:\n\n{exc}", parent=self.root)
            return
        self.root.deiconify()

        if result.user_exit:
            return

        if not result.success:
            msg = f"Failed after filling {result.filled} report(s).\n\n{result.error}"
            messagebox.showerror("Automation Failed", msg, parent=self.root)
        elif result.filled == 0:
            messagebox.showinfo("No Reports", "No pending reports were found.", parent=self.root)
        else:
            messagebox.showinfo("Success", f"Successfully filled {result.filled} report(s).", parent=self.root)


def main():
    root = ttb.Window(themename="darkly")
    fix_retina_scaling(root)
    suppress_bgerror(root)
    root.withdraw()

    credentials = ensure_credentials(root)
    if credentials is None:
        root.destroy()
        return

    root.deiconify()
    HilanLauncher(root, credentials)
    root.mainloop()


if __name__ == "__main__":
    main()
