import asyncio
import json
import logging
import re
from enum import StrEnum
from pathlib import Path
from tkinter import ttk

import ttkbootstrap as ttb
from playwright.async_api import Frame, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.utils import Utils

LOGIN_URL = "https://tipalti.net.hilan.co.il/login"
HOME_URL = "https://tipalti.net.hilan.co.il/Hilannetv2/ng/personal-file/home"
TASK_BUTTON_SELECTOR = 'button[aria-label*="לטיפול"]'
OVERRIDES_FILE = Path(__file__).resolve().parents[2] / "report_overrides.json"


class ReportType(StrEnum):
    PRESENT = "נכח"
    WORK_FROM_HOME = "ע.בית"
    SICK = "ע.חול"
    HALF_VACATION = "חצי חופשה"
    SICK_LEAVE = "מחלה"
    VACATION = "חופשה"
    CHILD_SICK = "מחלת ילד"
    HALF_DAY_SICK = "חצי יום מחלה"
    HALF_DAY_RESERVES = "חצי יום מילואים"
    RESERVES = "מילואים"
    PARENT_SICK = "מחלת הורה"
    SPOUSE_SICK = "מחלת בן זוג"
    WORK_DURING_RESERVES = "עבודה במילואים"
    TRAINING = "השתלמות"
    CONFERENCE = "כנס"
    FUN_DAY = "י.כיף"
    COURSE = "קורס"
    HALF_DAY_CHILD_SICK = "חצי יום מחלת ילד"
    VAL_WORK_ON_ELECTION_DAY = "עבודה ביום בחירות"


REQUIRES_MANUAL_ACTION: set[ReportType] = {
    ReportType.HALF_VACATION,
    ReportType.SICK_LEAVE,
    ReportType.CHILD_SICK,
    ReportType.HALF_DAY_SICK,
    ReportType.HALF_DAY_RESERVES,
    ReportType.RESERVES,
    ReportType.PARENT_SICK,
    ReportType.SPOUSE_SICK,
    ReportType.WORK_DURING_RESERVES,
    ReportType.HALF_DAY_CHILD_SICK,
}


class DayLetter(StrEnum):
    A = "א"
    B = "ב"
    C = "ג"
    D = "ד"
    H = "ה"


REPORT_TYPE_BY_DAY = {
    DayLetter.A: ReportType.WORK_FROM_HOME,
    DayLetter.B: ReportType.PRESENT,
    DayLetter.C: ReportType.PRESENT,
    DayLetter.D: ReportType.WORK_FROM_HOME,
    DayLetter.H: ReportType.PRESENT,
}


async def login(page: Page):
    username = Utils.get_mandatory_env("HILAN_USERNAME")
    password = Utils.get_mandatory_env("HILAN_PASSWORD")

    await page.goto(LOGIN_URL)
    await page.get_by_placeholder("מספר העובד").fill(username)
    await page.get_by_placeholder("סיסמה").fill(password)
    await page.get_by_role("button", name="כניסה", exact=True).click()
    await page.wait_for_url(HOME_URL, timeout=10000)


async def get_error_handling_frame(page: Page, timeout: int = 5000) -> Frame:
    deadline = asyncio.get_event_loop().time() + timeout / 1000
    while asyncio.get_event_loop().time() < deadline:
        for frame in page.frames:
            if "EmployeeErrorHandling" in frame.url:
                return frame
        await asyncio.sleep(0.3)
    raise ValueError("Could not find EmployeeErrorHandling iframe")


def extract_day_letter(day_text: str) -> DayLetter:
    match = re.search(r"יום\s+([אבגדה])", day_text)
    if not match:
        raise ValueError(f"Could not extract day letter from: '{day_text}'")
    return DayLetter(match.group(1))


def extract_date(day_text: str) -> str:
    match = re.search(r"(\d{2}/\d{2})", day_text)
    if not match:
        raise ValueError(f"Could not extract date from: '{day_text}'")
    return match.group(1)


def load_overrides() -> dict[str, ReportType]:
    if not OVERRIDES_FILE.exists():
        return {}
    data = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return {date: ReportType(report_type) for date, report_type in data.items()}


class UserExitError(Exception):
    pass


class ConfirmAction:
    SAVE = "save"
    CHANGE = "change"
    EXIT = "exit"


REPORT_TYPE_VALUES = [member.value for member in ReportType]


def _ask_manual_action(date_str: str, report_type: str):
    """Blocks until the user finishes handling the site popup and clicks Continue."""
    dialog = ttb.Window(themename="darkly", title="Action Required")
    dialog.resizable(False, False)
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)

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
        frame, text="Continue", width=12, bootstyle="success",
        command=lambda: (dialog.quit(), dialog.destroy()),
    ).pack()

    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    dialog.lift()
    dialog.attributes("-topmost", True)

    dialog.mainloop()


def _ask_confirm(date_str: str, report_type: str) -> tuple[str, str | None]:
    """Returns (action, new_type). new_type is set only for CHANGE."""
    result_action = ConfirmAction.EXIT
    result_type: str | None = None

    dialog = ttb.Window(themename="darkly", title="Confirm Report")
    dialog.resizable(False, False)
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)

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
        dialog.quit()
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

    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    dialog.lift()
    dialog.attributes("-topmost", True)

    dialog.mainloop()
    return result_action, result_type


def _handle_manual_action_if_needed(date_str: str, report_type: ReportType, logger: logging.Logger):
    if report_type in REQUIRES_MANUAL_ACTION:
        logger.info(f"Report type '{report_type}' requires manual action, pausing...")
        _ask_manual_action(date_str, report_type)
        logger.info("User completed manual action, continuing...")


async def fill_report(
    page: Page,
    logger: logging.Logger,
    overrides: dict[str, ReportType],
    *,
    confirm_before_save: bool = False,
):
    frame = await get_error_handling_frame(page)

    day_text = await frame.locator(".ROC").first.inner_text()
    date_str = extract_date(day_text)

    report_type = overrides.get(date_str)
    if not report_type:
        day_letter = extract_day_letter(day_text)
        report_type = REPORT_TYPE_BY_DAY.get(day_letter)
        if not report_type:
            raise ValueError(f"No report type for day letter '{day_letter}'")
    else:
        logger.info(f"Loaded {len(overrides)} date override(s): {overrides}")

    await frame.locator("select").first.select_option(label=report_type)

    logger.info(f"{day_text} -> {report_type}")

    _handle_manual_action_if_needed(date_str, report_type, logger)

    if confirm_before_save:
        while True:
            action, new_type = _ask_confirm(date_str, report_type)
            match action:
                case ConfirmAction.SAVE:
                    break
                case ConfirmAction.CHANGE:
                    report_type = ReportType(new_type)
                    await frame.locator("select").first.select_option(label=report_type)
                    logger.info(f"User changed type for {date_str} -> {report_type}")
                    _handle_manual_action_if_needed(date_str, report_type, logger)
                    continue
                case ConfirmAction.EXIT:
                    logger.info("User chose to exit automation")
                    raise UserExitError
                case _:
                    raise RuntimeError(f"Unexpected confirm action: {action}")

    await frame.locator('input[value="שמור וסגור"]').click()
    await page.goto(HOME_URL)


async def wait_for_tasks(page: Page, timeout: int = 10000) -> int:
    try:
        await page.locator(TASK_BUTTON_SELECTOR).first.wait_for(timeout=timeout)
    except PlaywrightTimeoutError:
        return 0
    return await page.locator(TASK_BUTTON_SELECTOR).count()


async def test_hilan(
    page: Page,
    logger: logging.Logger,
):
    await login(page)

    filled = 0
    remaining = await wait_for_tasks(page)
    logger.info(f"Found {remaining} pending reports to fill")
    overrides = load_overrides()

    while remaining > 0:
        button = page.locator(TASK_BUTTON_SELECTOR).first
        filled += 1
        logger.info(f"[{filled}] Opening report...")
        await button.click()
        await fill_report(page, logger, overrides)
        remaining = await wait_for_tasks(page)

    logger.info(f"Done. Filled {filled} reports, no tasks remaining.")
