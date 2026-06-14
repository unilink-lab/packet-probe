#include "cli_send_options.hpp"

#include <stdexcept>
#include <utility>

namespace packet_probe::cli {

namespace {

void set_send_format(CliOptions& options, SendInputFormat format, std::string file_path = {}) {
  ++options.send_option_count;
  if (options.send_option_count > 1) {
    throw std::invalid_argument("--send-text, --send-hex, and --send-file cannot be used together");
  }
  options.send_options.format = format;
  options.send_options.file_path = std::move(file_path);
}

}  // namespace

bool parse_send_option(CliOptions& options, std::string const& arg, int& index, int argc, char** argv) {
  if (arg == "--send-text") {
    set_send_format(options, SendInputFormat::Text);
    return true;
  }
  if (arg == "--send-hex") {
    set_send_format(options, SendInputFormat::Hex);
    return true;
  }
  if (arg == "--send-file") {
    if (++index >= argc) {
      throw std::invalid_argument("--send-file requires a value");
    }
    set_send_format(options, SendInputFormat::File, argv[index]);
    return true;
  }
  return false;
}

}  // namespace packet_probe::cli
