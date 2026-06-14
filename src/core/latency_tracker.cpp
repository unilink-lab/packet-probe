#include "packet_probe/latency_tracker.hpp"

#include <string>

namespace packet_probe {

std::optional<LatencyMeasurement> LatencyTracker::observe(PacketEvent const& event) {
  if (event.type != EventType::RawBytes) {
    return std::nullopt;
  }

  if (event.direction == Direction::AppToDevice) {
    pending_.push_back({event.sequence, event.timestamp_ns, event.payload.size()});
    return std::nullopt;
  }

  if (event.direction == Direction::DeviceToApp && !pending_.empty()) {
    auto request = pending_.front();
    pending_.pop_front();

    LatencyMeasurement measurement;
    measurement.request_sequence = request.sequence;
    measurement.response_sequence = event.sequence;
    measurement.latency_ns = event.timestamp_ns - request.timestamp_ns;
    measurement.request_size = request.size;
    measurement.response_size = event.payload.size();
    return measurement;
  }

  return std::nullopt;
}

std::size_t LatencyTracker::pending_count() const { return pending_.size(); }

void LatencyTracker::clear() { pending_.clear(); }

PacketEvent make_latency_event(PacketEvent const& response, LatencyMeasurement const& measurement) {
  PacketEvent event;
  event.sequence = response.sequence + 1;
  event.timestamp_ns = response.timestamp_ns;
  event.session_id = response.session_id;
  event.transport = response.transport;
  event.direction = response.direction;
  event.type = EventType::Latency;
  event.source_endpoint = response.source_endpoint;
  event.destination_endpoint = response.destination_endpoint;
  event.request_sequence = measurement.request_sequence;
  event.response_sequence = measurement.response_sequence;
  event.latency_ns = measurement.latency_ns;
  event.request_size = measurement.request_size;
  event.response_size = measurement.response_size;
  event.summary = "response latency " + std::to_string(measurement.latency_ns / 1000) + " us";
  return event;
}

}  // namespace packet_probe
