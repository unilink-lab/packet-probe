#include <cassert>
#include <cstdint>
#include <vector>

#include "core/event_pipeline.hpp"
#include "decoder/frame_decoder_factory.hpp"
#include "packet_probe/core/sequence_allocator.hpp"

int main() {
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

  packet_probe::DecoderConfig fixed_config;
  fixed_config.decoder = "fixed";
  fixed_config.frame_size = 2;

  std::vector<packet_probe::PacketEvent> events;
  packet_probe::EventPipeline pipeline(packet_probe::make_frame_decoder_factory(fixed_config),
                                       [&](packet_probe::PacketEvent const& event) { events.push_back(event); },
                                       packet_probe::make_sequence_allocator());

  pipeline.consume(raw);
  assert(events.size() == 3);
  assert(events[0].sequence == 7);
  assert(events[0].parent_sequence == 0);
  assert(events[1].type == packet_probe::EventType::Frame);
  assert(events[1].parent_sequence == 7);
  assert(events[1].parent_sequences.size() == 1);
  assert(events[1].parent_sequences[0] == 7);
  assert(events[1].sequence != 7);
  assert(events[1].direction == raw.direction);
  assert(events[1].source_endpoint == raw.source_endpoint);
  assert(events[1].destination_endpoint == raw.destination_endpoint);
  assert((events[1].payload == std::vector<std::uint8_t>{0x01, 0x02}));
  assert(events[2].parent_sequence == 7);
  assert(events[2].parent_sequences.size() == 1);
  assert(events[2].parent_sequences[0] == 7);
  assert((events[2].payload == std::vector<std::uint8_t>{0x03, 0x04}));

  events.clear();
  auto empty = raw;
  empty.sequence = 8;
  empty.payload.clear();
  pipeline.consume(empty);
  assert(events.size() == 1);
  assert(events[0].sequence == 8);
  assert(events[0].type == packet_probe::EventType::RawBytes);

  packet_probe::DecoderConfig error_config;
  error_config.decoder = "length-prefix";
  error_config.length_size = 2;
  error_config.length_includes_header = true;

  std::vector<packet_probe::PacketEvent> error_events;
  packet_probe::EventPipeline error_pipeline(packet_probe::make_frame_decoder_factory(error_config),
                                             [&](packet_probe::PacketEvent const& event) {
                                               error_events.push_back(event);
                                             },
                                             packet_probe::make_sequence_allocator());

  auto invalid = raw;
  invalid.sequence = 9;
  invalid.payload = {0x00, 0x01};
  error_pipeline.consume(invalid);
  assert(error_events.size() == 2);
  assert(error_events[0].sequence == 9);
  assert(error_events[1].type == packet_probe::EventType::Error);
  assert(error_events[1].parent_sequence == 9);
  assert(error_events[1].parent_sequences.size() == 1);
  assert(error_events[1].parent_sequences[0] == 9);
  assert(error_events[1].summary.find("decoder error:") == 0);

  // Test fragmented packets (Option A)
  events.clear();
  auto frag1 = raw;
  frag1.sequence = 10;
  frag1.payload = {0xAA};
  pipeline.consume(frag1);
  // No frame should be emitted yet (only raw bytes event 10)
  assert(events.size() == 1);
  assert(events[0].sequence == 10);

  auto frag2 = raw;
  frag2.sequence = 11;
  frag2.payload = {0xBB};
  pipeline.consume(frag2);
  // Now, raw bytes event 11 and frame event should be emitted
  assert(events.size() == 3);
  assert(events[1].sequence == 11);
  assert(events[2].type == packet_probe::EventType::Frame);
  assert(events[2].parent_sequence == 11);
  assert(events[2].parent_sequences.size() == 2);
  assert(events[2].parent_sequences[0] == 10);
  assert(events[2].parent_sequences[1] == 11);
  assert((events[2].payload == std::vector<std::uint8_t>{0xAA, 0xBB}));

  return 0;
}
