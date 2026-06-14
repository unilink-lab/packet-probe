#include <cassert>
#include <cstdint>
#include <stdexcept>
#include <vector>

#include "decoder/frame_decoder_factory.hpp"

namespace {

bool throws_invalid_argument(auto fn) {
  try {
    fn();
  } catch (std::invalid_argument const&) {
    return true;
  }
  return false;
}

}  // namespace

int main() {
  packet_probe::DecoderConfig raw_config;
  auto raw = packet_probe::create_frame_decoder(raw_config);
  auto raw_result = raw->consume(std::vector<std::uint8_t>{0x01, 0x02});
  assert(raw->name() == "raw");
  assert(raw_result.frames.size() == 1);
  assert((raw_result.frames[0] == std::vector<std::uint8_t>{0x01, 0x02}));

  packet_probe::DecoderConfig fixed_config;
  fixed_config.decoder = "fixed";
  fixed_config.frame_size = 4;
  auto fixed = packet_probe::create_frame_decoder(fixed_config);
  auto partial = fixed->consume(std::vector<std::uint8_t>{0x02, 0x03});
  assert(partial.frames.empty());
  assert((partial.remaining_buffer == std::vector<std::uint8_t>{0x02, 0x03}));
  auto completed = fixed->consume(std::vector<std::uint8_t>{0xAA, 0xBB});
  assert(completed.frames.size() == 1);
  assert((completed.frames[0] == std::vector<std::uint8_t>{0x02, 0x03, 0xAA, 0xBB}));

  fixed->reset();
  auto many = fixed->consume(std::vector<std::uint8_t>{0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08});
  assert(many.frames.size() == 2);

  packet_probe::DecoderConfig delimiter_config;
  delimiter_config.decoder = "delimiter";
  delimiter_config.delimiter = packet_probe::parse_delimiter_bytes("0A");
  auto delimiter = packet_probe::create_frame_decoder(delimiter_config);
  auto delimited = delimiter->consume(std::vector<std::uint8_t>{0x41, 0x0A, 0x42, 0x0A});
  assert(delimited.frames.size() == 2);
  assert((delimited.frames[0] == std::vector<std::uint8_t>{0x41, 0x0A}));
  assert((delimited.frames[1] == std::vector<std::uint8_t>{0x42, 0x0A}));

  packet_probe::DecoderConfig big_config;
  big_config.decoder = "length-prefix";
  big_config.length_size = 2;
  big_config.length_endian = "big";
  auto big = packet_probe::create_frame_decoder(big_config);
  auto big_result = big->consume(std::vector<std::uint8_t>{0x00, 0x03, 0xAA, 0xBB, 0xCC});
  assert(big_result.frames.size() == 1);
  assert((big_result.frames[0] == std::vector<std::uint8_t>{0xAA, 0xBB, 0xCC}));

  packet_probe::DecoderConfig little_config;
  little_config.decoder = "length-prefix";
  little_config.length_size = 2;
  little_config.length_endian = "little";
  auto little = packet_probe::create_frame_decoder(little_config);
  auto little_result = little->consume(std::vector<std::uint8_t>{0x03, 0x00, 0x11, 0x22, 0x33});
  assert(little_result.frames.size() == 1);
  assert((little_result.frames[0] == std::vector<std::uint8_t>{0x11, 0x22, 0x33}));

  assert((packet_probe::parse_delimiter_bytes("CRLF") == std::vector<std::uint8_t>{0x0D, 0x0A}));
  assert(throws_invalid_argument([] {
    packet_probe::DecoderConfig invalid;
    invalid.decoder = "fixed";
    packet_probe::create_frame_decoder(invalid);
  }));
  assert(throws_invalid_argument([] {
    packet_probe::DecoderConfig invalid;
    invalid.decoder = "missing";
    packet_probe::create_frame_decoder(invalid);
  }));

  return 0;
}
