#!/usr/bin/env python3
"""Render the main screen to docs/screenshot.svg.

Usage: uv run python scripts/capture_screenshot.py
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.text import Text

from esspresso import (
    ACTIONS,
    EXIT_CHOICE,
    GREY,
    NEON_CYAN,
    NEON_GREEN,
    NEON_MAGENTA,
    Settings,
    render_banner,
    render_status,
)

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshot.svg"


def main() -> None:
    console = Console(record=True, width=84, force_terminal=True)
    console.print(render_banner())
    console.print(render_status(Settings()))
    console.print()

    prompt = Text()
    prompt.append("? ", style=f"bold {NEON_MAGENTA}")
    prompt.append("Main menu:", style=f"bold {NEON_GREEN}")
    prompt.append("  (Use arrow keys)", style=f"{GREY} italic")
    console.print(prompt)

    choices = [*ACTIONS.keys(), EXIT_CHOICE]
    for i, c in enumerate(choices):
        line = Text()
        if i == 0:
            line.append("» ", style=f"bold {NEON_MAGENTA}")
            line.append(c, style=f"bold {NEON_CYAN}")
        else:
            line.append("  ")
            line.append(c)
        console.print(line)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    console.save_svg(str(OUT), title="esspresso")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
