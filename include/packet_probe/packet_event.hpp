#pragma once

#include <cstdint>
#include <string>
#include <cstddef>
#include <vector>

namespace packet_probe {

enum class Direction {
  AppToDevice,
  DeviceToApp,
  Rx,
  Tx
};

enum class EventType {
  RawBytes,
  Frame,
  DecodedMessage,
  Error,
  StateChange,
  Statistic,
  Latency
};

struct PacketEvent {
  std::uint64_t sequence = 0;
  std::int64_t timestamp_ns = 0;

  std::string session_id;
  std::string transport;
  Direction direction = Direction::AppToDevice;
  EventType type = EventType::RawBytes;

  std::string source_endpoint;
  std::string destination_endpoint;

  std::vector<std::uint8_t> payload;

  std::string summary;
  std::string decoded_json;

  std::uint64_t request_sequence = 0;
  std::uint64_t response_sequence = 0;
  std::int64_t latency_ns = 0;
  std::size_t request_size = 0;
  std::size_t response_size = 0;
};

const char* to_string(Direction direction);
const char* to_string(EventType type);
std::int64_t now_ns();

}  // namespace packet_probe
