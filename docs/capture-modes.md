# Capture Modes

## 1. Direct Mode

Packet Probe connects directly to a target device.

Direct Mode is implemented for:

- TCP client sessions
- Serial sessions
- UDP datagram sessions

## 2. Proxy Mode

Packet Probe sits between an existing application and a target device.

Proxy Mode is implemented for TCP in MVP-2.
Serial proxy mode is not implemented yet.
UDP proxy mode is not implemented yet.

## 3. Hook Mode

An application emits communication events to Packet Probe.

This mode is not implemented in MVP-1.
