# Capture Modes

Packet Probe supports direct capture modes and proxy capture modes.

## Direct Modes

Direct modes connect Packet Probe directly to one communication endpoint.

Implemented direct modes:

- TCP client
- TCP server
- Serial
- UDP

## Proxy Modes

Proxy modes place Packet Probe between an existing application and a target device.

Implemented proxy modes:

- TCP proxy

Not implemented yet:

- Serial proxy
- UDP proxy

## Hook Mode

Hook mode is a possible future integration pattern where an application emits
communication events to Packet Probe without changing the communication path.

Hook mode is not implemented yet.

## Engine Mode

```sh
packet-probe engine --ipc <path>
```

Engine mode starts Packet Probe idle, with no capture session running, and waits
for IPC control commands on `<path>`: `configure`, `start_capture`, `stop_capture`,
`get_status`, `list_serial_ports`, and `send`. See [ipc-protocol.md](ipc-protocol.md)
for the full command/result/status message schema.

Unlike the direct/proxy modes above, engine mode is a long-lived process: a viewer
can change capture settings and restart a capture session over IPC without
restarting the `packet-probe` process itself. The five direct/proxy modes remain
unchanged and are unaffected by engine mode's existence — they still take their
capture configuration from argv and run a single session for the life of the
process.
