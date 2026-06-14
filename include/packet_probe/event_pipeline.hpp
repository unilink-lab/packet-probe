#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>

#include "packet_probe/frame_decoder.hpp"
#include "packet_probe/packet_event.hpp"

namespace packet_probe {

class EventPipeline {
 public:
  using DecoderFactory = std::function<std::unique_ptr<FrameDecoder>()>;
  using EventSink = std::function<void(PacketEvent const&)>;

  EventPipeline(DecoderFactory decoder_factory, EventSink sink);

  void consume(PacketEvent const& event);

 private:
  std::string stream_key(PacketEvent const& event) const;
  FrameDecoder& decoder_for(PacketEvent const& event);
  PacketEvent make_frame_event(PacketEvent const& parent, std::vector<std::uint8_t> payload);

  DecoderFactory decoder_factory_;
  EventSink sink_;
  std::uint64_t next_derived_sequence_ = 1000000000000ULL;
  std::unordered_map<std::string, std::unique_ptr<FrameDecoder>> decoders_;
  std::mutex mutex_;
};

}  // namespace packet_probe
