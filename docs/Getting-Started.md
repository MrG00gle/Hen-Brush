# Getting Started

Install Hen-Brush, run the bundled sample animation without hardware, and run the tests.

> **How this page was checked:** the Windows commands were run with the project's `.venv` (Python 3.12.10). The Linux and GUI commands are copied from `README.md` and `requirements-gui.txt` and were **not verified on this machine**. The interactive TUI session was not driven by hand; it is covered by Textual pilot tests.

Hen-Brush drives physical drones. Read the [safety notes](Home.md#safety-notes) before connecting a real radio, and try new animations over `loop://` first.

## Prerequisites

- Python 3.10 or newer (the code uses `match` and `X | None`; it was developed and tested on 3.12). On Windows, use the launcher: `py -3.12`.
- A serial port, or the built-in loopback `loop://`, which needs no hardware.
- For the GUI only: Linux with GTK 4.10+, libadwaita 1.4+ and `blueprint-compiler` 0.10+.

## Install on Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

This covers the core, the terminal UI and the tests. The GUI is not supported on Windows. `requirements.txt` pins `pyserial==3.5`, `numpy==2.5.4`, `textual==8.2.8`, `pytest==9.1.1` and `pytest-cov==7.1.0`. On this machine the installed versions equal these pins.

## Install on Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Linux with the GUI

> **Not verified on this machine.** Copied from `README.md` and `requirements-gui.txt`.

Install the system packages first (GTK4, libadwaita, gobject-introspection and `blueprint-compiler`), then the Python binding:

```bash
# Debian / Ubuntu
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 blueprint-compiler \
    libgirepository1.0-dev libcairo2-dev pkg-config python3-dev
# Fedora
sudo dnf install python3-gobject gtk4 libadwaita blueprint-compiler
# Arch
sudo pacman -S python-gobject gtk4 libadwaita blueprint-compiler

pip install -r requirements-gui.txt
```

`requirements-gui.txt` contains `PyGObject==3.58.1`; that pin was not install-tested. If you would rather use the distribution's PyGObject, create the venv with `python3 -m venv --system-site-packages .venv` and skip `requirements-gui.txt`.

`blueprint-compiler` turns `ControlWindow/ui/window.blp` into `window.ui` the first time the GUI starts, and again whenever the `.blp` changes. Set `BLUEPRINT_COMPILER` if the executable is not on `PATH`. See [User-Interfaces](User-Interfaces.md#blueprint-build-step).

## Run the sample animation

The bundled `sample_animation` has three drones with 12 frames each, 500 ms apart (about 5.5 s long), and a `config.json` that points at `loop://`.

### Terminal UI

```powershell
.venv\Scripts\python.exe -m ControlTerminal sample_animation --port loop:// --speed 115200 --timeout 1
```

On Linux, with the venv active:

```bash
python -m ControlTerminal sample_animation --port loop:// --speed 115200 --timeout 1
```

You get a drone table on the left, a log pane on the right and six buttons. Select a row, press **Start** (or **Start all**), and watch the "Animation Step" column advance. Quit with `Ctrl+Q`. All keys and options are in [User-Interfaces](User-Interfaces.md#tui-controlterminal).

Because the port is `loop://`, no telemetry comes back, so "Position" stays at each drone's first frame and "Pos. error" stays `0.00`. That is expected.

`python -m ControlTerminal --help` was run on Windows and printed the usage and options shown in [User-Interfaces](User-Interfaces.md#command-line).

### GUI

> **Not verified on this machine.** Linux only.

```bash
python -m ControlWindow sample_animation --port loop:// --speed 115200 --timeout 1
```

On this Windows machine the command prints `ControlWindow: GTK4/libadwaita GUI is not available: No module named 'gi'` and exits with code 1.

### A quick check without any UI

`scripts/presenter_demo.py` drives the presenter layer for about two seconds and prints a live table. It writes its own temporary animation, uses `loop://`, and exits with code 0 (run on Windows):

```powershell
.venv\Scripts\python.exe scripts\presenter_demo.py
```

It prints five snapshots with the drones `Live` and the step advancing, then `Stop requested for all drones (3)`, a final table with the drones `Ended`, and the last five log lines.

## Serial settings

The program needs a port, a speed and a timeout. They come from command-line flags, from a JSON file in the animation directory, or from both:

| Situation | Result |
|-----------|--------|
| `--port`, `--speed` and `--timeout` are all given | the flags are used; the JSON file is not needed |
| only some flags are given, and the JSON file is complete | **the JSON file is used**, the flags are ignored (not merged), and a warning is logged: `Incomplete direct serial config (port, speed and timeout are all needed), using the config file.` |
| no flags, and a complete JSON file | the JSON file is used |
| neither is complete | exit code 2, `ControlTerminal: No serial config detected` (or `ControlWindow: ...`) |

A flag value of `0` counts as given. The JSON format is described in [Animation-Format](Animation-Format.md#serial-settings-file).

## Run the tests

From the repository root, with the venv active (or use `.venv\Scripts\python.exe` on Windows):

```bash
pip install -r requirements.txt
python -m pytest
```

`pytest.ini` turns on branch coverage and fails the run below 85 %. Last run on Windows: **587 passed, 32 skipped, total coverage 99.38 %**. The 32 skips are the GUI tests, which need GTK. Variants:

```bash
python -m pytest -m "not gui"     # everything that runs without GTK
python -m pytest -m gui           # only the GUI tests (skipped without GTK)
```

More in [Testing](Testing.md).

## Where to go next

- Write your own animation: [Animation-Format](Animation-Format.md)
- Understand the design: [Architecture](Architecture.md)
- Something went wrong: [Troubleshooting](Troubleshooting.md)

## See also

- [Home](Home.md)
- [User-Interfaces](User-Interfaces.md)
- [Testing](Testing.md)
