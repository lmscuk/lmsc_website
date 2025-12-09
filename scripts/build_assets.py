#!/usr/bin/env python3
"""Build and minify frontend assets using lightningcss and esbuild.

This script expects Node.js tooling to be available. Run it before deploying
so Flask serves the pre-compressed bundles exposed via ``asset_url``.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
DIST_DIR = STATIC_DIR / "dist"


def _ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        sys.stderr.write(
            f"Required command '{name}' is not available. Install Node.js tooling before running this script.\n"
        )
        sys.exit(1)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> int:
    _ensure_command("npx")

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    css_output = DIST_DIR / "style.min.css"
    js_output = DIST_DIR / "script.min.js"

    css_input = STATIC_DIR / "css" / "style.css"
    js_input = STATIC_DIR / "js" / "script.js"

    commands: list[tuple[str, list[str]]] = [
        (
            "CSS",
            [
                "npx",
                "lightningcss",
                "--minify",
                "--bundle",
                str(css_input),
                "--output",
                str(css_output),
            ],
        ),
        (
            "JS",
            [
                "npx",
                "esbuild",
                str(js_input),
                "--bundle",
                "--minify",
                "--format=esm",
                "--external:https://*",
                f"--outfile={js_output}",
            ],
        ),
    ]

    for label, command in commands:
        print(f"[build-assets] Bundling {label} -> {command[-1] if command else ''}")
        _run(command)

    print("[build-assets] Assets minified successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
