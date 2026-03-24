import logging
import tkinter as tk
from dataclasses import dataclass

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By

from src.hilan import (
    TASK_BUTTON_SELECTOR,
    ReportType,
    UserExitError,
    fill_report,
    login,
    wait_for_tasks,
)
from src.logger import Logger
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


def run(
    root: tk.Tk, overrides: dict[str, ReportType], *, username: str, password: str, confirm_before_save: bool = False
) -> AutomationResult:
    logger = Logger.create()
    logger.setLevel(logging.DEBUG)
    callbacks = TkCallbacks(root)

    if overrides:
        logger.info(f"Date overrides: {overrides}")

    filled = 0

    options = ChromeOptions()
    for arg in BROWSER_LAUNCH_ARGS:
        options.add_argument(arg)
    options.add_argument("--ignore-certificate-errors")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=options)

    try:
        login(driver, username, password)
    except TimeoutException:
        logger.exception("Login timed out")
        driver.quit()
        return AutomationResult(error="Login failed. Please check your Employee ID and Password.")
    except Exception:
        logger.exception("Login failed")
        driver.quit()
        return AutomationResult(error="Login failed due to an unexpected error. Please try again.")

    try:
        remaining = wait_for_tasks(driver)
        logger.info(f"Found {remaining} pending reports to fill")

        while remaining > 0:
            driver.find_element(By.CSS_SELECTOR, TASK_BUTTON_SELECTOR).click()
            filled += 1
            logger.info(f"[{filled}] Opening report...")
            fill_report(driver, logger, overrides, callbacks, confirm_before_save=confirm_before_save)
            remaining = wait_for_tasks(driver)

        logger.info(f"Done. Filled {filled} reports, no tasks remaining.")
        return AutomationResult(filled=filled)
    except UserExitError:
        logger.info(f"User exited early after {filled} report(s).")
        return AutomationResult(filled=filled, user_exit=True)
    except Exception as exc:
        logger.exception("Automation failed")
        return AutomationResult(filled=filled, error=f"An error occurred while filling reports: {exc}")
    finally:
        driver.quit()
