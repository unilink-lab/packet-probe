#pragma once

#include <cstddef>
#include <cstdint>
#include <deque>
#include <optional>

#include "packet_probe/core/packet_event.hpp"

namespace packet_probe {

struct LatencyMeasurement {
  std::uint64_t request_sequence = 0;
  std::uint64_t response_sequence = 0;
  std::int64_t latency_ns = 0;
  std::size_t request_size = 0;
  std::size_t response_size = 0;
};

class LatencyTracker {
 public:
  std::optional<LatencyMeasurement> observe(PacketEvent const& event);
  std::size_t pending_count() const;
  void clear();

 private:
  struct PendingRequest {
    std::uint64_t sequence = 0;
    std::int64_t timestamp_ns = 0;
    std::size_t size = 0;
  };

  std::deque<PendingRequest> pending_;
};

PacketEvent make_latency_event(PacketEvent const& response, LatencyMeasurement const& measurement);

}  // namespace packet_probe
