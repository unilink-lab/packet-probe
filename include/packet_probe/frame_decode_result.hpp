#pragma once

#include <cstdint>
#include <vector>

namespace packet_probe {

struct FrameDecodeResult {
  std::vector<std::vector<std::uint8_t>> frames;
  std::vector<std::uint8_t> remaining_buffer;
};

}  // namespace packet_probe
