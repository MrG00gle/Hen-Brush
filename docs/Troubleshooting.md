# Troubleshooting

Symptoms, causes and fixes, each with the place in the code and how it was checked.

> **How the entries were checked:** entries marked *run on Windows* were reproduced with the project's `.venv` (Python 3.12.10) and the message is pasted from the run. Entries marked *from code* come from reading the source. Entries marked *not verified on this machine* involve GTK or Linux.

## Python version

### `SyntaxError` on `match` or on `X | None`

- **Cause:** `python` on your `PATH` is 3.8 or 3.9. The code needs Python 3.10 or newer. *From the README and the code.*
- **Fix:** create the venv with a newer interpreter, on Windows `py -3.12 -m venv .venv`. See [Getting-Started](Getting-Started.md).
- *Not verified on this machine* (only 3.12 is installed).

## Start-up errors (exit code 2)

Both entry points print one line to stderr and exit with code 2. All of these were *run on Windows*.

### `Animation directory not found` / `Animation path is not a directory`

```text
ControlTerminal: Animation directory not found: nodir
ControlTerminal: Animation path is not a directory: README.md
```

- **Cause:** the `<animation_dir>` argument is wrong (`Loader.__init__` raises `FileNotFoundError` or `NotADirectoryError`).
- **Fix:** pass the folder that contains the `drone_<n>.csv` files.

### `No serial config detected`

```text
ControlTerminal: No serial config detected
```

- **Cause:** you gave not all of `--port`, `--speed` and `--timeout`, and the folder has no complete JSON file. Before the message you also see, on the console, `No config file with JSON format found in directory: ...`, and the same `No serial config detected` line logged by `ControlTower`.
- **Fix:** give all three flags, or add a JSON file with `serial_port`, `serial_speed` and `ping_timeout`. See [Getting-Started](Getting-Started.md#serial-settings).

### The port cannot be opened

```text
ControlTerminal: could not open port 'COM99': FileNotFoundError(2, 'The system cannot find the file specified.', None, 2)
```

- **Cause:** pyserial cannot open the device. `serial.SerialException` is an `OSError`, and both entry points catch `OSError`.
- **Fix:** check the port name (`COM3`, `/dev/ttyUSB0`), that the device is plugged in, that no other program holds it, and on Linux that your user may access it. Use `loop://` to test without hardware.
- The message above is from Windows. The text on Linux comes from pyserial and was not verified.
- `SerialError` exists in `ControlTower.common` but nothing raises it; port failures are pyserial exceptions.

### `--refresh must be greater than 0`

```text
python -m ControlTerminal: error: --refresh must be greater than 0
```

- **Cause:** `--refresh 0` or a negative value. Exit code 2.
- **Fix:** use a positive number of seconds, the default is 0.25.

### Partial flags are ignored

- **Symptom:** you gave `--port COM3` only, and the program still used `loop://` from the JSON file.
- **Cause:** direct flags win only when `--port`, `--speed` and `--timeout` are **all** given (`0` counts as given). Otherwise a complete JSON file is used and a warning is logged: `Incomplete direct serial config (port, speed and timeout are all needed), using the config file.` The values are not merged. *Run on Windows.*
- **Fix:** give all three flags, or remove the JSON file.

## Drones and animations

### A drone is missing

- **Cause:** the loader skipped its file. Reasons: the name does not match the pattern, the id is above 255, the id is a duplicate, the file has no valid row, or it could not be read. The messages and their levels are in the table in [Animation-Format](Animation-Format.md#what-happens-on-errors). *Run on Windows.*
- **Where to look:** the console, **before** the UI starts. These messages are logged before the log buffer is installed, so they are **not** in the log pane. See [Presenter-API](Presenter-API.md#log-buffer-and-startup-messages).
- **Fix:** rename or correct the file.

### A row is skipped with `Skipping malformed row`

- **Cause:** a blank line, a header line, text where a number is expected, or fewer than 7 columns. *Run on Windows.*
- **Fix:** remove blank and header lines; every row needs `timestamp_ms,x,y,z,r,g,b`.

### `ping_timeout` is not a ping

- **Cause:** the JSON key `ping_timeout` is used as the serial **read timeout in seconds**, converted with `int()` (so `2.9` becomes `2`). *From code; the conversion was run on Windows.*

### Rows stay at the starting position and "Pos. error" stays 0.00

- **Cause (with `loop://`):** this is expected. The loopback only returns the host's own `CPOINT` frames, which `listen()` skips. No telemetry arrives, so the reported position is never updated.
- **Cause (with a real link):** see the next entry.

### "Pos. error" looks wrong with real telemetry

- **Cause:** `Drone.position` (the expected position) is never updated by production code, so it stays at the first frame. The error is the distance between the reported position and the first frame, not the frame that should be reached now. *From code.*

### A drone goes to Ended early with a traceback on the console

- **Symptom:** one drone shows `Ended` after a few frames, and the console shows a traceback in `Dispatcher_Thread(0)`.
- **Cause:** a CSV value that cannot be encoded is only detected when its frame is sent: a colour channel outside 0 to 255, or a coordinate that is not finite or does not fit float16 (more than 65504 in magnitude). The `ValueError` ends that drone's thread, and the scheduler marks the drone `ENDED`. Other drones keep playing.
- **Reproduced on Windows** with a one-drone animation over `loop://` whose second row has red = 300. The console showed the traceback ending in:

```text
Exception in thread Dispatcher_Thread(0):
...
  File "...\ControlTower\ControlTower.py", line 107, in _dispatch_operation
    self.comm.send(CPointPayload(drone.id, point, color))
...
ValueError: RGB values must be integers between 0 and 255
```

  and the drone was `ENDED` with `animation_step` 1 (the step that failed).
- **Fix:** correct the value in the CSV. See [Animation-Format](Animation-Format.md#value-limits-and-when-they-are-enforced).

### Stop does not land or return the drones

- **Cause:** by design. `stop` and `pause` only stop or hold the sending of animation frames. They send no command (no `RTH`, no `DISARM`, no hold). See [Scheduler-and-Drone-Lifecycle](Scheduler-and-Drone-Lifecycle.md#what-stop-means).

## Serial link

### `Dropping frame: bad footer` / `checksum mismatch` / `unknown packet type`

```text
WARNING Dropping frame: bad footer (...)
WARNING Dropping frame: checksum mismatch, expected 182, got 73 (...)
WARNING Dropping frame: unknown packet type 0x42 (...)
```

- **Cause:** line noise, a wrong speed, or a firmware that uses a different packet layout. The receiver resynchronizes by itself; nothing is raised. *Messages produced on Windows with corrupted frames.*
- **Fix:** check the baud rate on both sides and the cable or radio. See [Serial-Protocol](Serial-Protocol.md#receiving).

### `Malformed telemetry payload ...`

```text
Malformed telemetry payload 0102: Expected 12 bytes, got 2
```

- **Cause:** a telemetry packet that is not exactly 12 bytes long, or whose status byte is not 1, 2 or 3 (`9 is not a valid DroneStatus`). The packet is dropped and the listener continues. The errors were *run on Windows*; the log line format is from `CommunicationHandler.listen`.

### Telemetry positions look mirrored or wrong

- **Cause:** commands encode float16 little-endian, telemetry decodes it big-endian. This is documented in the code and has not been confirmed against firmware (the firmware is not in this repository).
- **Fix:** confirm the byte order with the firmware before changing either side. See [Serial-Protocol](Serial-Protocol.md#byte-order).

## GUI

### `ControlWindow: GTK4/libadwaita GUI is not available`

```text
ControlWindow: GTK4/libadwaita GUI is not available: No module named 'gi'
```

- **Cause:** PyGObject (`gi`) is not installed. Exit code 1. *Run on Windows.* The GUI needs Linux, GTK 4.10+, libadwaita 1.4+ and `blueprint-compiler` 0.10+.
- **Fix:** install the packages in [Getting-Started](Getting-Started.md#linux-with-the-gui).

### `blueprint-compiler` cannot be run or fails

- **Cause:** `window.ui` is missing or older than `window.blp`, and the compiler is missing or errors. `ensure_ui` raises `RuntimeError` with install hints (`Cannot run 'blueprint-compiler' to compile window.blp. Install blueprint-compiler ...` or `... failed with exit code N`); the entry point reports it as `GUI is not available` with exit code 1.
- **Fix:** install `blueprint-compiler`, or set `BLUEPRINT_COMPILER` to the executable.
- *Not verified on this machine.*

## Tests

### Coverage below 85 % fails the run

- **Cause:** `pytest.ini` has `--cov-fail-under=85`. Running only a subset of the tests can drop the total below the gate; add `--no-cov` for a quick subset run.

### GUI tests are skipped

- **Cause:** they need GTK4, libadwaita, a usable `window.ui` and a display. On this machine the skip reason is `GTK4/libadwaita not available: No module named 'gi'`. See [Testing](Testing.md#gui-tests-and-skipping).

### The `serial` and `slow` markers select nothing

- **Cause:** both markers are registered in `pytest.ini`, but no test uses them today (checked by searching `tests/`). Only `gui` is used.

## See also

- [Getting-Started](Getting-Started.md)
- [Animation-Format](Animation-Format.md)
- [Serial-Protocol](Serial-Protocol.md)
- [Testing](Testing.md)
