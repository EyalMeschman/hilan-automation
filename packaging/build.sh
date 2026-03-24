#!/bin/bash
set -e
cd "$(dirname "$0")/.."
uv sync --extra build
uv run pyinstaller packaging/hilan.spec --noconfirm
echo ""
echo "Build complete: dist/Hilan Automation.app"
