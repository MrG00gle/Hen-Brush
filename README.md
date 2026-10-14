# Hen-Brush

Hen-Brush plays light-and-motion animations on a swarm of drones. It loads one CSV animation per drone,
streams the frames to the drones over a serial link and shows their telemetry (position, status, progress).
Two front ends share the same core: a terminal UI (Textual) and a desktop GUI (GTK4 / libadwaita).

## Documentation

The full documentation lives in [docs/](docs/Home.md): [Getting started](docs/Getting-Started.md),
[Architecture](docs/Architecture.md), [Animation format](docs/Animation-Format.md),
[Serial protocol](docs/Serial-Protocol.md), [Scheduler and drone lifecycle](docs/Scheduler-and-Drone-Lifecycle.md),
[User interfaces](docs/User-Interfaces.md), [Presenter API](docs/Presenter-API.md), [Testing](docs/Testing.md),
[Development guide](docs/Development-Guide.md), [Troubleshooting](docs/Troubleshooting.md) and
[Glossary](docs/Glossary.md).

## Requirements

- Python 3.10 or newer (developed and tested on 3.12). The code uses `match` and `X | None`, so a
  `python` on your PATH that is 3.8 or 3.9 will not work. On Windows use the launcher: `py -3.12`.
- A serial port, or the built-in loopback `loop://` for trying things out without hardware.
- The GUI also needs Linux with GTK 4.10+, libadwaita 1.4+ and `blueprint-compiler` 0.10+ (see below).

## Setup

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

This covers the core, the terminal UI and the tests. The GUI is not supported on Windows.

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For the GUI install the system packages first, then the Python binding:

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

If you would rather use the distribution's PyGObject instead of building it, create the venv with
`python3 -m venv --system-site-packages .venv` and skip `requirements-gui.txt`.

`blueprint-compiler` turns `ControlWindow/ui/window.blp` into `window.ui` the first time the GUI starts and
whenever the `.blp` changes. The generated `window.ui` is git-ignored. Set `BLUEPRINT_COMPILER` if the
executable is not on `PATH`.

## Run

Both programs take the animation directory as the first argument.

```bash
python -m ControlTerminal <animation_dir> [--port COM3|/dev/ttyUSB0|loop://] [--speed 115200] [--timeout 1] [--refresh 0.25]
python -m ControlWindow   <animation_dir> [--port ...] [--speed ...] [--timeout ...]
```

`--port`, `--speed` and `--timeout` override the serial settings from the animation directory's JSON file.
If you give none of them, the JSON file must provide all three. Both programs exit with code 2 and a one-line
message when the directory is missing or no complete serial configuration is available.

To try the TUI without hardware, use the bundled sample and the loopback port:

```bash
python -m ControlTerminal sample_animation --port loop:// --speed 115200 --timeout 1
```

### Animation directory format

- `drone_<n>.csv` (`Drone<n>.csv` and `<n>.csv` also work): one file per drone, no header, columns
  `timestamp_ms,x,y,z,r,g,b`. The drone id is `n` and must be 0-255. Malformed rows are skipped and logged.
- An optional `*.json` file (the first by name is used) with the serial settings:

```json
{ "serial_port": "/dev/ttyUSB0", "serial_speed": 115200, "ping_timeout": 1 }
```

## Tests

```bash
pip install -r requirements.txt
python -m pytest
```

`pytest.ini` turns on coverage (branch coverage, missing lines in the report) and fails the run below 85 %.
Coverage covers `ControlTower`, `ControlTerminal` and the GTK-free parts of `ControlWindow`; the GTK glue
(`window.py`, `app.py`, `models.py`, `__main__.py`) is excluded in `.coveragerc` because it needs a display.

Markers:

- `gui`: needs GTK4, libadwaita and a display. These tests are skipped when `gi` is not importable.
- `serial`: needs a real serial port. Deselect with `-m "not serial"`. No test needs one today; serial
  behavior is tested through `loop://` and a fake port.
- `slow`: takes more than a second.

```bash
python -m pytest -m "not gui"     # everything that runs without GTK
python -m pytest -m gui           # only the GUI smoke tests (skipped without GTK)
```

## Protocol overview

Every message is a frame:

```
AA 55 | type | length | payload (length bytes) | checksum | 55 AA
```

- `checksum` is the XOR of `type`, `length` and every payload byte.
- The payload is at most 255 bytes.
- The receiver keeps a persistent buffer. Garbage, a wrong footer, a wrong checksum or an unknown type is
  logged and skipped (it resynchronises on the next header); bad wire data never raises.

Packet types:

| Type | Value | Direction | Meaning |
|------|-------|-----------|---------|
| PING | 0x01 | | reserved |
| PONG | 0x02 | | reserved |
| DATA | 0x03 | | reserved |
| ACK | 0x04 | | not used |
| POINT | 0x05 | host to drone | go to a position |
| CPOINT | 0x06 | host to drone | go to a position and set the color (one animation frame) |
| COMMAND | 0x07 | host to drone | command byte |
| TELEMETRY | 0x08 | drone to host | state report |
| ERROR | 0xFF | | not used |

Payloads (`f16` is an IEEE 754 half-precision float):

| Payload | Size | Layout |
|---------|------|--------|
| Point | 8 | drone_id (1), command (1), x, y, z (3 x f16, little-endian) |
| CPoint | 11 | drone_id (1), command (1), x, y, z (3 x f16, little-endian), r, g, b (3 x 1) |
| Command | 2 | drone_id (1), command (1) |
| Telemetry | 12 | drone_id (1), x, y, z (3 x f16, big-endian), r, g, b (3 x 1), drone status (1), animation status (1, not decoded) |

Commands: `TELEMETRY_REQUEST` 1, `ARM` 2, `POSITION_COLOR` 3, `POSITION` 4, `RTH` 5, `DISARM` 6.
Drone status: `LOST` 1, `INACTIVE` 2, `OK` 3.

Positions are little-endian when sent and big-endian when received. This is kept as it is because the
firmware is not part of this repository (see Known limitations).

## Architecture

```
                 +---------------------+      +---------------------+
                 |  ControlTerminal    |      |  ControlWindow      |
                 |  Textual TUI        |      |  GTK4 / libadwaita  |
                 +----------+----------+      +----------+----------+
                            |   rows, button states,     |
                            |   actions, log lines       |
                 +----------v----------------------------v----------+
                 |  ControlTower.Presenter                          |
                 |  DronePresenter, DroneRow, LogBuffer, Bootstrap  |
                 +----------------------+---------------------------+
                                        | Controller protocol (start / pause / stop)
                 +----------------------v---------------------------+
                 |  ControlTower  (facade)                          |
                 +-----+-----------------+----------------------+---+
                       |                 |                      |
              +--------v------+  +-------v--------+   +---------v----------+
              | Loader        |  | Scheduler      |   | CommunicationHandler|
              | CSV + JSON    |  | one thread per |   | frames over serial  |
              | -> Drones     |  | drone + listener|  | (pyserial, loop://) |
              +--------+------+  +-------+--------+   +---------+----------+
                       |                 |                      |
                 +-----v-----------------v----------------------v----------+
                 |  ControlTower.common: Drone, Animation, Point, Color,    |
                 |  Command, DroneStatus, DroneAnimationStatus, errors      |
                 +----------------------------------------------------------+
```

- core (`ControlTower`): `common` holds the domain types. `Loader` builds drones from an animation
  directory. `CommunicationHandler` frames and parses packets on a serial port. `Scheduler` runs one thread
  per drone that sends each frame at its timestamp, plus a listener thread for telemetry. `ControlTower`
  ties them together and exposes `start`, `pause`, `stop`, `send_to_point` and `shutdown`.
- presenter (`ControlTower.Presenter`): UI-agnostic. `DronePresenter` turns drones into formatted
  `DroneRow`s, decides which buttons are enabled and runs the start/pause/stop actions. `LogBuffer` collects
  log records. `Bootstrap` holds the command-line arguments shared by both UIs.
- TUI (`ControlTerminal`): a Textual app that renders presenter rows and log lines.
- GUI (`ControlWindow`): a GTK4/libadwaita window built from `ui/window.blp`. `row_mapping.py` and
  `ui_build.py` are GTK-free and unit-tested.

Threading rules: scheduler, serial and logging threads only produce data. Only the UI thread touches
widgets. Both UIs poll on a timer for the drone table; the TUI also polls the log buffer, while the GUI
receives log lines through a subscriber that schedules work with `GLib.idle_add`.

Scheduler behavior: for each frame the drone thread waits for the pause gate, waits the time between
timestamps, sets `animation_step` and then sends that frame. When the last frame is sent the drone is
`ENDED`; `start` on an ended or ready drone restarts it from frame 0, and `start` on a paused drone
resumes it. `stop` is prompt.

## Known limitations and open questions

- Licensing is inconsistent (the `LICENSE` file is MIT, the source headers say LGPL-3.0-or-later). It has not
  been resolved yet, so the headers are untouched.
- Float16 byte order differs between commands (little-endian) and telemetry (big-endian). Confirm with the
  firmware before changing either side.
- Telemetry byte 11 (animation status) is received but not decoded.
- Drone ids above 255 cannot be sent on the wire and are skipped by the loader.
- The GTK window and the Blueprint file have not been run or compiled on the development machine
  (Windows). Check them on Linux.
