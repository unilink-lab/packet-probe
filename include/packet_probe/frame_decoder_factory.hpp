#pragma once

#include <functional>
#include <memory>

#include "packet_probe/decoder_config.hpp"
#include "packet_probe/frame_decoder.hpp"

namespace packet_probe {

std::unique_ptr<FrameDecoder> create_frame_decoder(DecoderConfig const& config);
std::function<std::unique_ptr<FrameDecoder>()> make_frame_decoder_factory(DecoderConfig config);

}  // namespace packet_probe
