# Playwright to Selenium Migration

## Goal

Replace Playwright with Selenium to reduce the packaged app size. The Playwright driver payload (~100+ MB) bundled in PyInstaller is the primary size culprit. Selenium uses the system ChromeDriver (auto-managed by built-in selenium-manager) and adds negligible packaging overhead.

## Decisions

- **Sync over async:** Selenium is synchronous. The entire automation layer drops `async/await`. The GUI already blocks during `asyncio.run()`, so switching to a direct synchronous call is simpler with no UX regression.
- **Built-in selenium-manager:** No extra dependency for ChromeDriver management. Selenium 4.25+ auto-downloads the correct ChromeDriver for the user's installed Chrome.
- **Drop console log forwarding:** `page.on("console", ...)` was debug-only logging. Selenium has no native equivalent. Dropped without impact.
- **Drop fingerprint shim:** Already removed by the user. `src/assets/fingerprint_shim.js` and the `add_init_script` call are gone.
- **CSP bypass:** Playwright's `bypass_csp=True` has no Selenium equivalent, but Selenium doesn't enforce CSP, so no action needed.

## Scope

### Files modified

| File | Change |
|------|--------|
| `src/automation.py` | Replace Playwright browser lifecycle with Selenium WebDriver. Async to sync. |
| `src/hilan.py` | Replace all Playwright page/frame/locator APIs with Selenium equivalents. Async to sync. |
| `src/utils.py` | No functional change — Chrome launch args list stays the same. |
| `run.py` | Remove `asyncio.run()` wrapper, call `run_automation()` directly. Remove `import asyncio`. |
| `pyproject.toml` | Replace `playwright>=1.40.0` with `selenium>=4.25.0`. Update description. |
| `hilan.spec` | Remove Playwright driver bundling and hidden imports. Add Selenium hidden import if needed. |
| `src/README.md` | Remove "Install Playwright browsers" setup step. Update project structure description. |

### Files deleted

| File | Reason |
|------|--------|
| `src/assets/fingerprint_shim.js` | Fingerprint shim no longer used (if still present). |
| `src/assets/` | Directory removed if empty after shim deletion. |

### Files unchanged

`README.md`, `logger.py`, `build.sh`, `src/credentials.py`, `src/config.py`, `src/tutorial.py`, `src/ui/dialogs.py`, `src/ui/tk_utils.py`, `src/ui/__init__.py`, `.github/workflows/release.yml`, `.github/workflows/linter.yml`, icons, `.vscode/`.

## API Migration Map

### automation.py

| Playwright | Selenium |
|-----------|----------|
| `async with async_playwright() as p` | `driver = webdriver.Chrome(options=options)` |
| `p.chromium.launch(channel="chrome", headless=False, args=BROWSER_LAUNCH_ARGS)` | `ChromeOptions` with args from `BROWSER_LAUNCH_ARGS` + `add_experimental_option("excludeSwitches", ["enable-automation"])` |
| `browser.new_context(bypass_csp=True, ignore_https_errors=True)` | `options.add_argument("--ignore-certificate-errors")` |
| `context.new_page()` | Driver is the page |
| `page.on("console", lambda msg: logger.debug(msg.text))` | Dropped (debug-only) |
| `page.locator(TASK_BUTTON_SELECTOR).first.click()` | `driver.find_element(By.CSS_SELECTOR, TASK_BUTTON_SELECTOR).click()` |
| `PlaywrightTimeout` catch | `TimeoutException` from `selenium.common.exceptions` |
| `page.close(); context.close(); browser.close()` | `driver.quit()` |

### hilan.py

| Playwright | Selenium |
|-----------|----------|
| `page.goto(url)` | `driver.get(url)` |
| `page.get_by_placeholder("...").fill(value)` | `el = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="..."]'); el.clear(); el.send_keys(value)` |
| `page.get_by_role("button", name="...", exact=True).click()` | `driver.find_element(By.XPATH, '//button[text()="..."]').click()` |
| `page.wait_for_url(url, timeout=10000)` | `WebDriverWait(driver, 10).until(EC.url_to_be(url))` |
| `page.frames` iteration for iframe | `WebDriverWait` to find iframe by CSS, then `driver.switch_to.frame(element)` |
| `frame.locator(".ROC").first.inner_text()` | `driver.find_element(By.CSS_SELECTOR, ".ROC").text` (after frame switch) |
| `frame.locator("select").first.select_option(label=...)` | `Select(driver.find_element(By.CSS_SELECTOR, "select")).select_by_visible_text(...)` |
| `frame.locator('input[value="..."]').click()` | `driver.find_element(By.CSS_SELECTOR, 'input[value="..."]').click()` |
| `page.locator(sel).first.wait_for(timeout=...)` | `WebDriverWait(driver, timeout).until(EC.presence_of_element_located(...))` |
| `page.locator(sel).count()` | `len(driver.find_elements(...))` |
| `PlaywrightTimeoutError` | `TimeoutException` |

### run.py

| Before | After |
|--------|-------|
| `import asyncio` | Removed |
| `asyncio.run(run_automation(...))` | `run_automation(...)` |

### hilan.spec

| Before | After |
|--------|-------|
| `playwright_driver` path resolution (lines 3-4) | Removed |
| `datas` includes `(str(playwright_driver), "playwright/driver")` | Removed |
| `hiddenimports` includes `playwright`, `playwright._impl`, etc., `greenlet`, `pyee` | Replaced with `selenium` (if needed) |

### pyproject.toml

| Before | After |
|--------|-------|
| `description = "...using Playwright"` | `description = "...using Selenium"` |
| `"playwright>=1.40.0"` | `"selenium>=4.25.0"` |

### src/README.md

| Before | After |
|--------|-------|
| Setup step: `uv run playwright install` | Removed |
| `automation.py` described as "Playwright lifecycle" | Updated to "Selenium lifecycle" or "Browser lifecycle" |

## Iframe Handling Detail

Playwright allows working with frames as independent objects (`frame.locator(...)`). Selenium requires an explicit switch:

1. Find iframe element: `WebDriverWait` until an iframe with `src` containing `"EmployeeErrorHandling"` is present
2. Switch: `driver.switch_to.frame(iframe_element)`
3. Interact with elements inside the frame using normal `find_element` calls
4. Switch back: `driver.switch_to.default_content()` before navigating away

The `get_error_handling_frame()` function changes from returning a `Frame` object to switching the driver context in-place and returning nothing (or returning the driver for chaining). After `fill_report` completes its frame work, it calls `driver.switch_to.default_content()` before `driver.get(HOME_URL)`.

## Type Annotation Changes

| Before | After |
|--------|-------|
| `from playwright.async_api import Page, Frame` | `from selenium.webdriver.remote.webdriver import WebDriver` |
| `page: Page` parameter | `driver: WebDriver` parameter |
| `frame: Frame` return type | No return — driver context switch |
| `async def` | `def` |

## Packaging Impact

- **Removed:** `playwright/driver` (~100+ MB) from bundled data
- **Removed:** `greenlet`, `pyee` hidden imports (Playwright async dependencies)
- **Added:** `selenium` package (lightweight, ~1-2 MB)
- **Expected size reduction:** Significant — from ~139 MB zip to an estimated ~30-40 MB (needs measurement)

## Behavioral Parity

Everything stays functionally identical:
- Login flow (navigate, fill credentials, click, wait for redirect)
- Task button discovery and counting
- Report filling loop (iframe switch, read day, select type, optional manual/confirm dialogs, save)
- Error handling (timeout on login, timeout on tasks, user exit)
- GUI interaction (Tk callbacks for manual action and confirm dialogs)

The only behavioral difference: browser console messages are no longer forwarded to the Python logger (debug-level only, no user impact).
