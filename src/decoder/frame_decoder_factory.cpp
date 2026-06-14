#include "packet_probe/frame_decoder_factory.hpp"

#include <algorithm>
#include <cctype>
#include <stdexcept>

namespace packet_probe {

std::unique_ptr<FrameDecoder> make_fixed_size_frame_decoder(std::size_t frame_size);
std::unique_ptr<FrameDecoder> make_delimiter_frame_decoder(std::vector<std::uint8_t> delimiter,
                                                           bool include_delimiter);
std::unique_ptr<FrameDecoder> make_length_prefix_frame_decoder(std::size_t length_size, std::string length_endian,
                                                               bool length_includes_header);

namespace {

class RawFrameDecoder final : public FrameDecoder {
 public:
  std::string name() const override { return "raw"; }

  FrameDecodeResult consume(std::span<const std::uint8_t> payload) override {
    FrameDecodeResult result;
    result.frames.emplace_back(payload.begin(), payload.end());
    return result;
  }

  void reset() override {}
};

std::string lowercase(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) {
    return static_cast<char>(std::tolower(ch));
  });
  return value;
}

std::uint8_t parse_hex_byte(std::string const& byte) {
  if (byte.size() != 2) {
    throw std::invalid_argument("hex bytes must contain exactly two digits");
  }
  std::size_t parsed = 0;
  auto value = std::stoul(byte, &parsed, 16);
  if (parsed != byte.size() || value > 0xFF) {
    throw std::invalid_argument("invalid hex byte: " + byte);
  }
  return static_cast<std::uint8_t>(value);
}

}  // namespace

std::vector<std::uint8_t> parse_delimiter_bytes(std::string const& value) {
  auto const named = lowercase(value);
  if (named == "crlf") {
    return {0x0D, 0x0A};
  }
  if (named == "lf") {
    return {0x0A};
  }

  std::string compact;
  compact.reserve(value.size());
  for (auto ch : value) {
    if (!std::isspace(static_cast<unsigned char>(ch))) {
      compact += ch;
    }
  }
  if (compact.empty() || compact.size() % 2 != 0) {
    throw std::invalid_argument("--delimiter requires hex bytes, LF, or CRLF");
  }

  std::vector<std::uint8_t> bytes;
  bytes.reserve(compact.size() / 2);
  for (std::size_t i = 0; i < compact.size(); i += 2) {
    bytes.push_back(parse_hex_byte(compact.substr(i, 2)));
  }
  return bytes;
}

std::unique_ptr<FrameDecoder> create_frame_decoder(DecoderConfig const& config) {
  auto const decoder = lowercase(config.decoder);
  if (decoder == "raw") {
    return std::make_unique<RawFrameDecoder>();
  }
  if (decoder == "fixed") {
    return make_fixed_size_frame_decoder(config.frame_size);
  }
  if (decoder == "delimiter") {
    return make_delimiter_frame_decoder(config.delimiter, config.include_delimiter);
  }
  if (decoder == "length-prefix") {
    return make_length_prefix_frame_decoder(config.length_size, lowercase(config.length_endian),
                                            config.length_includes_header);
  }
  throw std::invalid_argument("unknown decoder: " + config.decoder);
}

std::function<std::unique_ptr<FrameDecoder>()> make_frame_decoder_factory(DecoderConfig config) {
  return [config = std::move(config)] { return create_frame_decoder(config); };
}

}  // namespace packet_probe
