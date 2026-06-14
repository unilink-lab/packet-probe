# Viewer IPC Validation

## Purpose

Validate that Packet Probe Viewer can connect to a Packet Probe IPC event stream
and display events.

## Requirements

- Python 3.10+
- PySide6
- unilink-python (with unilink core runtime libraries)
- Built `packet-probe`

Packet Probe Viewer uses `unilink-python` `UdsClient` for live IPC connections.

## Install viewer

```sh
cd viewer
python -m pip install -e .
```

## Start Packet Probe

```sh
packet-probe udp \
  --bind-host 127.0.0.1 \
  --bind-port 19000 \
  --ipc /tmp/packet-probe.sock \
  --log udp.jsonl
```

## Start viewer

```sh
packet-probe-viewer --socket /tmp/packet-probe.sock
```

## Send test UDP datagram

```sh
python3 - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(bytes.fromhex("02 10 01 00 03 A7"), ("127.0.0.1", 19000))
PY
```

## Expected result

* Viewer status changes to connected.
* Event table shows a `device_to_app` raw_bytes event.
* Selecting the row shows payload hex.
* Event detail panel shows raw JSON.

## Additional checks

- Start the viewer before Packet Probe and click Connect. The viewer should show a connection error and remain usable.
- Start Packet Probe, connect the viewer, then stop Packet Probe. The viewer should switch to disconnected state.
- Click Pause, send datagrams, then click Resume. Buffered events should appear.
- Click Clear. The table, hex view, and detail view should be cleared.
- Try connecting to a missing socket path repeatedly. The viewer should show connection errors and remain usable.
- Connect to a running Packet Probe IPC socket, click Disconnect, then Connect again. The viewer should reconnect without restarting.
- Close the viewer window while connected. The window should close without hanging.

## Launcher validation

Start `packet-probe-viewer`, enter:

```text
udp --bind-host 127.0.0.1 --bind-port 19000 --log udp.jsonl
```

Click `Start Capture`.

Expected:

* process output is visible
* viewer connects automatically
* UDP events appear in the table
* Stop Capture terminates the process
