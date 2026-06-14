#include "packet_probe/decoder/frame_decoder.hpp"

#include <algorithm>
#include <memory>
#include <stdexcept>

namespace packet_probe {

class DelimiterFrameDecoder final : public FrameDecoder {
 public:
  DelimiterFrameDecoder(std::vector<std::uint8_t> delimiter, bool include_delimiter)
      : delimiter_(std::move(delimiter)), include_delimiter_(include_delimiter) {
    if (delimiter_.empty()) {
      throw std::invalid_argument("delimiter decoder requires --delimiter");
    }
  }

  std::string name() const override { return "delimiter"; }

  FrameDecodeResult consume(std::span<const std::uint8_t> payload) override {
    buffer_.insert(buffer_.end(), payload.begin(), payload.end());

    FrameDecodeResult result;
    auto search_begin = buffer_.begin();
    while (true) {
      auto found = std::search(search_begin, buffer_.end(), delimiter_.begin(), delimiter_.end());
      if (found == buffer_.end()) {
        break;
      }

      auto frame_end = found + static_cast<std::ptrdiff_t>(delimiter_.size());
      auto payload_end = include_delimiter_ ? frame_end : found;
      result.frames.emplace_back(buffer_.begin(), payload_end);
      buffer_.erase(buffer_.begin(), frame_end);
      search_begin = buffer_.begin();
    }

    result.remaining_buffer = buffer_;
    return result;
  }

  void reset() override { buffer_.clear(); }

 private:
  std::vector<std::uint8_t> delimiter_;
  bool include_delimiter_;
  std::vector<std::uint8_t> buffer_;
};

std::unique_ptr<FrameDecoder> make_delimiter_frame_decoder(std::vector<std::uint8_t> delimiter,
                                                           bool include_delimiter) {
  return std::make_unique<DelimiterFrameDecoder>(std::move(delimiter), include_delimiter);
}

}  // namespace packet_probe
