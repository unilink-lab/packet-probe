# IPC Protocol Draft

This document defines the initial direction for future Packet Probe viewer IPC.
It is a draft only; UDS IPC is not implemented yet.

## Purpose

UDS IPC will let a future viewer subscribe to Packet Probe Core events without
mixing UI code into the capture, recorder, or decoder libraries.

## UDS Capture Mode vs UDS IPC

UDS capture mode and UDS IPC are separate features.

- UDS Capture Mode analyzes Unix Domain Socket communication sessions as a transport.
- UDS IPC is an internal local communication channel between Packet Probe Core and
  a future viewer.

## Transport

The planned transport is Unix Domain Socket.

## MVP Protocol

The initial protocol is JSONL over a stream socket.

- Message boundary: newline-delimited JSON
- Log metadata schema: `packet-probe.log.v1`
- Event schema: `packet-probe.event.v1`

Core to viewer messages:

- metadata
- raw packet event
- frame event
- latency event
- error event
- state event

Viewer to core messages:

- none in the MVP IPC protocol

## Read-Only Viewer Policy

The first viewer integration should be read-only. Viewer command send, capture
start/stop control, and mutation APIs are out of scope for the initial IPC protocol.
The CLI or daemon starts capture, and the viewer subscribes to the event stream.

## Reconnect Policy

The viewer should tolerate disconnects and reconnect to the IPC socket. On reconnect,
the core should send a fresh metadata line before new event lines.

## Future Extensions

- viewer command channel
- capture start/stop
- filter subscription
- snapshot request
- log replay stream
