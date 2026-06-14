# Packet Probe

Packet Probe is a lightweight device communication analyzer for inspecting,
recording, and decoding packets, frames, and messages over TCP, UDP, Serial, and UDS.

It is not an OS-level packet sniffer. Packet Probe focuses on application/device-level
communication sessions with connected equipment.

## Overview

Packet Probe connects to known device communication sessions and records the raw bytes
exchanged with target equipment. MVP-1 starts with TCP Direct Mode through a CLI named
`packet-probe`.

The core model records timestamp, direction, size, payload, transport, and session
metadata as `PacketEvent` values. Events can be printed as one-line hex output and
written as JSONL for later viewer support.

## Scope

MVP-1 includes:

- TCP Direct Mode CLI
- raw RX/TX byte events
- StateChange and Error events
- one-line hex output
- JSONL recording
- CTest-based unit tests for hex and JSONL behavior

## What Packet Probe is not

Packet Probe does not capture arbitrary OS-level network traffic like Wireshark or tcpdump.
It connects to known device communication sessions and analyzes the data exchanged through them.

Packet Probe does not use libpcap, Npcap, raw sockets, or promiscuous network capture.

## MVP status

Implemented:

- `packet-probe tcp-client`
- `PacketEvent`
- `CaptureSession`
- `TcpDirectCaptureSession`
- `JsonlRecorder`
- basic docs and tests

Not implemented yet:

- PyQt viewer
- UDS IPC
- TCP Proxy Mode
- UDP, Serial, or UDS capture modes
- decoder plugin system

## Build

By default, CMake looks for a sibling unilink source tree at `../unilink`.
If that path does not exist, it falls back to `find_package(unilink CONFIG REQUIRED)`.

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

Parallel build:

```sh
cmake --build build -j2
```

## Usage

```sh
packet-probe --help
packet-probe --version
packet-probe tcp-client --host 127.0.0.1 --port 9000
packet-probe tcp-client --host 127.0.0.1 --port 9000 --hex
packet-probe tcp-client --host 127.0.0.1 --port 9000 --log capture.jsonl --hex
```

In `tcp-client` mode, lines typed on stdin are sent to the target as raw bytes and
recorded as TX events. Bytes received from the target are recorded as RX events.

JSONL event example:

```json
{"seq":1,"time_ns":1781234567890,"session":"tcp-client-1","transport":"tcp","direction":"rx","type":"raw_bytes","size":6,"payload_hex":"0210010003A7","summary":"RX 6 bytes"}
```

## Roadmap

See [docs/roadmap.md](docs/roadmap.md).
