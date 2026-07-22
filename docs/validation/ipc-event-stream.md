# IPC Event Stream Validation

## Purpose

Validate that Packet Probe can expose captured events to a read-only viewer over
Unix Domain Socket IPC using JSONL message boundaries.

## Requirements

- Linux, macOS, or Windows
- `packet-probe` built locally
- Connection tool (`socat` for Linux/macOS, or Python/other UDS client for Windows)

## Setup

Start Packet Probe with UDP capture and IPC enabled:

### Linux/macOS:

```sh
packet-probe udp \
  --bind-host 127.0.0.1 \
  --bind-port 19000 \
  --ipc /tmp/packet-probe.sock \
  --log udp.jsonl
```

### Windows:

```powershell
packet-probe udp `
  --bind-host 127.0.0.1 `
  --bind-port 19000 `
  --ipc .\packet-probe.sock `
  --log udp.jsonl
```

## Windows Note

IPC is implemented through the wirestead UDS transport. On Windows, use a short socket path in a writable local directory when validating packaged or command-line builds.

## Connect A Viewer Client

In another terminal, connect with `socat`:

```sh
socat - UNIX-CONNECT:/tmp/packet-probe.sock
```

## Expected Metadata

The client should immediately receive one metadata line:

```json
{"type":"metadata","schema":"packet-probe.log.v1","event_schema":"packet-probe.event.v1","tool":"packet-probe","version":"0.1.0"}
```

## Generate Traffic

Send a UDP datagram to Packet Probe:

```sh
printf "hello" | nc -u -w1 127.0.0.1 19000
```

## Expected Event Line

The IPC client should receive a JSONL event after the datagram is captured. The
exact timestamp, sequence, and endpoint port values will vary.

```json
{"seq":1,"parent_seq":0,"time_ns":1781234567890,"session":"udp-1","transport":"udp","direction":"device_to_app","source":"127.0.0.1:53124","destination":"127.0.0.1:19000","type":"raw_bytes","size":5,"payload_hex":"68656C6C6F","summary":"DEVICE -> APP 5 bytes"}
```

## Disconnect And Reconnect

Stop the `socat` client with `Ctrl-C`, then reconnect:

```sh
socat - UNIX-CONNECT:/tmp/packet-probe.sock
```

The reconnected client should receive a fresh metadata line. Packet Probe should
continue capturing while clients disconnect and reconnect.

## Troubleshooting

- If the socket file is missing, confirm Packet Probe is still running and that
  `--ipc` points to the expected path.
- If startup fails, confirm the parent directory exists and the socket path is
  not a directory or regular file.
- If no event arrives, confirm traffic is sent to the configured bind host and
  bind port.
- UDS IPC platform support follows the underlying wirestead core and OS UDS/AF_UNIX support.
