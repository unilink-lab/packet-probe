#include "core/event_pipeline.hpp"

#include <exception>
#include <string>
#include <utility>
#include <vector>

namespace packet_probe {

EventPipeline::EventPipeline(DecoderFactory decoder_factory, EventSink sink)
    : decoder_factory_(std::move(decoder_factory)), sink_(std::move(sink)) {}

void EventPipeline::consume(PacketEvent const& event) {
  if (!sink_) {
    return;
  }

  sink_(event);
  if (event.type != EventType::RawBytes || event.payload.empty() || !decoder_factory_) {
    return;
  }

  std::vector<PacketEvent> derived_events;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    auto const key = stream_key(event);
    auto found = decoders_.find(key);
    if (found == decoders_.end()) {
      found = decoders_.emplace(key, decoder_factory_()).first;
    }
    auto& decoder = *found->second;

    // Track raw sequences contributing to the current decoding transaction (Option A)
    auto& seqs = stream_raw_sequences_[key];
    seqs.push_back(event.sequence);

    try {
      auto result = decoder.consume(event.payload);
      derived_events.reserve(result.frames.size());
      for (auto& frame : result.frames) {
        derived_events.push_back(make_frame_event(event, std::move(frame), seqs));
      }
      // If the decoder's buffer is empty, all accumulated raw packet sequences
      // have been fully reassembled into frames. Clear the history for the next frame.
      if (result.remaining_buffer.empty()) {
        seqs.clear();
      }
    } catch (std::exception const& ex) {
      auto error = event;
      error.sequence = next_derived_sequence_++;
      error.parent_sequence = event.sequence;
      error.parent_sequences = seqs;
      error.type = EventType::Error;
      error.payload.clear();
      error.summary = std::string("decoder error: ") + ex.what();
      derived_events.push_back(std::move(error));
      seqs.clear();
    }
  }

  for (auto const& derived : derived_events) {
    sink_(derived);
  }
}

std::string EventPipeline::stream_key(PacketEvent const& event) const {
  return event.session_id + "|" + event.transport + "|" + to_string(event.direction) + "|" + event.source_endpoint +
         "|" + event.destination_endpoint;
}


PacketEvent EventPipeline::make_frame_event(PacketEvent const& parent, std::vector<std::uint8_t> payload, std::vector<std::uint64_t> const& parent_seqs) {
  PacketEvent frame = parent;
  frame.sequence = next_derived_sequence_++;
  frame.parent_sequence = parent.sequence;
  frame.parent_sequences = parent_seqs;
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
