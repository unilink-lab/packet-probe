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

The current MVP is CLI-only. It records communication events from direct TCP, UDP,
and Serial sessions or TCP proxy sessions and writes them to stdout and optional
JSONL logs.

TCP Proxy Mode:

```text
[Existing App]
      |
      | TCP
      v
[Packet Probe TCP Proxy]
      |
      | TCP
      v
[Target Device]
```

Core responsibilities:

- define stable `PacketEvent` data
- record timestamp, direction, transport, size, payload, and summary
- record source and destination endpoints when proxying
- provide heuristic latency events for request/response-style traffic
- derive frame events from raw payloads through a transport-independent decoder pipeline
- keep capture, recorder, decoder, and future IPC layers separable

Capture responsibilities:

- connect to a known device communication session
- convert transport callbacks into `PacketEvent` values
- keep transport-specific code out of the core event model

Recorder responsibilities:

- serialize each event as one JSON object per line
- preserve a stable log format that a future viewer can load

Decoder pipeline:

```text
Raw Bytes
  -> Frame
    -> Future: Decoded Message
```

Raw byte events preserve the original transport payload. Frame events are derived
from raw byte events and use `parent_seq` to refer back to the source event.

Latency tracking:

- app_to_device raw byte events are treated as request candidates
- the next device_to_app raw byte event is paired as the response
- the emitted latency event records request sequence, response sequence, and elapsed time

Without a protocol decoder, request/response pairing is heuristic-based. Protocol-specific
decoders are expected to provide accurate pairing later.

Future viewer integration should happen through an IPC boundary, not by mixing PyQt
code into the core library.

UDS capture mode and UDS IPC are separate features. UDS capture mode analyzes Unix
Domain Socket communication sessions. UDS IPC is planned as an internal local
communication channel between Packet Probe Core and a future viewer.
