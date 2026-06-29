#!/usr/bin/env python3
"""Launch the Quant Agent Streamlit dashboard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "streamlit_app.py"


def main() -> None:
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    raise SystemExit(subprocess.call(cmd, cwd=str(ROOT)))


if __name__ == "__main__":
    main()
