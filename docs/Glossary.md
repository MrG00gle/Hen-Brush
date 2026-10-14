# Glossary

Terms that exist in the code, in alphabetical order. Where the code uses one word for two things, both meanings are listed.

| Term | Meaning | Where in code |
|------|---------|---------------|
| Animation | The flight path and light show of one drone: parallel lists of timestamps (ms), points and colors, one entry per frame. Loaded from one CSV file. See [Animation-Format](Animation-Format.md) | `common/Animation.py` |
| Animation frame | One row of an animation: `(timestamp, point, color)`. Not the same as a wire frame | `Animation.get_frame`, `Frame` |
| Animation step | The 0-based index of the animation frame a drone is at. Shown as `step/length`, for example `3/12` | `Drone.animation_step`, `DroneRow.step_text` |
| ARM, DISARM, RTH | Values of `Command` (2, 6 and 5). The repository does not define what the firmware does with them, and no UI sends them | `common/Command.py` |
| Battery | A `Drone` field (0 to 100, or -1 when unknown). Present but unused: nothing in the repository sets it | `Drone.battery` |
| Blueprint (`.blp`) | The markup language in which the GUI window is written; compiled to GTK builder XML (`window.ui`) by `blueprint-compiler` | `ControlWindow/ui/window.blp`, `ui_build.py` |
| Checksum | The XOR of the type byte, the length byte and every payload byte of a wire frame | `CommunicationProtocol.calculate_checksum` |
| Command | The command byte in a `POINT`, `CPOINT` or `COMMAND` payload: `TELEMETRY_REQUEST` 1, `ARM` 2, `POSITION_COLOR` 3, `POSITION` 4, `RTH` 5, `DISARM` 6 | `common/Command.py` |
| `Controller` | The `Protocol` the presenter needs: `drones`, `start`, `pause`, `stop`. `ControlTower` satisfies it | `Presenter/DronePresenter.py` |
| ControlTerminal | The Textual terminal UI, run with `python -m ControlTerminal` | `ControlTerminal/` |
| ControlTower | Two things with one name: the core package `ControlTower/`, and the facade class `ControlTower` that wires the loader, scheduler and communication handler | `ControlTower/ControlTower.py` |
| ControlWindow | The GTK4/libadwaita GUI, run with `python -m ControlWindow` | `ControlWindow/` |
| CPoint (CPOINT) | A "colored point": a position plus an RGB color. Packet type `0x06`, 11-byte payload. One CPOINT is sent per animation frame | `CPointPayload`, `PacketType.CPOINT` |
| Dispatcher thread | The thread, named `Dispatcher_Thread(<id>)`, that plays one drone's animation | `Scheduler._dispatch` |
| Drone | An object with an id, an animation, two statuses, a position, a reported position and an animation step | `common/Drone.py` |
| Drone ID | The number in the CSV file name, 0 to 255 (one byte on the wire) | `Loader`, `MAX_DRONE_ID` |
| `DroneAnimationStatus` | Playback state of a drone: `LIVE` (1, playing), `PAUSED` (2), `ENDED` (3), `READY` (4, not started). See [Scheduler-and-Drone-Lifecycle](Scheduler-and-Drone-Lifecycle.md) | `common/DroneAnimationSatus.py` |
| `DroneRow` | A display-ready snapshot of one drone: strings already formatted, plus `step` and `length` | `Presenter/DroneRow.py` |
| `DroneStatus` | Health status of a drone as reported by telemetry: `LOST` (1), `INACTIVE` (2), `OK` (3) | `common/DroneStatus.py` |
| float16 | IEEE 754 half-precision float, two bytes, used for coordinates on the wire. Largest finite value 65504 | `payload/_float16.py` |
| Footer, header | The two fixed bytes at the end (`55 AA`) and at the start (`AA 55`) of a wire frame | `CommunicationProtocol.FOOTER`, `HEADER` |
| Gate (pause gate) | The `threading.Event` in a run that is cleared while the drone is paused | `Scheduler._Run.gate` |
| Home position | The first point of a drone's animation | `Drone.home_position` |
| Listener thread | The thread, named `Listener`, that reads telemetry and applies it to the drones | `Scheduler._listen` |
| `LogBuffer`, `LogEntry` | A thread-safe `logging` handler with a bounded buffer, and one line in it | `Presenter/LogBuffer.py` |
| `loop://` | pyserial's in-process loopback port; whatever is written can be read back. Used to run without hardware | `serial.serial_for_url` |
| Packet, `PacketType` | A message on the serial link, and the byte that says what it is. The code also calls the whole message a "frame" | `PacketType.py` |
| POINT | A position without a color. Packet type `0x05`, 8-byte payload | `PointPayload` |
| Position error | The 3D distance between `Drone.position` and the reported position, shown with two decimals. `Drone.position` is never updated in production code, so it is the distance from the first frame | `Drone.position_error` |
| Presenter | The UI-agnostic layer (`DronePresenter` and friends) that both UIs use | `ControlTower/Presenter/` |
| Reported position | The position the drone last sent in telemetry; starts at the home position | `Drone.reported_position` |
| Telemetry | The state report a drone sends to the host: id, position, color and status. Packet type `0x08`, 12-byte payload | `TelemetryPayload` |
| Timestamp | The first CSV column, in milliseconds from the start of the animation | `Animation.timestamps` |
| Wire frame | The bytes on the serial link: header, type, length, payload, checksum, footer. See [Serial-Protocol](Serial-Protocol.md). Not the same as an animation frame | `CommunicationProtocol.create_packet` |

## See also

- [Home](Home.md)
- [Architecture](Architecture.md)
- [Serial-Protocol](Serial-Protocol.md)
