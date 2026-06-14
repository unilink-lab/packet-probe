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

MVP-2 adds:

- TCP Proxy Mode
- bidirectional forwarding
- app_to_device and device_to_app event directions
- source and destination endpoint metadata
- heuristic request/response latency events

## What Packet Probe is not

Packet Probe does not capture arbitrary OS-level network traffic like Wireshark or tcpdump.
It connects to known device communication sessions and analyzes the data exchanged through them.

Packet Probe does not use libpcap, Npcap, raw sockets, or promiscuous network capture.

## MVP status

Implemented:

- `packet-probe tcp-client`
- `packet-probe tcp-proxy`
- `PacketEvent`
- `CaptureSession`
- `TcpDirectCaptureSession`
- `TcpProxyCaptureSession`
- `JsonlRecorder`
- basic docs and tests

Not implemented yet:

- PyQt viewer
- UDS IPC
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
{"seq":1,"time_ns":1781234567890,"session":"tcp-client-1","transport":"tcp","direction":"device_to_app","type":"raw_bytes","size":6,"payload_hex":"0210010003A7","summary":"RX 6 bytes"}
```

## TCP Proxy Mode

TCP Proxy Mode places Packet Probe between an existing application and a target device.

```text
[Existing App] -> [Packet Probe] -> [Target Device]
```

Example:

```sh
packet-probe tcp-proxy \
  --listen-host 127.0.0.1 \
  --listen-port 9000 \
  --target-host 192.168.0.10 \
  --target-port 9000 \
  --log capture.jsonl \
  --hex \
  --latency
```

This mode is useful when you want to inspect the actual communication flow between
an existing application and connected equipment.

Proxy events use communication-flow directions:

- `app_to_device`: bytes forwarded from the existing app to the target device
- `device_to_app`: bytes forwarded from the target device back to the existing app

Without a protocol decoder, request/response pairing is heuristic-based.
For accurate pairing, protocol-specific decoder support will be added later.

Manual validation:

```sh
packet-probe tcp-proxy \
  --listen-host 127.0.0.1 \
  --listen-port 9000 \
  --target-host 127.0.0.1 \
  --target-port 9100 \
  --log proxy.jsonl \
  --hex
```

Then connect a test client to `127.0.0.1:9000` while a target echo server is
listening on `127.0.0.1:9100`.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md).
