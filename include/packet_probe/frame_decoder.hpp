#pragma once

#include <cstdint>
#include <span>
#include <string>

#include "packet_probe/frame_decode_result.hpp"

namespace packet_probe {

class FrameDecoder {
 public:
  virtual ~FrameDecoder() = default;

  virtual std::string name() const = 0;
  virtual FrameDecodeResult consume(std::span<const std::uint8_t> payload) = 0;
  virtual void reset() = 0;
};

}  // namespace packet_probe
