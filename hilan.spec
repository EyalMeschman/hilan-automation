import importlib
from pathlib import Path

playwright_driver = Path(importlib.import_module("playwright").__file__).parent / "driver"

import subprocess

tcl_tk_prefix = Path(subprocess.check_output(["brew", "--prefix", "tcl-tk"]).decode().strip()) / "lib"

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[
        (str(playwright_driver), "playwright/driver"),
        ("src", "src"),
        ("logger.py", "."),
        (str(tcl_tk_prefix / "tcl9.0"), "lib/tcl9.0"),
        (str(tcl_tk_prefix / "tk9.0"), "lib/tk9.0"),
    ],
    hiddenimports=[
        "playwright",
        "playwright._impl",
        "playwright._impl._driver",
        "playwright.async_api",
        "greenlet",
        "pyee",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pytest_asyncio", "pytest_playwright", "ruff"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Hilan Automation",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch="arm64",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Hilan Automation",
)

app = BUNDLE(
    coll,
    name="Hilan Automation.app",
    bundle_identifier="com.hilan.automation",
    icon="icon.icns",
)
