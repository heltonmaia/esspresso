"""esspresso — interactive terminal wrapper around esptool for ESP32 boards."""

from __future__ import annotations

import glob
import os
import subprocess
import sys
from dataclasses import dataclass

import questionary
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()


# ───────────────────────────── palette / style ─────────────────────────────

NEON_GREEN   = "#00ff9c"
MATRIX_GREEN = "#00ff41"
NEON_CYAN    = "#00ffff"
NEON_MAGENTA = "#ff00ff"
NEON_YELLOW  = "#ffd700"
DIM_GREEN    = "#008f11"
GREY         = "#6272a4"

QSTYLE = questionary.Style([
    ("qmark",       f"fg:{NEON_MAGENTA} bold"),
    ("question",    f"fg:{NEON_GREEN} bold"),
    ("answer",      f"fg:{NEON_CYAN} bold"),
    ("pointer",     f"fg:{NEON_MAGENTA} bold"),
    ("highlighted", f"fg:{NEON_CYAN} bold"),
    ("selected",    f"fg:{NEON_GREEN} bold"),
    ("separator",   f"fg:{GREY}"),
    ("instruction", f"fg:{GREY} italic"),
    ("text",        ""),
    ("disabled",    f"fg:{GREY} italic"),
])

BANNER_LINES = [
    "███████╗███████╗███████╗██████╗ ██████╗ ███████╗███████╗███████╗ ██████╗ ",
    "██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝██╔═══██╗",
    "█████╗  ███████╗███████╗██████╔╝██████╔╝█████╗  ███████╗███████╗██║   ██║",
    "██╔══╝  ╚════██║╚════██║██╔═══╝ ██╔══██╗██╔══╝  ╚════██║╚════██║██║   ██║",
    "███████╗███████║███████║██║     ██║  ██║███████╗███████║███████║╚██████╔╝",
    "╚══════╝╚══════╝╚══════╝╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝ ╚═════╝ ",
]
BANNER_GRADIENT = [MATRIX_GREEN, MATRIX_GREEN, NEON_GREEN, NEON_GREEN, NEON_CYAN, NEON_CYAN]


@dataclass
class Settings:
    baudrate: int = 460800
    start_address: str = "0x1000"


# ───────────────────────────── rendering helpers ─────────────────────────────

def render_banner() -> Panel:
    body = Text()
    for line, color in zip(BANNER_LINES, BANNER_GRADIENT):
        body.append(line + "\n", style=f"bold {color}")
    tagline = Text(
        "ESP32 flasher  ·  esptool wrapper  ·  v0.1.0",
        style=f"bold {NEON_MAGENTA}",
    )
    return Panel(
        Group(Align.center(body), Align.center(tagline)),
        border_style=MATRIX_GREEN,
        padding=(1, 2),
    )


def render_status(settings: Settings) -> Text:
    t = Text()
    t.append("▸ ", style=f"bold {NEON_MAGENTA}")
    t.append("BAUD ", style=GREY)
    t.append(str(settings.baudrate), style=f"bold {NEON_YELLOW}")
    t.append("   ", style=GREY)
    t.append("ADDR ", style=GREY)
    t.append(settings.start_address, style=f"bold {NEON_YELLOW}")
    t.append("   ", style=GREY)
    t.append("PWD ", style=GREY)
    t.append(os.path.basename(os.getcwd()) or "/", style=f"bold {NEON_CYAN}")
    return t


def show_success(title: str, body: str, stdout: str = "") -> None:
    console.print(Panel(
        Text(body, style=f"bold {NEON_GREEN}"),
        border_style=NEON_GREEN,
        title=f"[bold {MATRIX_GREEN}][ + ] {title}[/]",
        title_align="left",
        padding=(0, 1),
    ))
    if stdout.strip():
        console.print(Text(stdout.rstrip(), style=GREY))


def show_error(title: str, body: str, hint: str | None = None) -> None:
    lines: list[Text] = [Text(body, style="bold red")]
    if hint:
        lines.append(Text(""))
        lines.append(Text(f"hint ▸ {hint}", style=f"bold {NEON_YELLOW}"))
    console.print(Panel(
        Group(*lines),
        border_style="red",
        title=f"[bold red][ ! ] {title}[/]",
        title_align="left",
        padding=(0, 1),
    ))


def show_warning(title: str, body: str) -> None:
    console.print(Panel(
        Text(body, style=NEON_YELLOW),
        border_style=NEON_YELLOW,
        title=f"[bold {NEON_YELLOW}][ ~ ] {title}[/]",
        title_align="left",
        padding=(0, 1),
    ))


# ───────────────────────────── discovery ─────────────────────────────

def list_serial_ports() -> list[str]:
    ports: list[str] = []
    for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*"):
        ports.extend(glob.glob(pattern))
    return sorted(ports)


# ───────────────────────────── esptool wrapper ─────────────────────────────

def run_esptool(args: list[str]) -> tuple[int, str, str]:
    cmd = ["esptool", *args]
    console.print(Text(f"$ {' '.join(cmd)}", style=f"{GREY} italic"))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, "", "esptool not found in PATH. Install it with: pip install esptool"
    return proc.returncode, proc.stdout, proc.stderr


def friendly_error_hint(output: str) -> str | None:
    lo = output.lower()
    if "failed to connect" in lo or "no serial data received" in lo:
        return "Hold the BOOT button on the board and retry. Some boards also need a brief EN/RST press."
    if "permission denied" in lo:
        return "Your user probably can't access the serial port. Try: sudo usermod -aG dialout $USER (then log out and back in)."
    if "device or resource busy" in lo or "could not open port" in lo:
        return "Another process is using the port (serial monitor, IDE, another flash). Close it and retry."
    if "esptool not found" in lo:
        return "Install esptool: pip install esptool"
    return None


def show_esptool_result(returncode: int, stdout: str, stderr: str, success_title: str, success_body: str) -> None:
    if returncode == 0:
        show_success(success_title, success_body, stdout)
        return
    body = stderr.strip() or stdout.strip() or "Unknown error"
    hint = friendly_error_hint(stderr + stdout)
    show_error("esptool failed", body, hint)


# ───────────────────────────── interactive pickers ─────────────────────────────

def pick_port() -> str | None:
    ports = list_serial_ports()
    if not ports:
        show_warning("no ports", "No serial devices on /dev/ttyUSB* or /dev/ttyACM*.")
        return None
    return questionary.select("Select a port:", choices=ports, style=QSTYLE).ask()


def _browse_choices(current: str) -> list:
    try:
        entries = sorted(os.listdir(current))
    except PermissionError:
        entries = []
    dirs = [e for e in entries if os.path.isdir(os.path.join(current, e)) and not e.startswith(".")]
    bins = [e for e in entries if e.lower().endswith(".bin") and os.path.isfile(os.path.join(current, e))]

    choices: list = []
    if current != "/":
        choices.append(questionary.Choice(
            title=[(f"fg:{GREY}", "  [..]  "), (f"fg:{NEON_CYAN} bold", "parent directory")],
            value=("up", None),
        ))
    for d in dirs:
        choices.append(questionary.Choice(
            title=[(f"fg:{GREY}", "  [d]   "), (f"fg:{NEON_CYAN} bold", f"{d}/")],
            value=("dir", d),
        ))
    if (dirs or current != "/") and bins:
        choices.append(questionary.Separator("  ───"))
    for b in bins:
        choices.append(questionary.Choice(
            title=[(f"fg:{GREY}", "  [b]   "), (f"fg:{NEON_GREEN} bold", b)],
            value=("file", b),
        ))
    if not dirs and not bins:
        choices.append(questionary.Separator("  (no subdirs or .bin files here)"))
    choices.append(questionary.Separator("  ───"))
    choices.append(questionary.Choice(
        title=[(f"fg:{GREY}", "  [+]   "), (f"fg:{NEON_MAGENTA}", "type a custom path…")],
        value=("custom", None),
    ))
    choices.append(questionary.Choice(
        title=[(f"fg:{GREY}", "  [!]   "), (f"fg:{GREY} italic", "cancel")],
        value=("cancel", None),
    ))
    return choices


def pick_firmware(start: str = ".") -> str | None:
    """Interactive .bin picker with shell-like directory navigation."""
    current = os.path.abspath(start)
    while True:
        result = questionary.select(
            f"Firmware browser  ▸  {current}",
            choices=_browse_choices(current),
            style=QSTYLE,
        ).ask()
        if result is None:
            return None
        action, payload = result
        if action == "cancel":
            return None
        if action == "up":
            current = os.path.dirname(current) or "/"
            continue
        if action == "dir":
            current = os.path.join(current, payload)
            continue
        if action == "file":
            return os.path.join(current, payload)
        if action == "custom":
            path = questionary.path("Path to .bin file:", style=QSTYLE).ask()
            if not path:
                continue
            path = os.path.expanduser(os.path.expandvars(path))
            if not os.path.isfile(path):
                show_error("file not found", f"No such file: {path}")
                continue
            return path


# ───────────────────────────── actions ─────────────────────────────

def action_detect(_: Settings) -> None:
    ports = list_serial_ports()
    if not ports:
        show_warning("no devices", "No boards detected on /dev/ttyUSB* or /dev/ttyACM*.")
        return
    table = Table(
        show_header=True,
        header_style=f"bold {NEON_CYAN}",
        border_style=DIM_GREEN,
        title=f"[bold {NEON_GREEN}]{len(ports)} device(s) online[/]",
        title_justify="left",
        expand=False,
    )
    table.add_column("#", style=GREY, width=4, justify="right")
    table.add_column("device", style=f"bold {NEON_GREEN}")
    table.add_column("bus", style=NEON_CYAN)
    for idx, port in enumerate(ports, 1):
        kind = "USB" if "ttyUSB" in port else "ACM"
        table.add_row(f"{idx:02d}", port, kind)
    console.print(table)


def action_erase(settings: Settings) -> None:
    port = pick_port()
    if not port:
        return
    if not questionary.confirm(f"Erase flash on {port}?", default=False, style=QSTYLE).ask():
        return
    with console.status(Text("erasing flash…", style=f"bold {NEON_CYAN}"), spinner="dots"):
        rc, out, err = run_esptool(["--port", port, "--baud", str(settings.baudrate), "erase_flash"])
    show_esptool_result(rc, out, err, "flash erased", f"Wiped flash on {port}.")


def action_write(settings: Settings) -> None:
    port = pick_port()
    if not port:
        return
    firmware = pick_firmware()
    if not firmware:
        return
    address = questionary.text(
        "Flash address:", default=settings.start_address, style=QSTYLE,
    ).ask()
    if not address:
        return
    with console.status(
        Text(f"writing {firmware} @ {address}…", style=f"bold {NEON_CYAN}"),
        spinner="dots",
    ):
        rc, out, err = run_esptool([
            "--port", port,
            "--baud", str(settings.baudrate),
            "write_flash", address, firmware,
        ])
    show_esptool_result(rc, out, err, "firmware written", f"{firmware} → {port} @ {address}")


def action_settings(settings: Settings) -> None:
    baud = questionary.text(
        "Default baudrate:",
        default=str(settings.baudrate),
        validate=lambda v: v.isdigit() or "Must be a positive integer",
        style=QSTYLE,
    ).ask()
    if baud:
        settings.baudrate = int(baud)
    addr = questionary.text(
        "Default start address (hex, e.g. 0x1000):",
        default=settings.start_address,
        validate=lambda v: v.startswith("0x") or "Must start with 0x",
        style=QSTYLE,
    ).ask()
    if addr:
        settings.start_address = addr
    show_success(
        "settings updated",
        f"baudrate = {settings.baudrate}   ·   address = {settings.start_address}",
    )


# ───────────────────────────── main loop ─────────────────────────────

ACTIONS = {
    "[>]  SCAN     — detect connected ESP boards": action_detect,
    "[x]  ERASE    — wipe flash memory":           action_erase,
    "[^]  WRITE    — flash firmware binary":       action_write,
    "[=]  CONFIG   — baudrate, start address":     action_settings,
}
EXIT_CHOICE = "[q]  EXIT     — quit the shell"


def main() -> int:
    console.print(render_banner())
    settings = Settings()
    first = True
    while True:
        if not first:
            console.print(Rule(style=DIM_GREEN))
        first = False
        console.print(render_status(settings))
        choice = questionary.select(
            "Main menu:",
            choices=[*ACTIONS.keys(), EXIT_CHOICE],
            style=QSTYLE,
        ).ask()
        if choice is None or choice == EXIT_CHOICE:
            console.print(Text("◂ bye ▸", style=f"bold {NEON_MAGENTA}"))
            return 0
        ACTIONS[choice](settings)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print(Text("\n^C interrupted", style=f"bold {NEON_MAGENTA}"))
        sys.exit(130)
