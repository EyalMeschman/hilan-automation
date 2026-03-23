import logging
import tkinter as tk
from dataclasses import dataclass

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from logger import Logger
from src.hilan import (
    TASK_BUTTON_SELECTOR,
    ReportType,
    UserExitError,
    fill_report,
    login,
    wait_for_tasks,
)
from src.ui.dialogs import TkCallbacks
from src.utils import BROWSER_LAUNCH_ARGS


@dataclass(slots=True)
class AutomationResult:
    filled: int = 0
    error: str | None = None
    user_exit: bool = False

    @property
    def success(self) -> bool:
        return self.error is None


async def run(
    root: tk.Tk, overrides: dict[str, ReportType], *, username: str, password: str, confirm_before_save: bool = False
) -> AutomationResult:
    logger = Logger.create()
    logger.setLevel(logging.DEBUG)
    callbacks = TkCallbacks(root)

    if overrides:
        logger.info(f"Date overrides: {overrides}")

    filled = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            args=BROWSER_LAUNCH_ARGS,
        )
        context = await browser.new_context(
            bypass_csp=True,
            ignore_https_errors=True,
        )
        page = await context.new_page()
        page.on("console", lambda msg: logger.debug(msg.text))

        try:
            await login(page, username, password)
        except PlaywrightTimeout:
            logger.exception("Login timed out")
            return AutomationResult(error="Login failed. Please check your Employee ID and Password.")
        except Exception:
            logger.exception("Login failed")
            return AutomationResult(error="Login failed due to an unexpected error. Please try again.")

        try:
            remaining = await wait_for_tasks(page)
            logger.info(f"Found {remaining} pending reports to fill")

            while remaining > 0:
                button = page.locator(TASK_BUTTON_SELECTOR).first
                filled += 1
                logger.info(f"[{filled}] Opening report...")
                await button.click()
                await fill_report(page, logger, overrides, callbacks, confirm_before_save=confirm_before_save)
                remaining = await wait_for_tasks(page)

            logger.info(f"Done. Filled {filled} reports, no tasks remaining.")
            return AutomationResult(filled=filled)
        except UserExitError:
            logger.info(f"User exited early after {filled} report(s).")
            return AutomationResult(filled=filled, user_exit=True)
        except Exception as exc:
            logger.exception("Automation failed")
            return AutomationResult(filled=filled, error=f"An error occurred while filling reports: {exc}")
        finally:
            await page.close()
            await context.close()
            await browser.close()
