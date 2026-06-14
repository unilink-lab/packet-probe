# Packet Probe Viewer

Packet Probe Viewer is an optional read-only viewer for Packet Probe event streams.

The viewer subscribes to Packet Probe's UDS IPC stream and displays
JSONL events in a table, hex view, and detail panel.

## Install

```sh
cd viewer
python -m pip install -e .
```

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

## Example with Packet Probe

Terminal 1:

```sh
packet-probe udp \
  --bind-host 127.0.0.1 \
  --bind-port 19000 \
  --ipc /tmp/packet-probe.sock \
  --log udp.jsonl
```

Terminal 2:

```sh
packet-probe-viewer --socket /tmp/packet-probe.sock
```

Terminal 3:

```sh
python3 - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(b"hello", ("127.0.0.1", 19000))
PY
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

## Limitations

- read-only viewer
- no command send
- no capture start/stop
- no replay
- Unix Domain Socket IPC only for now
- viewer currently keeps events in memory
- very large captures should be recorded as JSONL and analyzed separately
