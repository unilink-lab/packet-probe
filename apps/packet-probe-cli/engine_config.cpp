#include "engine_config.hpp"

#include <stdexcept>

#include "capture/serial_options.hpp"
#include "core/hex_dump.hpp"
#include "packet_probe/decoder/decoder_config.hpp"

namespace packet_probe::cli {

namespace {

std::string get_string(nlohmann::json const& config, char const* key, std::string const& fallback = "") {
  auto const it = config.find(key);
  if (it == config.end() || it->is_null()) return fallback;
  if (!it->is_string()) throw std::invalid_argument(std::string("config.") + key + " must be a string");
  return it->get<std::string>();
}

std::uint16_t get_port(nlohmann::json const& config, char const* key, std::uint16_t fallback = 0) {
  auto const it = config.find(key);
  if (it == config.end() || it->is_null()) return fallback;
  // Accept any non-negative JSON integer: nlohmann parses positive literals from wire
  // text as number_unsigned, but in-memory-constructed json objects (e.g. from a plain
  // `int` literal) are number_integer, so is_number_integer() (which covers both) is
  // the correct check rather than is_number_unsigned() alone.
  if (!it->is_number_integer()) throw std::invalid_argument(std::string("config.") + key + " must be a port number");
  auto const value = it->get<std::int64_t>();
  if (value < 0 || value > 65535) throw std::invalid_argument(std::string("config.") + key + " out of range");
  return static_cast<std::uint16_t>(value);
}

bool get_bool(nlohmann::json const& config, char const* key, bool fallback) {
  auto const it = config.find(key);
  if (it == config.end() || it->is_null()) return fallback;
  if (!it->is_boolean()) throw std::invalid_argument(std::string("config.") + key + " must be a boolean");
  return it->get<bool>();
}

}  // namespace

nlohmann::json engine_config_to_json(CliOptions const& options) {
  nlohmann::json config;
  config["mode"] = options.mode;
  config["host"] = options.host;
  config["port"] = options.port;
  config["serial_port"] = options.serial_port;
  config["baudrate"] = options.baudrate;
  config["data_bits"] = options.data_bits;
  config["stop_bits"] = options.stop_bits;
  config["parity"] = to_string(options.parity);
  config["flow_control"] = to_string(options.flow_control);
  config["listen_host"] = options.listen_host;
  config["listen_port"] = options.listen_port;
  config["bind_host"] = options.bind_host;
  config["bind_port"] = options.bind_port;
  config["target_host"] = options.target_host;
  config["target_port"] = options.target_port;
  config["log_path"] = options.log_path;
  config["hex_raw"] = options.hex_raw;
  config["hex_frame"] = options.hex_frame;
  config["latency"] = options.latency;

  nlohmann::json decoder;
  decoder["decoder"] = options.decoder_config.decoder;
  decoder["frame_size"] = options.decoder_config.frame_size;
  decoder["delimiter_hex"] = to_hex(options.decoder_config.delimiter, false);
  decoder["include_delimiter"] = options.decoder_config.include_delimiter;
  decoder["length_size"] = options.decoder_config.length_size;
  decoder["length_endian"] = options.decoder_config.length_endian;
  decoder["length_includes_header"] = options.decoder_config.length_includes_header;
  config["decoder"] = std::move(decoder);

  return config;
}

CliOptions engine_config_from_json(nlohmann::json const& config) {
  if (!config.is_object()) {
    throw std::invalid_argument("config must be a JSON object");
  }

  CliOptions options;
  options.mode = get_string(config, "mode");
  options.host = get_string(config, "host");
  options.port = get_port(config, "port");
  options.serial_port = get_string(config, "serial_port");

  auto const baudrate_it = config.find("baudrate");
  if (baudrate_it != config.end() && !baudrate_it->is_null()) {
    options.baudrate = parse_serial_baudrate(std::to_string(baudrate_it->get<std::uint64_t>()));
  }
  auto const data_bits_it = config.find("data_bits");
  if (data_bits_it != config.end() && !data_bits_it->is_null()) {
    options.data_bits = parse_serial_data_bits(std::to_string(data_bits_it->get<int>()));
  }
  auto const stop_bits_it = config.find("stop_bits");
  if (stop_bits_it != config.end() && !stop_bits_it->is_null()) {
    options.stop_bits = parse_serial_stop_bits(std::to_string(stop_bits_it->get<int>()));
  }
  options.parity = parse_serial_parity(get_string(config, "parity", "none"));
  options.flow_control = parse_serial_flow_control(get_string(config, "flow_control", "none"));

  options.listen_host = get_string(config, "listen_host");
  options.listen_port = get_port(config, "listen_port");
  options.bind_host = get_string(config, "bind_host", "0.0.0.0");
  options.bind_port = get_port(config, "bind_port");
  options.target_host = get_string(config, "target_host");
  options.target_port = get_port(config, "target_port");
  options.log_path = get_string(config, "log_path");
  options.hex_raw = get_bool(config, "hex_raw", false);
  options.hex_frame = get_bool(config, "hex_frame", false);
  options.latency = get_bool(config, "latency", true);

  auto const decoder_it = config.find("decoder");
  if (decoder_it != config.end() && !decoder_it->is_null()) {
    if (!decoder_it->is_object()) throw std::invalid_argument("config.decoder must be an object");
    auto const& decoder = *decoder_it;
    options.decoder_config.decoder = get_string(decoder, "decoder", "raw");
    auto const frame_size_it = decoder.find("frame_size");
    if (frame_size_it != decoder.end() && !frame_size_it->is_null()) {
      options.decoder_config.frame_size = frame_size_it->get<std::size_t>();
    }
    auto const delimiter_hex = get_string(decoder, "delimiter_hex");
    if (!delimiter_hex.empty()) {
      options.decoder_config.delimiter = parse_delimiter_bytes(delimiter_hex);
    }
    options.decoder_config.include_delimiter = get_bool(decoder, "include_delimiter", true);
    auto const length_size_it = decoder.find("length_size");
    if (length_size_it != decoder.end() && !length_size_it->is_null()) {
      options.decoder_config.length_size = length_size_it->get<std::size_t>();
    }
    options.decoder_config.length_endian = get_string(decoder, "length_endian", "big");
    options.decoder_config.length_includes_header = get_bool(decoder, "length_includes_header", false);
  }

  return options;
}

}  // namespace packet_probe::cli
