import logging
import traceback

from playwright.async_api import async_playwright

from logger import Logger
from src.scanners.hilan_scanner_test import (
    ReportType,
    fill_report,
    login,
    wait_for_tasks,
)
from src.utils import Utils


class AutomationResult:
    def __init__(self, filled: int = 0, error: str | None = None):
        self.filled = filled
        self.error = error

    @property
    def success(self) -> bool:
        return self.error is None


async def run(overrides: dict[str, ReportType]) -> AutomationResult:
    logger = Logger.create()
    logger.setLevel(logging.DEBUG)

    if overrides:
        logger.info(f"Date overrides: {overrides}")

    filled = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        context = await browser.new_context(
            bypass_csp=True,
            ignore_https_errors=True,
        )
        Utils.cover_footprints(context)

        page = await context.new_page()
        page.on("console", lambda msg: logger.debug(msg.text))

        try:
            await login(page)

            remaining = await wait_for_tasks(page)
            logger.info(f"Found {remaining} pending reports to fill")

            while remaining > 0:
                button = page.locator('button[aria-label*="לטיפול"]').first
                filled += 1
                logger.info(f"[{filled}] Opening report...")
                await button.click()
                await fill_report(page, logger, overrides)
                remaining = await wait_for_tasks(page)

            logger.info(f"Done. Filled {filled} reports, no tasks remaining.")
            return AutomationResult(filled=filled)
        except Exception:
            logger.exception("Automation failed")
            return AutomationResult(filled=filled, error=traceback.format_exc())
        finally:
            await page.close()
            await context.close()
            await browser.close()
