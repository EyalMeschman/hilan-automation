import asyncio
import logging
import re
from enum import StrEnum

from playwright.async_api import Frame, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.utils import Utils

LOGIN_URL = "https://tipalti.net.hilan.co.il/login"
HOME_URL = "https://tipalti.net.hilan.co.il/Hilannetv2/ng/personal-file/home"
TASK_BUTTON_SELECTOR = 'button[aria-label*="לטיפול"]'


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
    SPOUSE_SICK = "מחלת בן זוג"
    SICK_DURING_RESERVES = "מחלת במילואים"
    WORK = "עבודה"
    TRAINING = "השתלמות"
    CONFERENCE = "כנס"
    FUN_DAY = "י.כיף"
    COURSE = "קורס"
    HALF_DAY_CHILD_SICK = "חצי יום מחלת ילד"
    WORK_ON_ELECTION_DAY = "עבודה ביום בחירות"


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


async def fill_report(page: Page, logger: logging.Logger):
    frame = await get_error_handling_frame(page)

    day_text = await frame.locator(".ROC").first.inner_text()
    day_letter = extract_day_letter(day_text)
    report_type = REPORT_TYPE_BY_DAY.get(day_letter)
    if not report_type:
        raise ValueError(f"No report type for day letter '{day_letter}'")

    await frame.locator("select").first.select_option(label=report_type)

    logger.info(f"{day_text} -> {report_type}")
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

    while remaining > 0:
        button = page.locator(TASK_BUTTON_SELECTOR).first
        filled += 1
        logger.info(f"[{filled}] Opening report...")
        await button.click()
        await fill_report(page, logger)
        remaining = await wait_for_tasks(page)

    logger.info(f"Done. Filled {filled} reports, no tasks remaining.")
