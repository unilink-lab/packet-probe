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
