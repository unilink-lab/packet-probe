#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace packet_probe {

struct DecoderConfig {
  std::string decoder = "raw";
  std::size_t frame_size = 0;
  std::vector<std::uint8_t> delimiter;
  bool include_delimiter = true;
  std::size_t length_size = 2;
  std::string length_endian = "big";
  bool length_includes_header = false;
};

std::vector<std::uint8_t> parse_delimiter_bytes(std::string const& value);

}  // namespace packet_probe
