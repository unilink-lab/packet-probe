# Capture Modes

## 1. Direct Mode

Packet Probe connects directly to a target device.

MVP-1 implements Direct Mode for TCP client sessions only.

## 2. Proxy Mode

Packet Probe sits between an existing application and a target device.

Proxy Mode is implemented for TCP in MVP-2.
UDP and Serial proxy modes are not implemented yet.

## 3. Hook Mode

An application emits communication events to Packet Probe.

This mode is not implemented in MVP-1.
