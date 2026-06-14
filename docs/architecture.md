# Architecture

Packet Probe is organized around a transport-independent event model.

```text
[Target Device]
      |
 TCP / UDP / Serial / UDS
      |
[Packet Probe Core]
      |
 Future: UDS IPC
      |
[Viewer]
```

The current MVP is CLI-only. It records communication events from a direct TCP client
session and writes them to stdout and optional JSONL logs.

Core responsibilities:

- define stable `PacketEvent` data
- record timestamp, direction, transport, size, payload, and summary
- keep capture, recorder, decoder, and future IPC layers separable

Capture responsibilities:

- connect to a known device communication session
- convert transport callbacks into `PacketEvent` values
- keep transport-specific code out of the core event model

Recorder responsibilities:

- serialize each event as one JSON object per line
- preserve a stable log format that a future viewer can load

Future viewer integration should happen through an IPC boundary, not by mixing PyQt
code into the core library.
