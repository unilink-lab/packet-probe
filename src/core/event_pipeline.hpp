#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>

#include "packet_probe/core/sequence_allocator.hpp"
#include "packet_probe/decoder/frame_decoder.hpp"
#include "packet_probe/core/packet_event.hpp"

namespace packet_probe {

class EventPipeline {
 public:
  using DecoderFactory = std::function<std::unique_ptr<FrameDecoder>()>;
  using EventSink = std::function<void(PacketEvent const&)>;

  EventPipeline(DecoderFactory decoder_factory, EventSink sink, SharedSequenceAllocator seq_alloc);

  void consume(PacketEvent const& event);

 private:
  std::string stream_key(PacketEvent const& event) const;
  PacketEvent make_frame_event(PacketEvent const& parent, std::vector<std::uint8_t> payload, std::vector<std::uint64_t> const& parent_seqs);

  DecoderFactory decoder_factory_;
  EventSink sink_;
  SharedSequenceAllocator seq_alloc_;
  std::unordered_map<std::string, std::unique_ptr<FrameDecoder>> decoders_;
  std::unordered_map<std::string, std::vector<std::uint64_t>> stream_raw_sequences_;
  std::mutex mutex_;
};

}  // namespace packet_probe
