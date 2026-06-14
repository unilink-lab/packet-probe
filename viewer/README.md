# Packet Probe Viewer

Packet Probe Viewer is an optional read-only viewer for Packet Probe event streams.

The viewer is planned to subscribe to Packet Probe's UDS IPC stream and display
JSONL events in a table, hex view, and detail panel.

## Status

The viewer is not implemented yet. This directory currently defines the planned
packaging and dependency boundary.

## License

The viewer source code is licensed under Apache-2.0.

The viewer depends on PySide6 / Qt for Python as an external runtime dependency.
PySide6 and Qt are not vendored in this repository and are distributed under their
own license terms.

See:

- `LICENSE`
- `THIRD_PARTY_NOTICES.md`

## Planned features

- Connect to Packet Probe UDS IPC event stream
- Display packet/event table
- Show raw payload hex
- Show event detail JSON
- Pause/resume live updates
- Reconnect to IPC socket

## Out of scope for initial viewer

- Sending commands to devices
- Starting/stopping capture
- Decoder plugin management
- Replay editing
