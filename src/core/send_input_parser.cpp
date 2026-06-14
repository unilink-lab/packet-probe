#include "packet_probe/send_input_parser.hpp"

#include <cctype>
#include <fstream>
#include <iterator>
#include <stdexcept>

namespace packet_probe {

namespace {

bool is_separator(char ch) {
  return std::isspace(static_cast<unsigned char>(ch)) || ch == ':' || ch == '-';
}

int hex_value(char ch) {
  auto const byte = static_cast<unsigned char>(ch);
  if (byte >= '0' && byte <= '9') {
    return byte - '0';
  }
  if (byte >= 'a' && byte <= 'f') {
    return 10 + byte - 'a';
  }
  if (byte >= 'A' && byte <= 'F') {
    return 10 + byte - 'A';
  }
  return -1;
}

[[noreturn]] void throw_hex_error(std::size_t column, std::string const& message) {
  throw std::invalid_argument("invalid hex input at column " + std::to_string(column) + ": " + message);
}

std::uint8_t read_hex_byte(std::string const& line, std::size_t& index, std::size_t column) {
  if (index >= line.size() || hex_value(line[index]) < 0) {
    throw_hex_error(column, "expected two hex digits");
  }
  auto const high = hex_value(line[index]);
  ++index;
  if (index >= line.size() || hex_value(line[index]) < 0) {
    throw_hex_error(column, "expected two hex digits");
  }
  auto const low = hex_value(line[index]);
  ++index;
  return static_cast<std::uint8_t>((high << 4) | low);
}

}  // namespace

std::vector<std::uint8_t> parse_text_payload(std::string const& line) {
  return std::vector<std::uint8_t>(line.begin(), line.end());
}

std::vector<std::uint8_t> parse_hex_payload(std::string const& line) {
  std::vector<std::uint8_t> payload;
  std::size_t index = 0;
  while (index < line.size()) {
    if (is_separator(line[index])) {
      ++index;
      continue;
    }

    auto const column = index + 1;
    if (line[index] == '0' && index + 1 < line.size() && (line[index + 1] == 'x' || line[index + 1] == 'X')) {
      index += 2;
    }

    if (index >= line.size() || hex_value(line[index]) < 0) {
      throw_hex_error(column, "expected two hex digits");
    }

    payload.push_back(read_hex_byte(line, index, column));

    if (index < line.size() && !is_separator(line[index])) {
      if (line[index] == '0' && index + 1 < line.size() && (line[index + 1] == 'x' || line[index + 1] == 'X')) {
        continue;
      }
      if (hex_value(line[index]) < 0) {
        throw_hex_error(index + 1, "expected hex digit or separator");
      }
    }
  }
  return payload;
}

std::vector<std::uint8_t> read_binary_file(std::string const& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) {
    throw std::runtime_error("failed to open send file: " + path);
  }
  return std::vector<std::uint8_t>(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
}

}  // namespace packet_probe
