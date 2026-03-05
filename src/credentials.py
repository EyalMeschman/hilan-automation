import tkinter as tk
from tkinter import messagebox, ttk

from src.config import load_config, save_config
from src.tutorial import show_tutorial_if_needed


class CredentialsDialog:
    """Modal dialog that collects credentials on first run."""

    def __init__(self, root: tk.Tk):
        self.result: dict | None = None

        self.dialog = tk.Toplevel(root)
        self.dialog.title("Hilan - Login")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

        frame = ttk.Frame(self.dialog, padding=20)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="Enter your Hilan credentials", font=("", 13, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 12))

        ttk.Label(frame, text="Employee ID:").grid(row=1, column=0, padx=(0, 8), sticky="e")
        self.username_entry = ttk.Entry(frame, width=24)
        self.username_entry.grid(row=1, column=1, pady=4)
        self.username_entry.focus_set()

        ttk.Label(frame, text="Password:").grid(row=2, column=0, padx=(0, 8), sticky="e")
        self.password_entry = ttk.Entry(frame, width=24, show="*")
        self.password_entry.grid(row=2, column=1, pady=4)

        self.remember_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Remember me", variable=self.remember_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 8))

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(4, 0))
        ttk.Button(btn_frame, text="Continue", command=self._submit).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Exit", command=self._on_close).pack(side="left")

        self.password_entry.bind("<Return>", lambda _: self._submit())

        self.dialog.update_idletasks()
        w = self.dialog.winfo_width()
        h = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() - w) // 2
        y = (self.dialog.winfo_screenheight() - h) // 2
        self.dialog.geometry(f"+{x}+{y}")

        show_tutorial_if_needed(self.dialog, "login")

    def _submit(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Missing credentials", "Please enter both Employee ID and Password.", parent=self.dialog)
            return

        if self.remember_var.get():
            save_config(username, password)

        self.result = {"username": username, "password": password}
        self.dialog.destroy()

    def _on_close(self):
        self.result = None
        self.dialog.destroy()


def ensure_credentials(root: tk.Tk) -> tuple[str, str] | None:
    """Return (username, password) from saved config or by showing the login dialog.

    Returns None if the user closes the dialog without submitting.
    """
    config = load_config()
    username = config.get("username", "")
    password = config.get("password", "")

    if username and password:
        return username, password

    dialog = CredentialsDialog(root)
    root.wait_window(dialog.dialog)

    if dialog.result is None:
        return None

    return dialog.result["username"], dialog.result["password"]
