#include "cli_options.hpp"

#include <stdexcept>

#include "cli_decoder_options.hpp"
#include "cli_send_options.hpp"

namespace packet_probe::cli {

std::uint16_t parse_port(std::string const& value) {
  std::size_t parsed = 0;
  auto port = std::stoul(value, &parsed, 10);
  if (parsed != value.size() || port == 0 || port > 65535) {
    throw std::invalid_argument("invalid --port value: " + value);
  }
  return static_cast<std::uint16_t>(port);
}

CliOptions parse_args(int argc, char** argv) {
  CliOptions options;
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--help") {
      options.help = true;
    } else if (arg == "--version") {
      options.version = true;
    } else if (arg == "--hex" || arg == "--hex-raw") {
      options.hex_raw = true;
    } else if (arg == "--hex-frame") {
      options.hex_frame = true;
    } else if (arg == "--latency") {
      options.latency = true;
    } else if (parse_send_option(options, arg, i, argc, argv)) {
    } else if (parse_decoder_option(options, arg, i, argc, argv)) {
    } else if (arg == "--host") {
      if (++i >= argc) {
        throw std::invalid_argument("--host requires a value");
      }
      options.host = argv[i];
    } else if (arg == "--port") {
      if (++i >= argc) {
        throw std::invalid_argument("--port requires a value");
      }
      if (options.mode == "serial") {
        options.serial_port = argv[i];
      } else {
        options.port = parse_port(argv[i]);
      }
    } else if (arg == "--baudrate") {
      if (++i >= argc) {
        throw std::invalid_argument("--baudrate requires a value");
      }
      options.baudrate = parse_serial_baudrate(argv[i]);
    } else if (arg == "--data-bits") {
      if (++i >= argc) {
        throw std::invalid_argument("--data-bits requires a value");
      }
      options.data_bits = parse_serial_data_bits(argv[i]);
    } else if (arg == "--stop-bits") {
      if (++i >= argc) {
        throw std::invalid_argument("--stop-bits requires a value");
      }
      options.stop_bits = parse_serial_stop_bits(argv[i]);
    } else if (arg == "--parity") {
      if (++i >= argc) {
        throw std::invalid_argument("--parity requires a value");
      }
      options.parity = parse_serial_parity(argv[i]);
    } else if (arg == "--flow-control") {
      if (++i >= argc) {
        throw std::invalid_argument("--flow-control requires a value");
      }
      options.flow_control = parse_serial_flow_control(argv[i]);
    } else if (arg == "--listen-host") {
      if (++i >= argc) {
        throw std::invalid_argument("--listen-host requires a value");
      }
      options.listen_host = argv[i];
    } else if (arg == "--listen-port") {
      if (++i >= argc) {
        throw std::invalid_argument("--listen-port requires a value");
      }
      options.listen_port = parse_port(argv[i]);
    } else if (arg == "--bind-host") {
      if (++i >= argc) {
        throw std::invalid_argument("--bind-host requires a value");
      }
      options.bind_host = argv[i];
    } else if (arg == "--bind-port") {
      if (++i >= argc) {
        throw std::invalid_argument("--bind-port requires a value");
      }
      options.bind_port = parse_port(argv[i]);
    } else if (arg == "--target-host") {
      if (++i >= argc) {
        throw std::invalid_argument("--target-host requires a value");
      }
      options.target_host = argv[i];
    } else if (arg == "--target-port") {
      if (++i >= argc) {
        throw std::invalid_argument("--target-port requires a value");
      }
      options.target_port = parse_port(argv[i]);
    } else if (arg == "--log") {
      if (++i >= argc) {
        throw std::invalid_argument("--log requires a value");
      }
      options.log_path = argv[i];
    } else if (arg == "--ipc") {
      if (++i >= argc) {
        throw std::invalid_argument("--ipc requires a value");
      }
      options.ipc_path = argv[i];
    } else if (!arg.empty() && arg[0] == '-') {
      throw std::invalid_argument("unknown option: " + arg);
    } else if (options.mode.empty()) {
      options.mode = arg;
    } else {
      throw std::invalid_argument("unexpected argument: " + arg);
    }
  }
  return options;
}

void validate_options(CliOptions const& options) {
  if (options.mode == "engine") {
    if (options.ipc_path.empty()) {
      throw std::invalid_argument("engine requires --ipc");
    }
    return;
  }
  if (options.mode == "tcp-client") {
    if (options.host.empty()) {
      throw std::invalid_argument("tcp-client requires --host");
    }
    if (options.port == 0) {
      throw std::invalid_argument("tcp-client requires --port");
    }
    return;
  }
  if (options.mode == "tcp-server") {
    if (options.listen_host.empty()) {
      throw std::invalid_argument("tcp-server requires --listen-host");
    }
    if (options.listen_port == 0) {
      throw std::invalid_argument("tcp-server requires --listen-port");
    }
    return;
  }
  if (options.mode == "tcp-proxy") {
    if (options.listen_host.empty()) {
      throw std::invalid_argument("tcp-proxy requires --listen-host");
    }
    if (options.listen_port == 0) {
      throw std::invalid_argument("tcp-proxy requires --listen-port");
    }
    if (options.target_host.empty()) {
      throw std::invalid_argument("tcp-proxy requires --target-host");
    }
    if (options.target_port == 0) {
      throw std::invalid_argument("tcp-proxy requires --target-port");
    }
    return;
  }
  if (options.mode == "serial") {
    if (options.serial_port.empty()) {
      throw std::invalid_argument("serial requires --port");
    }
    if (options.baudrate == 0) {
      throw std::invalid_argument("serial requires --baudrate");
    }
    return;
  }
  if (options.mode == "udp") {
    if (options.bind_host.empty()) {
      throw std::invalid_argument("udp requires --bind-host");
    }
    if (options.bind_port == 0) {
      throw std::invalid_argument("udp requires --bind-port");
    }
    auto const has_target_host = !options.target_host.empty();
    auto const has_target_port = options.target_port != 0;
    if (has_target_host != has_target_port) {
      throw std::invalid_argument("udp target requires both --target-host and --target-port");
    }
    if (options.send_option_count > 0 && (!has_target_host || !has_target_port)) {
      throw std::invalid_argument("udp send input requires --target-host and --target-port");
    }
    return;
  }
  throw std::invalid_argument("unknown or missing mode: " + options.mode);
}

}  // namespace packet_probe::cli
