# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project intent

`esspresso` is an interactive Python terminal app that wraps `esptool.py` to make flashing firmware to ESP32 boards easier. It is a UX layer, **not** a reimplementation — all flash operations are delegated to `esptool` via `subprocess`. Do not port esptool logic into this codebase; shell out.

## Layout

Single-module project — everything lives in `esspresso.py`. Keep it that way until a concrete reason to split (e.g. a second entry point, a non-trivial test suite). Do not preemptively package into subdirectories.

## Install and run

This project uses `uv` with a lockfile (`uv.lock`, committed). The venv lives **outside** the repo at `/mnt/hd3/uv-common/uv-esspresso`, and the uv cache is shared at `/mnt/hd3/uv-cache`. These paths are specific to this machine — do not hardcode them in code, only in env vars.

Required env vars (set by the shell helper, see `.zshrc` helpers section below):

```
UV_CACHE_DIR=/mnt/hd3/uv-cache
UV_PROJECT_ENVIRONMENT=/mnt/hd3/uv-common/uv-esspresso
```

With those set, from the project root:

```bash
uv sync              # install/refresh from uv.lock into the external venv
uv run esspresso     # run the CLI without activating anything
uv add <pkg>         # add a dep; updates pyproject.toml + uv.lock
uv lock --upgrade    # bump locked versions
```

`esptool.py` is pulled in as a transitive dependency — after `uv sync` it lives inside the external venv's `bin/` and is on `PATH` whenever the venv is activated or you use `uv run`.

## .zshrc helpers (activate / deactivate)

Two shell functions expected in the user's `~/.zshrc`:

```bash
export UV_CACHE_DIR=/mnt/hd3/uv-cache

uvon() {
    local name="${1:-$(basename "$PWD")}"
    export UV_PROJECT_ENVIRONMENT="/mnt/hd3/uv-common/uv-${name}"
    [ -d "$UV_PROJECT_ENVIRONMENT" ] || uv venv "$UV_PROJECT_ENVIRONMENT"
    source "$UV_PROJECT_ENVIRONMENT/bin/activate"
}
uvoff() {
    deactivate 2>/dev/null
    unset UV_PROJECT_ENVIRONMENT
}
```

Usage from inside the project: `uvon` (activates `uv-esspresso`), `uvoff` (deactivates). No `.venv/` is ever created in the repo.

## No build / lint / test yet

There is no test suite, linter config, or CI. Do not invent commands. `uv run python -m py_compile esspresso.py` is the only meaningful static check today — use it before handing off changes.

## Architecture

- **UI stack:** `rich` for panels and colored output; `questionary` for arrow-key-navigable menus (chosen over `InquirerPy`). Don't mix in a second prompt library.
- **Main loop** (`main` in `esspresso.py`): shell-style REPL backed by the `ACTIONS` dict. To add a new menu entry, write an `action_*(settings)` function and register it in `ACTIONS` — the loop picks it up automatically.
- **`Settings` dataclass:** in-memory only (baudrate, start_address). No persistence — if you add a config file, plumb it through `Settings`, not globals.
- **Serial port discovery** (`list_serial_ports`): Linux-only glob of `/dev/ttyUSB*` and `/dev/ttyACM*`. Do not swap in `pyserial.tools.list_ports` without discussion — the spec is intentionally Linux-focused.
- **Firmware discovery** (`pick_firmware`): lists `*.bin` in CWD, plus a "Type a custom path…" escape hatch.
- **esptool invocation** (`run_esptool`): `subprocess.run` on `esptool --port … --baud … <cmd> …`, captures stdout/stderr. Use `esptool` (not `esptool.py`) — the `.py` name is deprecated in esptool ≥ 5. Never reimplement esptool logic in-process.
- **Error surface** (`show_result` + `friendly_error_hint`): success → green panel; failure → red panel with a translated hint for common causes (BOOT not held, permission denied, port busy, esptool missing). When adding new error cases, extend `friendly_error_hint` rather than sprinkling `if`s at call sites.

## Locale

User-facing strings (menu labels, prompts, success/error messages) are in English. Keep them in English unless the user explicitly asks for another language.
