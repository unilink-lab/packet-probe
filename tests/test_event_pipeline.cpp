#include <cassert>
#include <cstdint>
#include <vector>

#include "packet_probe/event_pipeline.hpp"
#include "packet_probe/frame_decoder_factory.hpp"

int main() {
  packet_probe::DecoderConfig config;
  config.decoder = "fixed";
  config.frame_size = 2;

  std::vector<packet_probe::PacketEvent> events;
  packet_probe::EventPipeline pipeline(packet_probe::make_frame_decoder_factory(config),
                                       [&](packet_probe::PacketEvent const& event) { events.push_back(event); });

  packet_probe::PacketEvent raw;
  raw.sequence = 7;
  raw.timestamp_ns = 100;
  raw.session_id = "serial-1";
  raw.transport = "serial";
  raw.direction = packet_probe::Direction::DeviceToApp;
  raw.type = packet_probe::EventType::RawBytes;
  raw.source_endpoint = "/dev/pts/1";
  raw.destination_endpoint = "packet-probe";
  raw.payload = {0x01, 0x02, 0x03, 0x04};
  raw.summary = "DEVICE -> APP 4 bytes";

  pipeline.consume(raw);

  assert(events.size() == 3);
  assert(events[0].sequence == 7);
  assert(events[0].parent_sequence == 0);
  assert(events[1].type == packet_probe::EventType::Frame);
  assert(events[1].parent_sequence == 7);
  assert(events[1].sequence != 7);
  assert(events[1].direction == raw.direction);
  assert(events[1].source_endpoint == raw.source_endpoint);
  assert(events[1].destination_endpoint == raw.destination_endpoint);
  assert((events[1].payload == std::vector<std::uint8_t>{0x01, 0x02}));
  assert(events[2].parent_sequence == 7);
  assert((events[2].payload == std::vector<std::uint8_t>{0x03, 0x04}));

  return 0;
}
