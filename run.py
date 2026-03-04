import json
import re
import tkinter as tk
from tkinter import messagebox, ttk

import pytest
from dotenv import load_dotenv

from src.scanners.hilan_scanner_test import OVERRIDES_FILE, ReportType

load_dotenv(".env.defaults")
load_dotenv(".env", override=True)

REPORT_TYPE_VALUES = [member.value for member in ReportType]


class HilanLauncher:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Hilan Report Overrides")
        self.root.resizable(False, False)
        self.overrides: dict[str, str] = {}

        self._build_ui()
        self.root.eval("tk::PlaceWindow . center")

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.grid(sticky="nsew")

        # --- input row ---
        input_frame = ttk.LabelFrame(main, text="Add Override", padding=8)
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(input_frame, text="Date (DD/MM):").grid(row=0, column=0, padx=(0, 4))
        self.date_entry = ttk.Entry(input_frame, width=8)
        self.date_entry.grid(row=0, column=1, padx=(0, 12))

        ttk.Label(input_frame, text="Report Type:").grid(row=0, column=2, padx=(0, 4))
        self.type_combo = ttk.Combobox(
            input_frame,
            values=REPORT_TYPE_VALUES,
            state="readonly",
            width=30,
        )
        self.type_combo.grid(row=0, column=3, padx=(0, 12))

        ttk.Button(input_frame, text="Add", command=self._add_override).grid(row=0, column=4)

        # --- table ---
        table_frame = ttk.Frame(main)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        self.tree = ttk.Treeview(table_frame, columns=("date", "type"), show="headings", height=8)
        self.tree.heading("date", text="Date")
        self.tree.heading("type", text="Report Type")
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("type", width=260, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- buttons ---
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=2, column=0, sticky="ew")

        ttk.Button(btn_frame, text="Remove Selected", command=self._remove_selected).pack(side="left")
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

    def _run(self):
        self._save_overrides()
        self.root.destroy()
        pytest.main(["src/scanners/hilan_scanner_test.py", "-s"])

    def _save_overrides(self):
        OVERRIDES_FILE.write_text(json.dumps(self.overrides, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    root = tk.Tk()
    HilanLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
