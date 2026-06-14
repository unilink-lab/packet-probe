# Packet Probe Viewer

Packet Probe Viewer is an optional read-only viewer for Packet Probe event streams.

The viewer subscribes to Packet Probe's UDS IPC stream and displays
JSONL events in a table, hex view, and detail panel.

## Install

The viewer depends on PySide6. Live IPC stream subscription also requires `unilink-python` to be installed.

For local development with sibling repositories, we recommend a local install of `unilink-python`:

```sh
python -m pip install -e ../unilink-python \
  -Ccmake.define.UNILINK_CORE_SOURCE_DIR=../unilink

cd viewer
python -m pip install -e .
```

*Note: In the final packaged standalone executable distributions, the `unilink-python` native extension will be bundled automatically.*

## Run

```sh
packet-probe-viewer --socket /tmp/packet-probe.sock
```

## Test

```sh
cd viewer
python -m pip install -e ".[test]"
python -m pytest
```

## Connect to an existing Packet Probe process

Use this when `packet-probe` is already running with `--ipc`.

```sh
packet-probe udp --bind-host 127.0.0.1 --bind-port 19000 --ipc /tmp/packet-probe.sock
packet-probe-viewer --socket /tmp/packet-probe.sock
```

## Launch Packet Probe from the viewer

Use this when you want the viewer to start `packet-probe` for you.

Do not include `--ipc` or `--ipc=` in the args field. The viewer generates and appends it automatically.

1. Set `CLI Path` to the `packet-probe` executable.
2. Enter capture arguments.
3. Click `Start Capture`.

Example args:

```text
udp --bind-host 127.0.0.1 --bind-port 19000 --log udp.jsonl
```

## Open a JSONL log

The viewer can open Packet Probe JSONL logs recorded with `--log`.

```sh
packet-probe udp \
  --bind-host 127.0.0.1 \
  --bind-port 19000 \
  --log udp.jsonl
```

Then open `udp.jsonl` from the viewer using:

```text
File > Open Log...
```

or the `Open Log` button.

## UI Layout

Packet Probe Viewer follows a compact desktop communication-tool layout.

- Top controls: CLI path, capture arguments, IPC socket, and action buttons
- Center view: live or offline event table
- Bottom tabs: Hex, JSON detail, and Process Log

## Limitations

- read-only viewer
- no command send
- no replay
- Unix Domain Socket IPC only for now
- viewer currently keeps events in memory
- very large captures should be recorded as JSONL and analyzed separately
