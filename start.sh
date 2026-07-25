#!/usr/bin/env bash
# Sets up (if needed) and launches ASCII Video.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c "import customtkinter, cv2, numpy, PIL, tkinterdnd2, platformdirs" >/dev/null 2>&1; then
    echo "Installing dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade pip -q
    "$VENV_DIR/bin/pip" install -q -r requirements.txt
fi

if ! "$VENV_DIR/bin/python" -c "import tkinter" >/dev/null 2>&1; then
    echo "Error: this Python has no tkinter support." >&2
    echo "Install your distro's tkinter package (e.g. 'sudo dnf install python3-tkinter'" >&2
    echo "or 'sudo apt install python3-tk'), then run this script again." >&2
    exit 1
fi

exec "$VENV_DIR/bin/python" -m ascii_video "$@"
