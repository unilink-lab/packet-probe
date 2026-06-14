#pragma once

#include <cstdint>
#include <optional>
#include <span>
#include <string>

namespace packet_probe {

class MessageDecoder {
 public:
  virtual ~MessageDecoder() = default;

  virtual std::string name() const = 0;
  virtual std::optional<std::string> decode_json(std::span<const std::uint8_t> frame_payload) = 0;
  virtual void reset() = 0;
};

}  // namespace packet_probe
