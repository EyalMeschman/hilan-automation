#!/bin/bash
set -e
uv sync --extra build
uv run pyinstaller hilan.spec --noconfirm
echo ""
echo "Build complete: dist/Hilan Automation.app"
