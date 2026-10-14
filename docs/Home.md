# Hen-Brush Documentation

Hen-Brush plays light-and-motion animations on a swarm of drones. It loads one CSV animation per drone, streams the frames to the drones over a serial link, and shows their telemetry (position, status, progress). Two front ends share the same core: a terminal UI (Textual) and a desktop GUI (GTK4 / libadwaita).

> Written against `dev` @ 4ce1707; core, TUI and tests checked on Windows, Python 3.12.10.

> **This software drives physical drones.** Read the [safety notes](#safety-notes) before you connect a real radio. Try every new animation over the `loop://` port first, with the props removed.

## Who this is for

- **Operators** who want to run an animation: start with [Getting-Started](Getting-Started.md), then [Animation-Format](Animation-Format.md) and [User-Interfaces](User-Interfaces.md).
- **Developers** who change or extend the code: [Architecture](Architecture.md), [Presenter-API](Presenter-API.md), [Development-Guide](Development-Guide.md) and [Testing](Testing.md).
- **Firmware authors** who need the wire format: [Serial-Protocol](Serial-Protocol.md).

## Pages

| Page | What it covers |
|------|----------------|
| [Getting-Started](Getting-Started.md) | install on Windows and Linux, run the sample in the TUI and GUI, run the tests |
| [Architecture](Architecture.md) | components, dependencies, threads, data flow, design decisions |
| [Animation-Format](Animation-Format.md) | CSV columns and units, JSON config keys, file names, error and skip behavior |
| [Serial-Protocol](Serial-Protocol.md) | frame layout, checksum, every payload, float16, a verified hex example |
| [Scheduler-and-Drone-Lifecycle](Scheduler-and-Drone-Lifecycle.md) | states, start / pause / stop, frame timing, telemetry handling |
| [User-Interfaces](User-Interfaces.md) | TUI layout, keys and options; GUI pages, columns and Blueprint build step |
| [Presenter-API](Presenter-API.md) | build a new UI on `DronePresenter`, `DroneRow` and `LogBuffer` |
| [Testing](Testing.md) | test layout, markers, doubles, coverage gate, how to write a test |
| [Development-Guide](Development-Guide.md) | conventions, recipes, workflow facts, known limitations |
| [Troubleshooting](Troubleshooting.md) | symptoms, causes and fixes |
| [Glossary](Glossary.md) | terms used in the code |

## What is verified

| Area | Windows | Linux |
|------|---------|-------|
| Core (loader, protocol, scheduler, presenter) | **verified**: 587 tests pass, 99.38 % coverage | not run here |
| Terminal UI | **verified** by Textual pilot tests and by headless and error-path runs; not driven by hand in a real terminal | not run here |
| GTK4 GUI | not supported on Windows | **not verified on this machine.** The window has not yet been run on a real GTK stack; its 32 tests are skipped here |
| Drone hardware and firmware | not part of this repository; never run against real drones | |

Every page says how its claims were checked: *run on Windows*, *covered by tests*, *copied from the README or comments*, or *not verified on this machine*.

## Quick start (60 seconds, no hardware)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ControlTerminal sample_animation --port loop:// --speed 115200 --timeout 1
```

Select a drone, press **Start**, watch the step column advance, quit with `Ctrl+Q`. More in [Getting-Started](Getting-Started.md).

## Safety notes

Each of these facts comes from the code.

- The repository contains **no drone firmware and no hardware setup**. Nothing here was run against real drones or a real radio.
- Frames are **fire-and-forget**: no acknowledgement, no retry, no delivery confirmation (`ACK` exists as a packet type but is marked "Not Used"). See [Serial-Protocol](Serial-Protocol.md).
- **Stop and pause only stop or hold the sending of animation frames.** They send no command to the drones (no return-to-home, no disarm, no hold). What a drone does when frames stop depends on firmware that is not in this repository. See [Scheduler-and-Drone-Lifecycle](Scheduler-and-Drone-Lifecycle.md#what-stop-means).
- The software checks only that values can be encoded (drone id 0 to 255, colors 0 to 255, coordinates within float16 range). It has **no bounds, geofence, speed or collision checks**. The unit and axes of x, y and z are not defined in the code. These limits are checked when a frame is sent, not when the file is loaded. See [Animation-Format](Animation-Format.md#value-limits-and-when-they-are-enforced).
- The float16 byte order differs between commands (little-endian) and telemetry (big-endian) and has not been confirmed with firmware. See [Serial-Protocol](Serial-Protocol.md#byte-order).
- Try new animations over `loop://` first, with the props removed.

## License

The authoritative statement is the `LICENSE` file: the MIT License, "Copyright (c) 2025 Mateusz K". Source files carry header comments that differ from it; this is known and unresolved. See [Development-Guide](Development-Guide.md#known-limitations-and-open-questions).

## Known issues in one place

The detailed lists are on the pages above; the main ones are the unconfirmed float16 byte order, the telemetry animation byte that is received but not decoded, `Drone.position` that is never updated (so "Pos. error" is measured from the first frame), the GUI that has not been run on real GTK, and the license header question.
