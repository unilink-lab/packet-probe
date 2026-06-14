# JSONL Format

Packet Probe writes newline-delimited JSON. A log file starts with one metadata
line, followed by event lines.

## Metadata

```json
{"type":"metadata","schema":"packet-probe.log.v1","event_schema":"packet-probe.event.v1","tool":"packet-probe","version":"0.1.0"}
```

The metadata line is not a `PacketEvent`.

## Event Schema

Event lines use `packet-probe.event.v1`.

Common fields:

- `seq`: event sequence number
- `parent_seq`: source event sequence for derived events, always present
- `time_ns`: wall-clock timestamp in nanoseconds since Unix epoch
- `session`: capture session id
- `transport`: `tcp`, `udp`, `serial`, or future transport name
- `direction`: communication-flow direction such as `app_to_device` or `device_to_app`
- `type`: event type such as `raw_bytes`, `frame`, `latency`, `error`, or `state_change`
- `source`: optional source endpoint
- `destination`: optional destination endpoint
- `size`: payload size in bytes
- `payload_hex`: uppercase compact hex string, empty when payload is empty
- `summary`: human-readable event summary
- `decoded`: optional decoded JSON object for future message decoders

Latency fields:

- `request_seq`
- `response_seq`
- `latency_ns`
- `latency_us`
- `request_size`
- `response_size`

## Sequence Policy

- `seq` is used for file-local event ordering.
- `parent_seq` links derived frame, decoded, or decoder error events to their source event.
- Raw transport events use `parent_seq: 0`.
- Frame events use the source raw event sequence as `parent_seq`.
- Current derived events use a separate high sequence range starting at `1000000000000`
  to avoid collisions with capture-session raw event sequences.
- Future work may replace this with a shared `SequenceAllocator` across capture sessions
  and the event pipeline.
