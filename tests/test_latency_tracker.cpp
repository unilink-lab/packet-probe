#include <cassert>
#include <cstdint>

#include "packet_probe/latency_tracker.hpp"

namespace {

packet_probe::PacketEvent raw(std::uint64_t sequence, std::int64_t timestamp_ns, packet_probe::Direction direction,
                              std::size_t size) {
  packet_probe::PacketEvent event;
  event.sequence = sequence;
  event.timestamp_ns = timestamp_ns;
  event.transport = "tcp";
  event.session_id = "tcp-proxy-1";
  event.direction = direction;
  event.type = packet_probe::EventType::RawBytes;
  event.payload.resize(size);
  return event;
}

}  // namespace

int main() {
  packet_probe::LatencyTracker tracker;

  auto no_latency = tracker.observe(raw(1, 1000, packet_probe::Direction::AppToDevice, 8));
  assert(!no_latency);
  assert(tracker.pending_count() == 1);

  auto latency = tracker.observe(raw(2, 1940, packet_probe::Direction::DeviceToApp, 7));
  assert(latency);
  assert(latency->request_sequence == 1);
  assert(latency->response_sequence == 2);
  assert(latency->latency_ns == 940);
  assert(latency->request_size == 8);
  assert(latency->response_size == 7);
  assert(tracker.pending_count() == 0);

  auto unmatched_response = tracker.observe(raw(3, 2000, packet_probe::Direction::DeviceToApp, 7));
  assert(!unmatched_response);

  tracker.observe(raw(4, 3000, packet_probe::Direction::AppToDevice, 3));
  tracker.observe(raw(5, 4000, packet_probe::Direction::AppToDevice, 4));
  assert(tracker.pending_count() == 2);

  auto first = tracker.observe(raw(6, 4500, packet_probe::Direction::DeviceToApp, 5));
  assert(first);
  assert(first->request_sequence == 4);
  assert(first->response_sequence == 6);
  assert(first->latency_ns == 1500);
  assert(tracker.pending_count() == 1);

  auto second = tracker.observe(raw(7, 4700, packet_probe::Direction::DeviceToApp, 6));
  assert(second);
  assert(second->request_sequence == 5);
  assert(second->response_sequence == 7);
  assert(second->latency_ns == 700);
  assert(tracker.pending_count() == 0);

  tracker.observe(raw(8, 5000, packet_probe::Direction::AppToDevice, 1));
  tracker.clear();
  assert(tracker.pending_count() == 0);

  return 0;
}
