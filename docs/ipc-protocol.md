# IPC Protocol

Packet Probe implements a read-only IPC event stream for future viewer
integration. The IPC stream lets a viewer subscribe to the same event JSONL used
by file recording without mixing UI code into capture, recorder, or decoder
libraries.

## UDS Capture Mode vs UDS IPC

UDS capture mode and UDS IPC are separate features.

- UDS Capture Mode analyzes Unix Domain Socket communication sessions as a
  transport.
- UDS IPC is an internal local communication channel between Packet Probe Core
  and a future viewer.

UDS capture mode is not implemented yet. UDS IPC event streaming is implemented
for Unix-like systems.

## Transport

The MVP transport is Unix Domain Socket with `SOCK_STREAM`.

UDS IPC is currently supported on Unix-like systems. Windows viewer integration
may use TCP loopback or named pipes in a future version.

## CLI Usage

Use `--ipc <path>` with any capture mode:

```sh
packet-probe udp \
  --bind-host 127.0.0.1 \
  --bind-port 19000 \
  --ipc /tmp/packet-probe.sock \
  --log udp.jsonl
```

`--ipc`, `--log`, `--hex`, and `--hex-frame` are independent. A capture can write
JSONL to disk and broadcast the same events to IPC clients at the same time.

## Protocol

The MVP protocol is JSONL over a stream socket.

- Message boundary: newline-delimited JSON
- Encoding: UTF-8 JSON lines
- Log metadata schema: `packet-probe.log.v1`
- Event schema: `packet-probe.event.v1`

Each client receives a metadata line immediately after connecting:

```json
{"type":"metadata","schema":"packet-probe.log.v1","event_schema":"packet-probe.event.v1","tool":"packet-probe","version":"0.1.0"}
```

After metadata, each captured event is sent as one JSON line using the same event
schema as JSONL log files.

Core to viewer messages:

- metadata
- raw packet event
- frame event
- latency event
- error event
- state event

Viewer to core messages:

- none in the MVP IPC protocol

## Multi-Client Behavior

Multiple viewer clients can connect to the same socket.

- Each client receives metadata on connection.
- Events are broadcast to all currently connected clients.
- If a client disconnects or a write fails, only that client is removed.
- Client failures do not stop capture, recording, or other IPC clients.

## Socket Lifecycle

When IPC starts:

- the parent directory must exist
- a stale socket at the same path is removed
- a directory or non-socket file at the path is treated as an error

When Packet Probe stops:

- the server socket is closed
- connected client sockets are closed
- the socket path is unlinked

## Read-Only Viewer Policy

The first viewer integration is read-only. Viewer command send, capture
start/stop control, filter subscription, snapshot request, and mutation APIs are
out of scope for the MVP IPC protocol. The CLI or daemon starts capture, and the
viewer subscribes to the event stream.

## Reconnect Policy

The viewer should tolerate disconnects and reconnect to the IPC socket. On
reconnect, the core sends a fresh metadata line before new event lines.

## Future Extensions

- viewer command channel
- capture start/stop
- filter subscription
- snapshot request
- log replay stream
