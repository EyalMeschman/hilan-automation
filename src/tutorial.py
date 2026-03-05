import tkinter as tk
from tkinter import ttk

from src.config import ConfigKey, load_config, update_config

TUTORIALS: dict[ConfigKey, list[dict[str, str]]] = {
    ConfigKey.SHOW_LOGIN_TUTORIAL: [
        {
            "title": "Welcome!",
            "body": (
                "Welcome to Hilan Automation!\n\n"
                "This tool automates your Hilan attendance\n"
                "reports so you don't have to fill them manually.\n\n"
                "Let's get you started by logging in."
            ),
        },
        {
            "title": "Your Credentials",
            "body": (
                "Enter your Hilan Employee ID and password.\n\n"
                "Check 'Remember me' so you won't need to\n"
                "enter them again next time you open the app."
            ),
        },
    ],
    ConfigKey.SHOW_MAIN_TUTORIAL: [
        {
            "title": "Main Dashboard",
            "body": (
                "This is the main dashboard where you configure\n"
                "which dates and report types to automate.\n\n"
                "You can add date overrides, review them in\n"
                "the table, and run the automation when ready."
            ),
        },
        {
            "title": "Adding Date Overrides",
            "body": (
                "Use the 'From' and 'To' date pickers to select\n"
                "a date range, pick a report type from the\n"
                "dropdown, then click 'Add' to queue them.\n\n"
                "Each date in the range will appear in the table\n"
                "with the selected report type."
            ),
        },
        {
            "title": "Running the Automation",
            "body": (
                "When you're ready, click 'Run' to start.\n\n"
                "Enable 'Confirm before saving' if you want to\n"
                "review each report before it's submitted.\n\n"
                "You can also remove entries or log out using\n"
                "the buttons at the bottom."
            ),
        },
    ],
}


def _should_show(key: ConfigKey) -> bool:
    return load_config().get(key, True)


def _set_dont_show(key: ConfigKey):
    update_config(**{key: False})


class TutorialDialog:
    def __init__(self, parent: tk.Toplevel | tk.Tk, key: ConfigKey):
        self.key = key
        self.steps = TUTORIALS[key]
        self.current = 0

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Tutorial")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self._finish)

        frame = ttk.Frame(self.dialog, padding=24)
        frame.grid(sticky="nsew")

        self.title_label = ttk.Label(frame, text="", font=("", 14, "bold"))
        self.title_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.body_label = ttk.Label(frame, text="", font=("", 11), justify="left")
        self.body_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 16))

        self.step_label = ttk.Label(frame, text="", font=("", 9))
        self.step_label.grid(row=2, column=0, columnspan=3, pady=(0, 12))

        separator = ttk.Separator(frame, orient="horizontal")
        separator.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        self.dont_show_var = tk.BooleanVar(value=False)
        self.dont_show_cb = ttk.Checkbutton(frame, text="Don't show this again", variable=self.dont_show_var)
        self.dont_show_cb.grid(row=4, column=0, sticky="w")

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=1, columnspan=2, sticky="e")

        self.back_btn = ttk.Button(btn_frame, text="Back", command=self._back)
        self.back_btn.pack(side="left", padx=(0, 6))

        self.next_btn = ttk.Button(btn_frame, text="Next", command=self._next)
        self.next_btn.pack(side="left")

        self._render_step()

        self.dialog.update_idletasks()
        self._position_beside_parent(parent)

    def _position_beside_parent(self, parent: tk.Toplevel | tk.Tk):
        gap = 20
        parent.update_idletasks()
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        tw = self.dialog.winfo_width()
        th = self.dialog.winfo_height()
        screen_w = self.dialog.winfo_screenwidth()

        x = px + pw + gap
        if x + tw > screen_w:
            x = px - tw - gap

        y = py + (ph - th) // 2

        self.dialog.geometry(f"+{x}+{y}")

    def _render_step(self):
        step = self.steps[self.current]
        self.title_label.config(text=step["title"])
        self.body_label.config(text=step["body"])
        self.step_label.config(text=f"Step {self.current + 1} of {len(self.steps)}")

        self.back_btn.config(state="normal" if self.current > 0 else "disabled")

        is_last = self.current == len(self.steps) - 1
        self.next_btn.config(text="Finish" if is_last else "Next")

        if is_last:
            self.dont_show_cb.grid()
        else:
            self.dont_show_cb.grid_remove()

    def _next(self):
        if self.current < len(self.steps) - 1:
            self.current += 1
            self._render_step()
        else:
            self._finish()

    def _back(self):
        if self.current > 0:
            self.current -= 1
            self._render_step()

    def _finish(self):
        if self.dont_show_var.get():
            _set_dont_show(self.key)
        self.dialog.destroy()


def show_tutorial_if_needed(parent: tk.Toplevel | tk.Tk, key: ConfigKey):
    if key not in TUTORIALS:
        return
    if not _should_show(key):
        return

    dialog = TutorialDialog(parent, key)
    parent.wait_window(dialog.dialog)
