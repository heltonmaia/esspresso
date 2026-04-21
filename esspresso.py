"""esspresso — interactive terminal wrapper around esptool.py for ESP32 boards."""

from __future__ import annotations

import glob
import os
import subprocess
import sys
from dataclasses import dataclass

import questionary
from rich.console import Console
from rich.panel import Panel

console = Console()


@dataclass
class Settings:
    baudrate: int = 460800
    start_address: str = "0x1000"


# ---------- discovery ----------

def list_serial_ports() -> list[str]:
    ports: list[str] = []
    for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*"):
        ports.extend(glob.glob(pattern))
    return sorted(ports)


def list_bin_files(directory: str = ".") -> list[str]:
    return sorted(glob.glob(os.path.join(directory, "*.bin")))


# ---------- esptool wrapper ----------

def run_esptool(args: list[str]) -> tuple[int, str, str]:
    cmd = ["esptool", *args]
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
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


def show_result(returncode: int, stdout: str, stderr: str, success_msg: str) -> None:
    if returncode == 0:
        console.print(Panel(success_msg, style="green", title="Success"))
        if stdout.strip():
            console.print(stdout.rstrip(), style="dim")
        return
    body = stderr.strip() or stdout.strip() or "Unknown error"
    hint = friendly_error_hint(stderr + stdout)
    message = f"{body}\n\n[bold]Hint:[/bold] {hint}" if hint else body
    console.print(Panel(message, style="red", title="Error"))


# ---------- interactive pickers ----------

def pick_port() -> str | None:
    ports = list_serial_ports()
    if not ports:
        console.print("[yellow]No serial ports found on /dev/ttyUSB* or /dev/ttyACM*.[/yellow]")
        return None
    return questionary.select("Select a port:", choices=ports).ask()


def pick_firmware() -> str | None:
    bins = list_bin_files(".")
    custom = "Type a custom path…"
    choices = [*bins, custom] if bins else [custom]
    if not bins:
        console.print("[yellow]No .bin files in current directory.[/yellow]")
    choice = questionary.select("Select firmware (.bin):", choices=choices).ask()
    if choice is None:
        return None
    if choice != custom:
        return choice
    path = questionary.path("Path to .bin file:").ask()
    if not path:
        return None
    if not os.path.isfile(path):
        console.print(f"[red]File not found: {path}[/red]")
        return None
    return path


# ---------- actions ----------

def action_detect(_: Settings) -> None:
    ports = list_serial_ports()
    if not ports:
        console.print(Panel(
            "No boards detected on /dev/ttyUSB* or /dev/ttyACM*.",
            style="yellow", title="Detect",
        ))
        return
    listing = "\n".join(f"  • {p}" for p in ports)
    console.print(Panel(listing, style="cyan", title=f"{len(ports)} port(s) found"))


def action_erase(settings: Settings) -> None:
    port = pick_port()
    if not port:
        return
    if not questionary.confirm(f"Erase flash on {port}?", default=False).ask():
        return
    with console.status("[cyan]Erasing flash…[/cyan]", spinner="dots"):
        rc, out, err = run_esptool(["--port", port, "--baud", str(settings.baudrate), "erase_flash"])
    show_result(rc, out, err, f"Flash erased on {port}.")


def action_write(settings: Settings) -> None:
    port = pick_port()
    if not port:
        return
    firmware = pick_firmware()
    if not firmware:
        return
    address = questionary.text("Flash address:", default=settings.start_address).ask()
    if not address:
        return
    with console.status(
        f"[cyan]Writing {firmware} to {port} @ {address}…[/cyan]", spinner="dots"
    ):
        rc, out, err = run_esptool([
            "--port", port,
            "--baud", str(settings.baudrate),
            "write_flash", address, firmware,
        ])
    show_result(rc, out, err, f"Wrote {firmware} to {port} at {address}.")


def action_settings(settings: Settings) -> None:
    baud = questionary.text(
        "Default baudrate:",
        default=str(settings.baudrate),
        validate=lambda v: v.isdigit() or "Must be a positive integer",
    ).ask()
    if baud:
        settings.baudrate = int(baud)
    addr = questionary.text(
        "Default start address (hex, e.g. 0x1000):",
        default=settings.start_address,
        validate=lambda v: v.startswith("0x") or "Must start with 0x",
    ).ask()
    if addr:
        settings.start_address = addr
    console.print(
        f"[green]Settings updated.[/green] baudrate={settings.baudrate} address={settings.start_address}"
    )


# ---------- main loop ----------

ACTIONS = {
    "Detect connected boards": action_detect,
    "Erase flash": action_erase,
    "Write firmware": action_write,
    "Settings": action_settings,
}


def banner() -> None:
    console.print(Panel.fit(
        "[bold cyan]esspresso[/bold cyan] — interactive ESP32 flasher\n"
        "[dim]wrapper around esptool.py[/dim]",
        border_style="cyan",
    ))


def main() -> int:
    banner()
    settings = Settings()
    while True:
        choice = questionary.select(
            "Main menu:",
            choices=[*ACTIONS.keys(), "Exit"],
        ).ask()
        if choice is None or choice == "Exit":
            console.print("[cyan]Bye.[/cyan]")
            return 0
        ACTIONS[choice](settings)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[cyan]Interrupted.[/cyan]")
        sys.exit(130)
