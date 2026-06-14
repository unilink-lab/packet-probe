#include "packet_probe/packet_event.hpp"

#include <chrono>

namespace packet_probe {

const char* to_string(Direction direction) {
  switch (direction) {
    case Direction::Rx:
      return "rx";
    case Direction::Tx:
      return "tx";
  }
  return "rx";
}

const char* to_string(EventType type) {
  switch (type) {
    case EventType::RawBytes:
      return "raw_bytes";
    case EventType::Frame:
      return "frame";
    case EventType::DecodedMessage:
      return "decoded_message";
    case EventType::Error:
      return "error";
    case EventType::StateChange:
      return "state_change";
    case EventType::Statistic:
      return "statistic";
  }
  return "raw_bytes";
}

std::int64_t now_ns() {
  auto const now = std::chrono::system_clock::now().time_since_epoch();
  return std::chrono::duration_cast<std::chrono::nanoseconds>(now).count();
}

}  // namespace packet_probe
