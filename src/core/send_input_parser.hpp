#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "core/send_input.hpp"

namespace packet_probe {

std::vector<std::uint8_t> parse_text_payload(std::string const& line);
std::vector<std::uint8_t> parse_hex_payload(std::string const& line);
std::vector<std::uint8_t> read_binary_file(std::string const& path);

}  // namespace packet_probe
