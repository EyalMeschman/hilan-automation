import subprocess
from pathlib import Path

ROOT = Path(SPECPATH).parent
tcl_tk_prefix = Path(subprocess.check_output(["brew", "--prefix", "tcl-tk"]).decode().strip()) / "lib"

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "src"), "src"),
        (str(tcl_tk_prefix / "tcl9.0"), "lib/tcl9.0"),
        (str(tcl_tk_prefix / "tk9.0"), "lib/tk9.0"),
    ],
    hiddenimports=[
        "selenium",
        "selenium.webdriver",
        "selenium.webdriver.chrome",
        "selenium.webdriver.chrome.webdriver",
        "selenium.webdriver.chrome.options",
        "selenium.webdriver.chrome.service",
        "selenium.webdriver.common",
        "selenium.webdriver.common.by",
        "selenium.webdriver.common.selenium_manager",
        "selenium.webdriver.remote",
        "selenium.webdriver.remote.webdriver",
        "selenium.webdriver.remote.errorhandler",
        "selenium.webdriver.support",
        "selenium.webdriver.support.wait",
        "selenium.webdriver.support.expected_conditions",
        "selenium.webdriver.support.select",
        "selenium.common",
        "selenium.common.exceptions",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff"],
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
    icon=str(ROOT / "assets" / "icon.icns"),
    info_plist={
        "NSHighResolutionCapable": True,
    },
)
