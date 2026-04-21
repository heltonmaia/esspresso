# esspresso

An interactive terminal UI for flashing ESP32 boards — a friendly wrapper
around [`esptool`](https://github.com/espressif/esptool) with menus, colors,
and translated error hints.

## Features

- Arrow-key-navigable main menu (shell-style REPL until you pick *Exit*).
- Auto-detection of connected boards on `/dev/ttyUSB*` and `/dev/ttyACM*`.
- Erase flash and write firmware with confirmation prompts.
- Firmware picker that lists `*.bin` files in the current directory, or lets
  you type a custom path.
- Configurable defaults (baudrate, start address) kept in memory for the
  session.
- Human-readable error panels for the usual failure modes: BOOT button not
  held, serial port permission denied, port busy, `esptool` missing.

## Requirements

- Linux (serial port discovery looks for `/dev/ttyUSB*` and `/dev/ttyACM*`).
- Python 3.10 or newer.
- [`uv`](https://docs.astral.sh/uv/) — recommended, reads the committed
  `uv.lock` for reproducible installs.

## Install

```bash
git clone https://github.com/heltonmaia/esspresso.git
cd esspresso
uv sync
```

`uv sync` creates a local `.venv/` and installs the pinned versions from
`uv.lock`, including `esptool` itself.

## Run

Without activating the venv:

```bash
uv run esspresso
```

Or, if you prefer an activated shell:

```bash
source .venv/bin/activate
esspresso
```

## Serial port permissions

On most Linux distros your user needs to be in the `dialout` group to access
`/dev/ttyUSB*`:

```bash
sudo usermod -aG dialout $USER
```

Log out and back in after running this.

## Flashing tips

- Many ESP32 boards require holding the **BOOT** button (and briefly tapping
  **EN**/**RST**) to enter the bootloader before erase or write.
- Close any serial monitor or IDE that might be holding the port before
  flashing.
- If the default baudrate (460800) fails, try a lower one (115200) from the
  *Settings* menu.

## License

[MIT](LICENSE) © [Helton Maia](https://heltonmaia.com) — helton.maia@ufrn.br
