#include "packet_probe/event_pipeline.hpp"

#include <exception>
#include <string>
#include <utility>

namespace packet_probe {

EventPipeline::EventPipeline(DecoderFactory decoder_factory, EventSink sink)
    : decoder_factory_(std::move(decoder_factory)), sink_(std::move(sink)) {}

void EventPipeline::consume(PacketEvent const& event) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!sink_) {
    return;
  }

  sink_(event);
  if (event.type != EventType::RawBytes || event.payload.empty() || !decoder_factory_) {
    return;
  }

  auto& decoder = decoder_for(event);
  try {
    auto result = decoder.consume(event.payload);
    for (auto& frame : result.frames) {
      sink_(make_frame_event(event, std::move(frame)));
    }
  } catch (std::exception const& ex) {
    auto error = event;
    error.sequence = next_derived_sequence_++;
    error.parent_sequence = event.sequence;
    error.type = EventType::Error;
    error.payload.clear();
    error.summary = std::string("decoder error: ") + ex.what();
    sink_(error);
  }
}

std::string EventPipeline::stream_key(PacketEvent const& event) const {
  return event.session_id + "|" + event.transport + "|" + to_string(event.direction) + "|" + event.source_endpoint +
         "|" + event.destination_endpoint;
}

FrameDecoder& EventPipeline::decoder_for(PacketEvent const& event) {
  auto key = stream_key(event);
  auto found = decoders_.find(key);
  if (found == decoders_.end()) {
    found = decoders_.emplace(std::move(key), decoder_factory_()).first;
  }
  return *found->second;
}

PacketEvent EventPipeline::make_frame_event(PacketEvent const& parent, std::vector<std::uint8_t> payload) {
  PacketEvent frame = parent;
  frame.sequence = next_derived_sequence_++;
  frame.parent_sequence = parent.sequence;
  frame.type = EventType::Frame;
  frame.payload = std::move(payload);
  frame.summary = "FRAME " + std::to_string(frame.payload.size()) + " bytes";
  frame.decoded_json.clear();
  frame.request_sequence = 0;
  frame.response_sequence = 0;
  frame.latency_ns = 0;
  frame.request_size = 0;
  frame.response_size = 0;
  return frame;
}

}  // namespace packet_probe
