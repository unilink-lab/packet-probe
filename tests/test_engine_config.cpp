#include <cassert>
#include <iostream>
#include <string>

#include "engine_config.hpp"

#define TEST_ASSERT(cond, msg)                                                                    \
  if (!(cond)) {                                                                                  \
    std::cerr << "Assertion failed: " << #cond << " - " << msg << std::endl;                      \
    std::exit(1);                                                                                 \
  }

using packet_probe::cli::CliOptions;
using packet_probe::cli::engine_config_from_json;
using packet_probe::cli::engine_config_to_json;

namespace {

void test_udp_roundtrip() {
  CliOptions options;
  options.mode = "udp";
  options.bind_host = "0.0.0.0";
  options.bind_port = 19000;
  options.target_host = "127.0.0.1";
  options.target_port = 19085;
  options.hex_raw = true;
  options.latency = false;
  options.decoder_config.decoder = "delimiter";
  options.decoder_config.delimiter = {0x0D, 0x0A};
  options.decoder_config.include_delimiter = false;

  auto const json = engine_config_to_json(options);
  auto const roundtripped = engine_config_from_json(json);

  TEST_ASSERT(roundtripped.mode == "udp", "mode preserved");
  TEST_ASSERT(roundtripped.bind_host == "0.0.0.0", "bind_host preserved");
  TEST_ASSERT(roundtripped.bind_port == 19000, "bind_port preserved");
  TEST_ASSERT(roundtripped.target_host == "127.0.0.1", "target_host preserved");
  TEST_ASSERT(roundtripped.target_port == 19085, "target_port preserved");
  TEST_ASSERT(roundtripped.hex_raw == true, "hex_raw preserved");
  TEST_ASSERT(roundtripped.latency == false, "latency preserved");
  TEST_ASSERT(roundtripped.decoder_config.decoder == "delimiter", "decoder kind preserved");
  TEST_ASSERT((roundtripped.decoder_config.delimiter == std::vector<std::uint8_t>{0x0D, 0x0A}), "delimiter bytes preserved");
  TEST_ASSERT(roundtripped.decoder_config.include_delimiter == false, "include_delimiter preserved");
}

void test_serial_roundtrip() {
  CliOptions options;
  options.mode = "serial";
  options.serial_port = "/dev/ttyUSB0";
  options.baudrate = 921600;
  options.data_bits = 7;
  options.stop_bits = 2;
  options.parity = packet_probe::SerialParity::Even;
  options.flow_control = packet_probe::SerialFlowControl::Hardware;

  auto const json = engine_config_to_json(options);
  auto const roundtripped = engine_config_from_json(json);

  TEST_ASSERT(roundtripped.mode == "serial", "mode preserved");
  TEST_ASSERT(roundtripped.serial_port == "/dev/ttyUSB0", "serial_port preserved");
  TEST_ASSERT(roundtripped.baudrate == 921600, "baudrate preserved");
  TEST_ASSERT(roundtripped.data_bits == 7, "data_bits preserved");
  TEST_ASSERT(roundtripped.stop_bits == 2, "stop_bits preserved");
  TEST_ASSERT(roundtripped.parity == packet_probe::SerialParity::Even, "parity preserved");
  TEST_ASSERT(roundtripped.flow_control == packet_probe::SerialFlowControl::Hardware, "flow_control preserved");
}

void test_tcp_proxy_roundtrip() {
  CliOptions options;
  options.mode = "tcp-proxy";
  options.listen_host = "127.0.0.1";
  options.listen_port = 19000;
  options.target_host = "127.0.0.1";
  options.target_port = 19085;
  options.latency = true;

  auto const json = engine_config_to_json(options);
  auto const roundtripped = engine_config_from_json(json);

  TEST_ASSERT(roundtripped.mode == "tcp-proxy", "mode preserved");
  TEST_ASSERT(roundtripped.listen_host == "127.0.0.1", "listen_host preserved");
  TEST_ASSERT(roundtripped.listen_port == 19000, "listen_port preserved");
  TEST_ASSERT(roundtripped.target_host == "127.0.0.1", "target_host preserved");
  TEST_ASSERT(roundtripped.target_port == 19085, "target_port preserved");
}

void test_defaults_on_missing_fields() {
  nlohmann::json config;
  config["mode"] = "udp";
  config["bind_port"] = 19000;

  auto const options = engine_config_from_json(config);
  TEST_ASSERT(options.mode == "udp", "mode preserved");
  TEST_ASSERT(options.bind_host == "0.0.0.0", "bind_host defaults to 0.0.0.0");
  TEST_ASSERT(options.bind_port == 19000, "bind_port preserved");
  TEST_ASSERT(options.decoder_config.decoder == "raw", "decoder defaults to raw");
  TEST_ASSERT(options.latency == true, "latency defaults to true");
}

void test_rejects_non_object() {
  bool threw = false;
  try {
    engine_config_from_json(nlohmann::json::array());
  } catch (std::exception const&) {
    threw = true;
  }
  TEST_ASSERT(threw, "non-object config must be rejected");
}

}  // namespace

int main() {
  test_udp_roundtrip();
  test_serial_roundtrip();
  test_tcp_proxy_roundtrip();
  test_defaults_on_missing_fields();
  test_rejects_non_object();
  std::cout << "All engine_config tests passed!" << std::endl;
  return 0;
}
