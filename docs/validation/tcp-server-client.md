# TCP Server Validation

## Purpose

Validate TCP Server Direct Mode by connecting a test TCP client to Packet Probe.

## Requirements

- Python 3
- Built packet-probe

## Packet Probe command

```bash
packet-probe tcp-server \
  --listen-host 127.0.0.1 \
  --listen-port 19000 \
  --log tcp-server.jsonl \
  --hex
```

## Test client

```bash
python3 -u -c 'import socket
s=socket.create_connection(("127.0.0.1", 19000))
s.sendall(bytes.fromhex("02 10 01 00 03 A7"))
print(s.recv(4096).hex())
'
```

## Expected stdout

```text
DEVICE -> APP ...
APP -> DEVICE ...
```

## Expected JSONL

- metadata line
- device_to_app raw_bytes event
- app_to_device raw_bytes event if stdin/send input is used

## Response Transmission Validation

```bash
echo "02 90 00 91" | packet-probe tcp-server \
  --listen-host 127.0.0.1 \
  --listen-port 19000 \
  --send-hex \
  --log tcp-server.jsonl \
  --hex
```

Verify receipt of response on the client side after connecting from another terminal.
