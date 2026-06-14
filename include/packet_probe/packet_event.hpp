#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace packet_probe {

enum class Direction { Rx, Tx };

enum class EventType {
  RawBytes,
  Frame,
  DecodedMessage,
  Error,
  StateChange,
  Statistic
};

struct PacketEvent {
  std::uint64_t sequence = 0;
  std::int64_t timestamp_ns = 0;

  std::string session_id;
  std::string transport;
  Direction direction = Direction::Rx;
  EventType type = EventType::RawBytes;

  std::vector<std::uint8_t> payload;

  std::string summary;
  std::string decoded_json;
};

const char* to_string(Direction direction);
const char* to_string(EventType type);
std::int64_t now_ns();

}  // namespace packet_probe
