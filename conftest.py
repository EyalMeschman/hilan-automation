import logging

import pytest
from dotenv import load_dotenv
from playwright.async_api import Browser, async_playwright

from logger import Logger
from src.utils import Utils

load_dotenv(".env.defaults")
load_dotenv(".env", override=True)


@pytest.fixture(name="logger", scope="session")
def fixture_logger() -> logging.Logger:
    return Logger.create()


@pytest.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser, logger: logging.Logger):
    context = await browser.new_context(
        bypass_csp=True,
        ignore_https_errors=True,
    )
    Utils.cover_footprints(context)

    page = await context.new_page()
    page.on("console", lambda msg: logger.debug(msg.text))

    yield page

    await page.close()
    await context.close()


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "manual: mark test as manual login")
