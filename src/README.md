# Developer Guide

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

2. Install dependencies:

```bash
uv sync
```

3. Install Playwright browsers:

```bash
uv run playwright install
```

## Project structure

```
run.py                  Entry point -- Tkinter GUI launcher
logger.py               Logging setup
hilan.spec              PyInstaller build spec
build.sh                Build script (produces .app bundle)
src/
├── automation.py       Playwright lifecycle: launch, login, loop reports
├── hilan.py            Hilan URLs, selectors, ReportType enum, fill logic
├── credentials.py      Login dialog, keyring read/write
├── config.py           Config file (~/.hilan-automation/config.json)
├── tutorial.py         First-run tutorial dialogs
├── utils.py            Browser args, fingerprint shim
├── assets/
│   └── fingerprint_shim.js
└── ui/
    ├── dialogs.py      Manual action + confirm-before-save modals
    └── tk_utils.py     Tkinter helpers
```

## Running locally

```bash
uv run python run.py
```

## Linting

```bash
uv run ruff format .
uv run ruff check --fix .
```

Linting runs automatically on pull requests to `main` via the `linter.yml` workflow.

## Building

The build produces a macOS `.app` bundle (arm64 only):

```bash
./build.sh
```

Output: `dist/Hilan Automation.app`

Requires Homebrew `tcl-tk`:

```bash
brew install tcl-tk
```

## Releasing

Releases are created manually through **GitHub Actions**:

1. Go to **Actions** > **Release** > **Run workflow**
2. Choose the version bump type:
   - **patch** -- `v1.0.0` -> `v1.0.1` (bug fixes, small changes)
   - **minor** -- `v1.0.0` -> `v1.1.0` (new features)
   - **major** -- `v1.0.0` -> `v2.0.0` (breaking changes)
3. Optionally check **Delete all previous releases** to free up storage
4. Click **Run workflow**

The workflow builds the app on a macOS runner, creates a git tag, and publishes a GitHub Release with the zip attached.

Users download the latest release from:
`https://github.com/EyalMeschman/hilan-automation/releases/latest`

### GitHub storage limits

The **GitHub Free plan** provides **500 MB** of storage for release assets. Each release zip is approximately **139 MB**, so you can keep **at most 3 releases** before hitting the limit.

To manage this:
- Use the **Delete all previous releases** checkbox when creating a new release
- Or manually delete old releases from the [Releases page](https://github.com/EyalMeschman/hilan-automation/releases)

If you run out of storage, the release workflow will fail when trying to upload the zip.
