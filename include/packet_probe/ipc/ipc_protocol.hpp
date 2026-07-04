#pragma once

namespace packet_probe {

inline constexpr char kPacketProbeLogSchema[] = "packet-probe.log.v1";
inline constexpr char kPacketProbeEventSchema[] = "packet-probe.event.v1";

// IPC control protocol v2 message types (viewer <-> core).
inline constexpr char kIpcMessageTypeCommand[] = "command";
inline constexpr char kIpcMessageTypeResult[] = "result";
inline constexpr char kIpcMessageTypeStatus[] = "status";

// IPC control protocol v2 command names (viewer -> core).
inline constexpr char kIpcCommandConfigure[] = "configure";
inline constexpr char kIpcCommandStartCapture[] = "start_capture";
inline constexpr char kIpcCommandStopCapture[] = "stop_capture";
inline constexpr char kIpcCommandGetStatus[] = "get_status";
inline constexpr char kIpcCommandListSerialPorts[] = "list_serial_ports";
inline constexpr char kIpcCommandSend[] = "send";

// Engine state values reported in "status" messages.
inline constexpr char kEngineStateIdle[] = "idle";
inline constexpr char kEngineStateCapturing[] = "capturing";

}  // namespace packet_probe
