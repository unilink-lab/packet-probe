# Roadmap

## MVP-1

- TCP Direct CLI
- raw byte capture
- hex output
- JSONL recording

## MVP-2

- TCP Proxy Mode
- bidirectional forwarding
- app_to_device / device_to_app event direction
- heuristic request/response latency tracking

## MVP-3

- Serial Direct Mode
- serial port configuration
- serial RX/TX raw byte capture
- serial JSONL recording

## MVP-4

- UDP Direct Mode
- datagram event model
- UDP endpoint metadata
- UDP JSONL recording

## MVP-5

- FrameDecoder interface
- raw/fixed/delimiter/length-prefix frame decoders
- frame PacketEvent
- EventPipeline

## MVP-6

- common send input format
- --send-text
- --send-hex
- --send-file
- CLI structure cleanup

## MVP-7

- UDS IPC
- core event stream server
- viewer protocol draft

## MVP-8

- PyQt read-only viewer

## MVP-9

- replay
- protocol-specific decoder
- decoder plugin
- protocol schema support
