#pragma once

#include <cstdint>
#include <string>

#include "packet_probe/decoder/decoder_config.hpp"
#include "core/send_input.hpp"
#include "capture/serial_options.hpp"

namespace packet_probe::cli {

struct CliOptions {
  std::string mode;
  std::string host;
  std::uint16_t port = 0;
  std::string serial_port;
  std::uint32_t baudrate = 115200;
  std::uint8_t data_bits = 8;
  std::uint8_t stop_bits = 1;
  SerialParity parity = SerialParity::None;
  SerialFlowControl flow_control = SerialFlowControl::None;
  std::string listen_host;
  std::uint16_t listen_port = 0;
  std::string bind_host = "0.0.0.0";
  std::uint16_t bind_port = 0;
  std::string target_host;
  std::uint16_t target_port = 0;
  std::string log_path;
  std::string ipc_path;
  DecoderConfig decoder_config;
  SendInputOptions send_options;
  int send_option_count = 0;
  bool hex_raw = false;
  bool hex_frame = false;
  bool latency = true;
  bool help = false;
  bool version = false;
};

std::uint16_t parse_port(std::string const& value);
CliOptions parse_args(int argc, char** argv);
void validate_options(CliOptions const& options);

}  // namespace packet_probe::cli
