#include <cassert>
#include <cstdint>
#include <string>
#include <vector>

#include "packet_probe/jsonl_serializer.hpp"

namespace {

bool has_no_newline(std::string const& value) { return value.find('\n') == std::string::npos; }

}  // namespace

int main() {
  auto const metadata = packet_probe::serialize_metadata_jsonl();
  assert(metadata.find("\"type\":\"metadata\"") != std::string::npos);
  assert(metadata.find("\"schema\":\"packet-probe.log.v1\"") != std::string::npos);
  assert(metadata.find("\"event_schema\":\"packet-probe.event.v1\"") != std::string::npos);
  assert(metadata.find("\"tool\":\"packet-probe\"") != std::string::npos);
  assert(has_no_newline(metadata));

  packet_probe::PacketEvent event;
  event.sequence = 42;
  event.parent_sequence = 41;
  event.timestamp_ns = 1781234567890;
  event.session_id = "udp-1";
  event.transport = "udp";
  event.direction = packet_probe::Direction::DeviceToApp;
  event.type = packet_probe::EventType::RawBytes;
  event.source_endpoint = "127.0.0.1:9100";
  event.destination_endpoint = "127.0.0.1:9000";
  event.payload = {0x02, 0x10, 0x01};
  event.summary = "DEVICE -> APP 3 bytes";

  auto const line = packet_probe::serialize_event_jsonl(event);
  assert(line.find("\"seq\":42") != std::string::npos);
  assert(line.find("\"parent_seq\":41") != std::string::npos);
  assert(line.find("\"transport\":\"udp\"") != std::string::npos);
  assert(line.find("\"direction\":\"device_to_app\"") != std::string::npos);
  assert(line.find("\"source\":\"127.0.0.1:9100\"") != std::string::npos);
  assert(line.find("\"destination\":\"127.0.0.1:9000\"") != std::string::npos);
  assert(line.find("\"type\":\"raw_bytes\"") != std::string::npos);
  assert(line.find("\"payload_hex\":\"021001\"") != std::string::npos);
  assert(has_no_newline(line));

  return 0;
}
