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

## Existing socket validation

### Steps

1. Start Packet Probe manually:

   ```sh
   packet-probe udp \
     --bind-host 127.0.0.1 \
     --bind-port 19000 \
     --ipc /tmp/packet-probe.sock \
     --log udp.jsonl
   ```

2. Start the viewer:

   ```sh
   packet-probe-viewer --socket /tmp/packet-probe.sock
   ```

3. Send a test UDP datagram:

   ```sh
   python3 - <<'PY'
   import socket
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.sendto(bytes.fromhex("02 10 01 00 03 A7"), ("127.0.0.1", 19000))
   PY
   ```

### Expected results

* The socket path field displays `/tmp/packet-probe.sock` without being overwritten by an auto-generated path.
* Viewer status changes to connected.
* Event table shows a `device_to_app` raw_bytes event.
* Selecting the row updates the Hex tab and JSON tab.

### Additional checks

- Start the viewer before Packet Probe and click Connect. The viewer should show a connection error and remain usable.
- Start Packet Probe, connect the viewer, then stop Packet Probe. The viewer should switch to disconnected state.
- Click Pause, send datagrams, then click Resume. Buffered events should appear.
- Click Clear. The table, hex view, and detail view should be cleared.
- Try connecting to a missing socket path repeatedly. The viewer should show connection errors and remain usable.
- Connect to a running Packet Probe IPC socket, click Disconnect, then Connect again. The viewer should reconnect without restarting.
- Close the viewer window while connected. The window should close without hanging.

## Send command validation

### Steps

1. Start Packet Probe in tcp-client mode with IPC:

   ```sh
   packet-probe tcp-client \
     --host 127.0.0.1 \
     --port 19100 \
     --ipc /tmp/packet-probe.sock \
     --log tcp.jsonl
   ```

   (Start a TCP echo server on port 19100 first, e.g. `ncat -l 19100 -k`.)

2. Start the viewer:

   ```sh
   packet-probe-viewer --socket /tmp/packet-probe.sock
   ```

3. Enter a hex payload in the Send Message panel, e.g. `AABBCC`.
4. Click `Send`.

### Expected results

* The CLI receives the hex payload and sends it to the connected TCP server.
* A `app_to_device` raw_bytes event appears in the viewer event table.
* The Hex tab and JSON tab update when the event row is selected.
* No errors appear in the Process Log.

### Additional checks

- Try sending from an unsupported mode (tcp-proxy). The send panel should be disabled or the command silently ignored.
- Send while disconnected from IPC. The viewer should show no error and not hang.

## Launcher validation

### Steps

1. Start the viewer without any argument:

   ```sh
   packet-probe-viewer
   ```

2. Set CLI Path to the built `packet-probe` executable.
3. Enter capture arguments:

   ```text
   udp --bind-host 127.0.0.1 --bind-port 19000 --log udp.jsonl
   ```

4. Click `Start Capture`.
5. Send a test UDP datagram:

   ```sh
   python3 - <<'PY'
   import socket
   s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   s.sendto(bytes.fromhex("02 10 01 00 03 A7"), ("127.0.0.1", 19000))
   PY
   ```

### Expected results

* When clicking `Start Capture`, the viewer generates an IPC socket path and updates the Socket Path field.
* Process output from the CLI process appears in the Process Log tab (without empty `[stdout]` or `[stderr]` prefixes).
* The viewer automatically attempts to connect to the generated IPC socket and succeeds (using the retry loop).
* UDP events appear in the table.
* Selecting an event updates the Hex tab and JSON tab.
* Clicking `Stop Capture` terminates the process.

### Additional checks

- Stop Capture: Verify that capture retries are halted immediately when `Stop Capture` is clicked or the process stops.
- Start Failure: Try to start capture with an invalid executable path. Verify that UI controls (e.g. Start Capture button) are properly restored when the process fails to start.
- IPC Argument rejection: Try to include `--ipc` or `--ipc=value` in the capture arguments. Verify that the viewer displays a warning dialog and refuses to start the capture.

