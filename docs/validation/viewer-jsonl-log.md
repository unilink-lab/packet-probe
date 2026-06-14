# Viewer JSONL Log Validation

## Purpose

Validate that Packet Probe Viewer can open a saved JSONL log and display events.

## Generate log

```sh
packet-probe udp \
  --bind-host 127.0.0.1 \
  --bind-port 19000 \
  --log udp.jsonl
```

Send test datagram:

```sh
python3 - <<'PY'
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.sendto(bytes.fromhex("02 10 01 00 03 A7"), ("127.0.0.1", 19000))
PY
```

Stop Packet Probe.

## Open log

```sh
packet-probe-viewer
```

Then open:

```text
File > Open Log...
```

Select `udp.jsonl`.

## Expected result

* Viewer status changes to `offline log`.
* Event table shows recorded events.
* Selecting an event shows payload hex.
* Event detail panel shows raw JSON.
