#include "packet_probe/frame_decoder.hpp"

#include <memory>
#include <stdexcept>

namespace packet_probe {

class LengthPrefixFrameDecoder final : public FrameDecoder {
 public:
  LengthPrefixFrameDecoder(std::size_t length_size, std::string length_endian, bool length_includes_header)
      : length_size_(length_size),
        little_endian_(length_endian == "little"),
        length_includes_header_(length_includes_header) {
    if (length_size_ != 1 && length_size_ != 2 && length_size_ != 4) {
      throw std::invalid_argument("length-prefix decoder requires --length-size <1|2|4>");
    }
    if (length_endian != "big" && length_endian != "little") {
      throw std::invalid_argument("length-prefix decoder requires --length-endian <little|big>");
    }
  }

  std::string name() const override { return "length-prefix"; }

  FrameDecodeResult consume(std::span<const std::uint8_t> payload) override {
    buffer_.insert(buffer_.end(), payload.begin(), payload.end());

    FrameDecodeResult result;
    while (buffer_.size() >= length_size_) {
      auto const length = read_length();
      if (length_includes_header_) {
        if (length < length_size_) {
          throw std::runtime_error("length-prefix frame length is smaller than the length header");
        }
        if (buffer_.size() < length) {
          break;
        }
        result.frames.emplace_back(buffer_.begin(), buffer_.begin() + static_cast<std::ptrdiff_t>(length));
        buffer_.erase(buffer_.begin(), buffer_.begin() + static_cast<std::ptrdiff_t>(length));
      } else {
        auto const total_size = length_size_ + length;
        if (buffer_.size() < total_size) {
          break;
        }
        auto frame_begin = buffer_.begin() + static_cast<std::ptrdiff_t>(length_size_);
        auto frame_end = buffer_.begin() + static_cast<std::ptrdiff_t>(total_size);
        result.frames.emplace_back(frame_begin, frame_end);
        buffer_.erase(buffer_.begin(), frame_end);
      }
    }

    result.remaining_buffer = buffer_;
    return result;
  }

  void reset() override { buffer_.clear(); }

 private:
  std::size_t read_length() const {
    std::size_t length = 0;
    if (little_endian_) {
      for (std::size_t i = 0; i < length_size_; ++i) {
        length |= static_cast<std::size_t>(buffer_[i]) << (8 * i);
      }
    } else {
      for (std::size_t i = 0; i < length_size_; ++i) {
        length = (length << 8) | buffer_[i];
      }
    }
    return length;
  }

  std::size_t length_size_;
  bool little_endian_;
  bool length_includes_header_;
  std::vector<std::uint8_t> buffer_;
};

std::unique_ptr<FrameDecoder> make_length_prefix_frame_decoder(std::size_t length_size, std::string length_endian,
                                                               bool length_includes_header) {
  return std::make_unique<LengthPrefixFrameDecoder>(length_size, std::move(length_endian), length_includes_header);
}

}  // namespace packet_probe
