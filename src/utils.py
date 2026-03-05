import os
from pathlib import Path

from playwright.async_api import BrowserContext

FINGERPRINT_SHIM_PATH = Path(__file__).parent / "assets" / "fingerprint_shim.js"

BROWSER_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
]


class Utils:
    @staticmethod
    async def cover_footprints(context: BrowserContext) -> None:
        await context.add_init_script(path=str(FINGERPRINT_SHIM_PATH))

    @staticmethod
    def get_mandatory_env(key: str) -> str:
        value = os.getenv(key)

        if not value:
            raise OSError(f"{key} env var is missing")

        return value
