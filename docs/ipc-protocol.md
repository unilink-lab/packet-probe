# IPC Protocol

Packet Probe implements a bidirectional IPC channel between the CLI and the
viewer. The IPC stream lets a viewer subscribe to the same event JSONL used by
file recording and send commands back to the CLI — without mixing UI code into
capture, recorder, or decoder libraries.

## UDS Capture Mode vs UDS IPC

UDS capture mode and UDS IPC are separate features.

- UDS Capture Mode analyzes Unix Domain Socket communication sessions as a
  transport.
- UDS IPC is an internal local communication channel between Packet Probe Core
  and a future viewer.

UDS capture mode is not implemented yet. UDS IPC event streaming is implemented
using the unilink UDS transport.

## Transport

Packet Probe IPC uses the unilink UDS transport.

The protocol is newline-delimited JSON over a local byte stream. Each viewer
client receives one metadata line on connection, followed by event JSON lines.

Windows support depends on the underlying unilink UDS implementation and OS
support. TCP loopback or named pipes may be considered later only if UDS support
is insufficient for packaged applications.

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

The protocol is JSONL over a stream socket. Both directions use newline-delimited JSON.

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

### Core to viewer messages

- metadata
- raw packet event
- frame event
- latency event
- error event
- state event

### Viewer to core messages

#### send

Sends a payload to the connected device. Supported in tcp-client, tcp-server, serial, and udp modes. Not supported in tcp-proxy mode.

```json
{"type":"command","command":"send","payload_hex":"AABBCC"}
```

- `payload_hex`: hex-encoded bytes to send (no spaces, separators, or `0x` prefix)
- The CLI decodes the hex payload and calls the session's `send()` method
- If decoding fails or the session has no send method, the command is silently ignored

## Multi-Client Behavior

Multiple viewer clients can connect to the same socket.

- Each client receives metadata on connection.
- Events are broadcast to all currently connected clients.
- If a client disconnects or a write fails, only that client is removed.
- Client failures do not stop capture, recording, or other IPC clients.

## Backpressure and Slow Clients

The current IPC implementation uses synchronous broadcast to connected clients.

This keeps the implementation simple, but a slow or blocked viewer client may delay
event broadcast. Packet Probe removes clients when socket writes fail, but it does
not yet use non-blocking sockets, per-client queues, or writer threads.

Future versions may add:

- non-blocking socket writes
- per-client bounded queues
- drop counters for slow clients
- viewer-side flow control

## Socket Lifecycle

When IPC starts:

- the parent directory must exist
- a stale socket at the same path is removed
- a directory or non-socket file at the path is treated as an error

When Packet Probe stops:

- the server socket is closed
- connected client sockets are closed
- the socket path is unlinked

## Viewer Policy

The CLI starts capture. The viewer subscribes to events and can send commands
back over the same socket. Capture start/stop control, filter subscription,
snapshot requests, and mutation APIs remain out of scope.

## Reconnect Policy

The viewer should tolerate disconnects and reconnect to the IPC socket. On
reconnect, the core sends a fresh metadata line before new event lines.

## Future Extensions

- capture start/stop control
- filter subscription
- snapshot request
- log replay stream
