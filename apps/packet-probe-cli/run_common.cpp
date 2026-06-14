#include "run_common.hpp"

#include <utility>

namespace packet_probe::cli {

bool stdin_is_terminal() {
#if defined(_WIN32)
  return _isatty(_fileno(stdin)) != 0;
#else
  return isatty(fileno(stdin)) != 0;
#endif
}

std::vector<std::uint8_t> parse_send_line(std::string const& line, SendInputOptions const& send_options) {
  switch (send_options.format) {
    case SendInputFormat::Text:
      return parse_text_payload(line);
    case SendInputFormat::Hex:
      return parse_hex_payload(line);
    case SendInputFormat::File:
      break;
  }
  throw std::logic_error("send-file does not parse stdin lines");
}

void print_event(PacketEvent const& event, bool hex_raw_enabled, bool hex_frame_enabled) {
  if (event.type == EventType::RawBytes && hex_raw_enabled) {
    auto direction = event.direction == Direction::AppToDevice ? "APP -> DEVICE" : "DEVICE -> APP";
    std::cout << format_event_line(event.timestamp_ns, direction, event.payload.size(), event.payload) << '\n';
    return;
  }

  if (event.type == EventType::Frame && hex_frame_enabled) {
    auto direction = event.direction == Direction::AppToDevice ? "APP -> DEVICE" : "DEVICE -> APP";
    std::cout << "[frame] parent=" << event.parent_sequence << ' ' << direction << ' ' << event.payload.size()
              << " bytes";
    auto const hex = to_hex(event.payload, true);
    if (!hex.empty()) {
      std::cout << "  " << hex;
    }
    std::cout << '\n';
    return;
  }

  if (event.type == EventType::Latency) {
    std::cout << "[latency] request=" << event.request_sequence << " response=" << event.response_sequence << ' '
              << event.latency_ns / 1000 << " us\n";
    return;
  }

  if (event.type == EventType::Error || event.type == EventType::StateChange) {
    std::cout << event.summary << '\n';
  }
}

std::unique_ptr<JsonlRecorder> make_recorder(CliOptions const& options) {
  auto recorder = std::make_unique<JsonlRecorder>();
  if (!options.log_path.empty()) {
    recorder->open(options.log_path);
  }
  return recorder;
}

EventPipeline make_pipeline(CliOptions const& options, JsonlRecorder& recorder) {
  (void)create_frame_decoder(options.decoder_config);
  return EventPipeline(make_frame_decoder_factory(options.decoder_config), [&](PacketEvent const& event) {
    recorder.record(event);
    print_event(event, options.hex_raw, options.hex_frame);
  });
}

}  // namespace packet_probe::cli
