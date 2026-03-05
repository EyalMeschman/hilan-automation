from pathlib import Path

from playwright.async_api import BrowserContext

FINGERPRINT_SHIM_PATH = Path(__file__).parent / "assets" / "fingerprint_shim.js"

BROWSER_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
]


async def cover_footprints(context: BrowserContext) -> None:
    await context.add_init_script(path=str(FINGERPRINT_SHIM_PATH))
