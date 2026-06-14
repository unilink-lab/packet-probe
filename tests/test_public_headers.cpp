#include "packet_probe/packet_probe.hpp"

#include "packet_probe/core/jsonl_serializer.hpp"
#include "packet_probe/core/packet_event.hpp"
#include "packet_probe/decoder/decoder_config.hpp"
#include "packet_probe/decoder/frame_decoder.hpp"
#include "packet_probe/decoder/message_decoder.hpp"
#include "packet_probe/ipc/ipc_protocol.hpp"

#include <cassert>
#include <memory>
#include <optional>
#include <string>

int main() {
  packet_probe::PacketEvent event;
  event.sequence = 1;
  auto const line = packet_probe::serialize_event_jsonl(event);
  assert(line.find("\"seq\":1") != std::string::npos);

  packet_probe::DecoderConfig config;
  config.decoder = "raw";
  assert(config.decoder == "raw");

  static_assert(packet_probe::kPacketProbeLogSchema[0] != '\0');
  static_assert(packet_probe::kPacketProbeEventSchema[0] != '\0');

  return 0;
}
