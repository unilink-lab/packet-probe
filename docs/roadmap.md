# Roadmap

This roadmap describes planned improvements for Packet Probe. It is not a release
history.

## Current Capabilities

- TCP Direct Mode
- TCP Server Direct Mode
- TCP Proxy Mode
- Serial Direct Mode
- UDP Direct Mode
- JSONL recording
- UDS IPC event stream
- Frame decoders
- Common send input
- Public/internal header separation

## Near-Term Work

- PyQt read-only viewer
- Viewer connection to UDS IPC event stream
- Basic packet table
- Raw payload hex view
- Frame event display
- JSONL log open/read support

## Core Stabilization

- Improve IPC backpressure handling
- Add non-blocking IPC writes or per-client queues
- Add drop counters for slow IPC clients
- Add more manual validation smoke tests
- Add Windows CI/build validation where practical

## Protocol Analysis

- Protocol-specific message decoder examples
- DecodedMessage event generation
- Decoder error reporting improvements
- Decoder configuration presets

## Replay and Offline Analysis

- JSONL replay
- Replay as event stream
- Replay into future viewer
- Time-scaling or step-through replay

## Plugin and Schema Support

- External decoder plugin interface
- Protocol schema support
- Device-specific decoder packages

## Later / Optional

- UDS capture mode
- TCP loopback or named-pipe IPC for Windows
- Multi-client TCP server mode
- TCP server send-on-connect support
- Viewer command channel
- Capture start/stop control from viewer
