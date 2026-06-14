#include <cassert>
#include <cstdint>
#include <string>
#include <vector>

#include "packet_probe/jsonl_recorder.hpp"

namespace {

packet_probe::PacketEvent base_event() {
  packet_probe::PacketEvent event;
  event.sequence = 1;
  event.timestamp_ns = 1781234567890;
  event.session_id = "tcp-client-1";
  event.transport = "tcp";
  event.direction = packet_probe::Direction::Rx;
  event.type = packet_probe::EventType::RawBytes;
  return event;
}

}  // namespace

int main() {
  auto event = base_event();
  event.payload = {0x02, 0x10, 0x01, 0x00, 0x03, 0xA7};
  event.summary = "RX 6 bytes";

  auto line = packet_probe::serialize_jsonl(event);
  assert(line ==
         "{\"seq\":1,\"time_ns\":1781234567890,\"session\":\"tcp-client-1\",\"transport\":\"tcp\","
         "\"direction\":\"rx\",\"type\":\"raw_bytes\",\"size\":6,\"payload_hex\":\"0210010003A7\","
         "\"summary\":\"RX 6 bytes\"}");

  auto empty = base_event();
  empty.payload = {};
  empty.summary = "RX 0 bytes";
  auto empty_line = packet_probe::serialize_jsonl(empty);
  assert(empty_line.find("\"size\":0") != std::string::npos);
  assert(empty_line.find("\"payload_hex\":\"\"") != std::string::npos);

  auto binary = base_event();
  binary.payload = {0x00, 0x7F, 0x80, 0xFF};
  binary.summary = "binary \"payload\"";
  auto binary_line = packet_probe::serialize_jsonl(binary);
  assert(binary_line.find("\"payload_hex\":\"007F80FF\"") != std::string::npos);
  assert(binary_line.find("\"summary\":\"binary \\\"payload\\\"\"") != std::string::npos);

  auto error = base_event();
  error.type = packet_probe::EventType::Error;
  error.summary = "line\nbreak";
  auto error_line = packet_probe::serialize_jsonl(error);
  assert(error_line.find("\"type\":\"error\"") != std::string::npos);
  assert(error_line.find("\"summary\":\"line\\nbreak\"") != std::string::npos);

  return 0;
}
