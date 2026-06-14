# Header Structure

Packet Probe separates public API headers from internal implementation headers.

## Public Headers

Public headers live under `include/packet_probe/` and describe the small API
surface that may be shared with external tools, viewers, replay utilities, and
future decoder plugins.

Current public headers:

- `packet_probe/packet_probe.hpp`
- `packet_probe/version.hpp`
- `packet_probe/core/packet_event.hpp`
- `packet_probe/core/jsonl_serializer.hpp`
- `packet_probe/decoder/decoder_config.hpp`
- `packet_probe/decoder/frame_decode_result.hpp`
- `packet_probe/decoder/frame_decoder.hpp`
- `packet_probe/decoder/message_decoder.hpp`
- `packet_probe/ipc/ipc_protocol.hpp`

## Internal Headers

Internal headers live under `src/` and are not part of the supported public C++
API. They are available to Packet Probe's own libraries, CLI, and tests through
private CMake include paths.

Internal areas include:

- capture sessions
- recorder implementation
- IPC server implementation
- event pipeline
- send input parsing
- CLI helpers
- internal utility helpers such as hex dump, endpoint formatting, and latency tracking

## Why Capture Sessions Are Internal

Packet Probe's external integration path is IPC/JSONL, not direct C++ embedding.
A future viewer should subscribe to the UDS IPC event stream instead of including
capture session classes directly.

The optional viewer is expected to integrate through the IPC JSONL event stream
instead of directly including internal C++ capture headers.

## Future

If Packet Probe later becomes a C++ SDK, selected internal headers may be
promoted to public API deliberately. Until then, `include/packet_probe/` remains
small by design.
