#include "packet_probe/frame_decoder.hpp"

#include <algorithm>
#include <memory>
#include <stdexcept>

namespace packet_probe {

class FixedSizeFrameDecoder final : public FrameDecoder {
 public:
  explicit FixedSizeFrameDecoder(std::size_t frame_size) : frame_size_(frame_size) {
    if (frame_size_ == 0) {
      throw std::invalid_argument("fixed decoder requires --frame-size");
    }
  }

  std::string name() const override { return "fixed"; }

  FrameDecodeResult consume(std::span<const std::uint8_t> payload) override {
    buffer_.insert(buffer_.end(), payload.begin(), payload.end());

    FrameDecodeResult result;
    while (buffer_.size() >= frame_size_) {
      result.frames.emplace_back(buffer_.begin(), buffer_.begin() + static_cast<std::ptrdiff_t>(frame_size_));
      buffer_.erase(buffer_.begin(), buffer_.begin() + static_cast<std::ptrdiff_t>(frame_size_));
    }
    result.remaining_buffer = buffer_;
    return result;
  }

  void reset() override { buffer_.clear(); }

 private:
  std::size_t frame_size_;
  std::vector<std::uint8_t> buffer_;
};

std::unique_ptr<FrameDecoder> make_fixed_size_frame_decoder(std::size_t frame_size) {
  return std::make_unique<FixedSizeFrameDecoder>(frame_size);
}

}  // namespace packet_probe
