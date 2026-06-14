#include <cassert>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <vector>

#include "core/send_input_parser.hpp"

namespace {

bool throws_invalid_argument(auto fn) {
  try {
    fn();
  } catch (std::invalid_argument const&) {
    return true;
  }
  return false;
}

bool throws_runtime_error(auto fn) {
  try {
    fn();
  } catch (std::runtime_error const&) {
    return true;
  }
  return false;
}

}  // namespace

int main() {
  assert((packet_probe::parse_text_payload("hello") == std::vector<std::uint8_t>{0x68, 0x65, 0x6C, 0x6C, 0x6F}));
  assert(packet_probe::parse_text_payload("").empty());

  assert((packet_probe::parse_hex_payload("02 10 01 00 03 A7") ==
          std::vector<std::uint8_t>{0x02, 0x10, 0x01, 0x00, 0x03, 0xA7}));
  assert((packet_probe::parse_hex_payload("0210010003A7") ==
          std::vector<std::uint8_t>{0x02, 0x10, 0x01, 0x00, 0x03, 0xA7}));
  assert((packet_probe::parse_hex_payload("0x02 0x10 0x01") == std::vector<std::uint8_t>{0x02, 0x10, 0x01}));
  assert((packet_probe::parse_hex_payload("02:10:01") == std::vector<std::uint8_t>{0x02, 0x10, 0x01}));
  assert((packet_probe::parse_hex_payload("02-10-01") == std::vector<std::uint8_t>{0x02, 0x10, 0x01}));

  assert(throws_invalid_argument([] { packet_probe::parse_hex_payload("0"); }));
  assert(throws_invalid_argument([] { packet_probe::parse_hex_payload("GG"); }));
  assert(throws_invalid_argument([] { packet_probe::parse_hex_payload("02 1"); }));
  assert(throws_invalid_argument([] { packet_probe::parse_hex_payload("02 0x"); }));
  assert(throws_invalid_argument([] { packet_probe::parse_hex_payload("02 ZZ"); }));

  auto const path = std::filesystem::temp_directory_path() / "packet-probe-send-input-test.bin";
  {
    std::ofstream output(path, std::ios::binary);
    std::vector<char> bytes{static_cast<char>(0x00), static_cast<char>(0x7F), static_cast<char>(0x80),
                            static_cast<char>(0xFF)};
    output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
  }

  assert((packet_probe::read_binary_file(path.string()) == std::vector<std::uint8_t>{0x00, 0x7F, 0x80, 0xFF}));
  std::filesystem::remove(path);
  assert(throws_runtime_error([] { packet_probe::read_binary_file("/tmp/packet-probe-missing-send-input.bin"); }));

  return 0;
}
