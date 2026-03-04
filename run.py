import asyncio
import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from src.automation import AutomationResult
from src.automation import run as run_automation
from src.credentials import clear_config, ensure_credentials
from src.scanners.hilan_scanner_test import ReportType

REPORT_TYPE_VALUES = [member.value for member in ReportType]
CHROME_APP_PATH = Path("/Applications/Google Chrome.app")


class HilanLauncher:
    def __init__(self, root: tk.Tk, credentials: tuple[str, str]):
        self.root = root
        self.root.title("Hilan Automation")
        self.root.resizable(False, False)
        self.username, self.password = credentials
        self.overrides: dict[str, str] = {}

        self._build_ui()
        self.root.eval("tk::PlaceWindow . center")

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.grid(sticky="nsew")

        override_frame = ttk.LabelFrame(main, text="Date Overrides", padding=8)
        override_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(override_frame, text="Date (DD/MM):").grid(row=0, column=0, padx=(0, 4))
        self.date_entry = ttk.Entry(override_frame, width=8)
        self.date_entry.grid(row=0, column=1, padx=(0, 12))

        ttk.Label(override_frame, text="Report Type:").grid(row=0, column=2, padx=(0, 4))
        self.type_combo = ttk.Combobox(
            override_frame,
            values=REPORT_TYPE_VALUES,
            state="readonly",
            width=24,
        )
        self.type_combo.grid(row=0, column=3, padx=(0, 12))

        ttk.Button(override_frame, text="Add", command=self._add_override).grid(row=0, column=4)

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

        ttk.Button(btn_frame, text="Remove Selected", command=self._remove_selected).pack(side="left")
        ttk.Button(btn_frame, text="Logout", command=self._logout).pack(side="left", padx=(8, 0))
        ttk.Button(btn_frame, text="Run", command=self._run).pack(side="right")

    def _add_override(self):
        raw_date = self.date_entry.get().strip()
        if not re.fullmatch(r"\d{2}/\d{2}", raw_date):
            messagebox.showwarning("Invalid date", "Date must be in DD/MM format (e.g. 02/03).")
            return

        selected = self.type_combo.get()
        if not selected:
            messagebox.showwarning("No type", "Please select a report type.")
            return

        self.overrides[raw_date] = selected
        self._refresh_tree()
        self.date_entry.delete(0, "end")

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
        clear_config()

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

        os.environ["HILAN_USERNAME"] = self.username
        os.environ["HILAN_PASSWORD"] = self.password

        overrides = {date: ReportType(val) for date, val in self.overrides.items()}

        self.root.destroy()
        result = asyncio.run(run_automation(overrides))
        _show_result(result)


def _show_result(result: AutomationResult):
    popup = tk.Tk()
    popup.withdraw()

    if not result.success:
        messagebox.showerror("Automation Failed", f"Failed after filling {result.filled} report(s).\n\n{result.error}", parent=popup)
    elif result.filled == 0:
        messagebox.showinfo("No Reports", "No pending reports were found.", parent=popup)
    else:
        messagebox.showinfo("Success", f"Successfully filled {result.filled} report(s).", parent=popup)

    popup.destroy()


def main():
    root = tk.Tk()
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
