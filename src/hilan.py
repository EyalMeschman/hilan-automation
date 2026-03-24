import json
import logging
import re
import time
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

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


def login(driver: WebDriver, username: str, password: str):
    driver.get(LOGIN_URL)
    username_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="מספר העובד"]')
    username_input.clear()
    username_input.send_keys(username)
    password_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="סיסמה"]')
    password_input.clear()
    password_input.send_keys(password)
    driver.find_element(By.XPATH, '//button[normalize-space()="כניסה"]').click()
    WebDriverWait(driver, 10).until(EC.url_to_be(HOME_URL))


def switch_to_error_handling_frame(driver: WebDriver, timeout: int = 5000) -> None:
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
            src = iframe.get_attribute("src") or ""
            if "EmployeeErrorHandling" in src:
                driver.switch_to.frame(iframe)
                return
        time.sleep(0.3)
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


def fill_report(
    driver: WebDriver,
    logger: logging.Logger,
    overrides: dict[str, ReportType],
    callbacks: AutomationCallbacks,
    *,
    confirm_before_save: bool = False,
):
    switch_to_error_handling_frame(driver)

    day_text = driver.find_element(By.CSS_SELECTOR, ".ROC").text
    date_str = extract_date(day_text)

    report_type = overrides.get(date_str)
    if not report_type:
        day_letter = extract_day_letter(day_text)
        report_type = DEFAULT_REPORT_TYPE_BY_DAY.get(day_letter)
        if not report_type:
            raise ValueError(f"No report type for day letter '{day_letter}'")
    else:
        logger.info(f"Loaded {len(overrides)} date override(s): {overrides}")

    Select(driver.find_element(By.CSS_SELECTOR, "select")).select_by_visible_text(report_type)

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
                    Select(driver.find_element(By.CSS_SELECTOR, "select")).select_by_visible_text(report_type)
                    logger.info(f"User changed type for {date_str} -> {report_type}")
                    _handle_manual_action_if_needed(date_str, report_type, logger, callbacks)
                    continue
                case ConfirmAction.EXIT:
                    logger.info("User chose to exit automation")
                    raise UserExitError
                case _:
                    raise RuntimeError(f"Unexpected confirm action: {action}")

    driver.find_element(By.CSS_SELECTOR, 'input[value="שמור וסגור"]').click()
    driver.switch_to.default_content()
    driver.get(HOME_URL)


def wait_for_tasks(driver: WebDriver, timeout: int = 10000) -> int:
    try:
        WebDriverWait(driver, timeout / 1000).until(EC.presence_of_element_located((By.CSS_SELECTOR, TASK_BUTTON_SELECTOR)))
    except TimeoutException:
        return 0
    return len(driver.find_elements(By.CSS_SELECTOR, TASK_BUTTON_SELECTOR))
