import asyncio
import json
import logging
import re
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from playwright.async_api import Frame, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.utils import Utils

LOGIN_URL = "https://tipalti.net.hilan.co.il/login"
HOME_URL = "https://tipalti.net.hilan.co.il/Hilannetv2/ng/personal-file/home"
TASK_BUTTON_SELECTOR = 'button[aria-label*="לטיפול"]'
OVERRIDES_FILE = Path(__file__).resolve().parents[1] / "report_overrides.json"


class UserExitError(Exception):
    pass


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


DEFAULT_REPORT_TYPE_BY_DAY = {
    DayLetter.A: ReportType.WORK_FROM_HOME,
    DayLetter.B: ReportType.PRESENT,
    DayLetter.C: ReportType.PRESENT,
    DayLetter.D: ReportType.WORK_FROM_HOME,
    DayLetter.H: ReportType.PRESENT,
}


class ConfirmAction(StrEnum):
    SAVE = "save"
    CHANGE = "change"
    EXIT = "exit"


class AutomationCallbacks(Protocol):
    def on_manual_action(self, date_str: str, report_type: str) -> None: ...
    def on_confirm(self, date_str: str, report_type: str) -> tuple[ConfirmAction, str | None]: ...


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


def _handle_manual_action_if_needed(
    date_str: str,
    report_type: ReportType,
    logger: logging.Logger,
    callbacks: AutomationCallbacks,
):
    if report_type in REQUIRES_MANUAL_ACTION:
        logger.info(f"Report type '{report_type}' requires manual action, pausing...")
        callbacks.on_manual_action(date_str, report_type)
        logger.info("User completed manual action, continuing...")


async def fill_report(
    page: Page,
    logger: logging.Logger,
    overrides: dict[str, ReportType],
    callbacks: AutomationCallbacks,
    *,
    confirm_before_save: bool = False,
):
    frame = await get_error_handling_frame(page)

    day_text = await frame.locator(".ROC").first.inner_text()
    date_str = extract_date(day_text)

    report_type = overrides.get(date_str)
    if not report_type:
        day_letter = extract_day_letter(day_text)
        report_type = DEFAULT_REPORT_TYPE_BY_DAY.get(day_letter)
        if not report_type:
            raise ValueError(f"No report type for day letter '{day_letter}'")
    else:
        logger.info(f"Loaded {len(overrides)} date override(s): {overrides}")

    await frame.locator("select").first.select_option(label=report_type)

    logger.info(f"{day_text} -> {report_type}")

    _handle_manual_action_if_needed(date_str, report_type, logger, callbacks)

    if confirm_before_save:
        while True:
            action, new_type = callbacks.on_confirm(date_str, report_type)
            match action:
                case ConfirmAction.SAVE:
                    break
                case ConfirmAction.CHANGE:
                    report_type = ReportType(new_type)
                    await frame.locator("select").first.select_option(label=report_type)
                    logger.info(f"User changed type for {date_str} -> {report_type}")
                    _handle_manual_action_if_needed(date_str, report_type, logger, callbacks)
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
