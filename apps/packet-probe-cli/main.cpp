#include <csignal>
#include <chrono>
#include <cstdint>
#include <exception>
#include <iostream>
#include <memory>
#include <optional>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#if defined(_WIN32)
#include <io.h>
#else
#include <unistd.h>
#endif

#include "packet_probe/hex_dump.hpp"
#include "packet_probe/jsonl_recorder.hpp"
#include "packet_probe/tcp_direct_capture_session.hpp"
#include "packet_probe/tcp_proxy_capture_session.hpp"
#include "packet_probe/version.hpp"

namespace {

std::sig_atomic_t g_stop_requested = 0;

void handle_signal(int) { g_stop_requested = 1; }

struct CliOptions {
  std::string mode;
  std::string host;
  std::uint16_t port = 0;
  std::string listen_host;
  std::uint16_t listen_port = 0;
  std::string target_host;
  std::uint16_t target_port = 0;
  std::string log_path;
  bool hex = false;
  bool latency = true;
  bool help = false;
  bool version = false;
};

void print_help(std::ostream& out) {
  out << "Usage:\n"
      << "  packet-probe [--help] [--version]\n"
      << "  packet-probe tcp-client --host <host> --port <port> [--log <path>] [--hex]\n"
      << "  packet-probe tcp-proxy --listen-host <host> --listen-port <port> "
         "--target-host <host> --target-port <port> [--log <path>] [--hex] [--latency]\n"
      << "\n"
      << "Modes:\n"
      << "  tcp-client    Connect directly to a TCP target device\n"
      << "  tcp-proxy     Listen locally and proxy one TCP client to a target device\n"
      << "\n"
      << "Options:\n"
      << "  --host <host>     Target host for tcp-client mode\n"
      << "  --port <port>     Target TCP port for tcp-client mode\n"
      << "  --listen-host <host>  Local listen host for tcp-proxy mode\n"
      << "  --listen-port <port>  Local listen port for tcp-proxy mode\n"
      << "  --target-host <host>  Target host for tcp-proxy mode\n"
      << "  --target-port <port>  Target port for tcp-proxy mode\n"
      << "  --log <path>      Write events as JSONL\n"
      << "  --hex             Print one-line hex output for raw byte events\n"
      << "  --latency         Enable heuristic request/response latency events\n"
      << "  --help            Show this help\n"
      << "  --version         Show version\n";
}

void print_tcp_proxy_help(std::ostream& out) {
  out << "Usage:\n"
      << "  packet-probe tcp-proxy --listen-host <host> --listen-port <port> "
         "--target-host <host> --target-port <port> [--log <path>] [--hex] [--latency]\n"
      << "\n"
      << "Options:\n"
      << "  --listen-host <host>  Local listen host\n"
      << "  --listen-port <port>  Local listen port\n"
      << "  --target-host <host>  Target device host\n"
      << "  --target-port <port>  Target device TCP port\n"
      << "  --log <path>          Write events as JSONL\n"
      << "  --hex                 Print one-line hex output for raw byte events\n"
      << "  --latency             Enable heuristic request/response latency events\n"
      << "  --help                Show this help\n";
}

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
    } else if (arg == "--hex") {
      options.hex = true;
    } else if (arg == "--latency") {
      options.latency = true;
    } else if (arg == "--host") {
      if (++i >= argc) {
        throw std::invalid_argument("--host requires a value");
      }
      options.host = argv[i];
    } else if (arg == "--port") {
      if (++i >= argc) {
        throw std::invalid_argument("--port requires a value");
      }
      options.port = parse_port(argv[i]);
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

std::vector<std::uint8_t> line_to_payload(std::string const& line) {
  return std::vector<std::uint8_t>(line.begin(), line.end());
}

bool stdin_is_terminal() {
#if defined(_WIN32)
  return _isatty(_fileno(stdin)) != 0;
#else
  return isatty(fileno(stdin)) != 0;
#endif
}

void print_event(packet_probe::PacketEvent const& event, bool hex_enabled) {
  if (event.type == packet_probe::EventType::RawBytes && hex_enabled) {
    auto direction = event.direction == packet_probe::Direction::AppToDevice ? "APP -> DEVICE" : "DEVICE -> APP";
    std::cout << packet_probe::format_event_line(event.timestamp_ns, direction, event.payload.size(), event.payload)
              << '\n';
    return;
  }

  if (event.type == packet_probe::EventType::Latency) {
    std::cout << "[latency] request=" << event.request_sequence << " response=" << event.response_sequence << ' '
              << event.latency_ns / 1000 << " us\n";
    return;
  }

  if (event.type == packet_probe::EventType::Error || event.type == packet_probe::EventType::StateChange) {
    std::cout << event.summary << '\n';
  }
}

int run_tcp_proxy(CliOptions const& options) {
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

  auto recorder = std::make_unique<packet_probe::JsonlRecorder>();
  if (!options.log_path.empty()) {
    recorder->open(options.log_path);
  }

  packet_probe::TcpProxyConfig config;
  config.listen_host = options.listen_host;
  config.listen_port = options.listen_port;
  config.target_host = options.target_host;
  config.target_port = options.target_port;
  config.latency_enabled = options.latency;

  packet_probe::TcpProxyCaptureSession session(config, [&](packet_probe::PacketEvent const& event) {
    recorder->record(event);
    print_event(event, options.hex);
  });

  session.start();
  while (!g_stop_requested && !session.stopped()) {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }
  session.stop();
  return 0;
}

int run_tcp_client(CliOptions const& options) {
  if (options.host.empty()) {
    throw std::invalid_argument("tcp-client requires --host");
  }
  if (options.port == 0) {
    throw std::invalid_argument("tcp-client requires --port");
  }

  auto recorder = std::make_unique<packet_probe::JsonlRecorder>();
  if (!options.log_path.empty()) {
    recorder->open(options.log_path);
  }

  packet_probe::TcpDirectCaptureOptions capture_options;
  capture_options.host = options.host;
  capture_options.port = options.port;

  packet_probe::TcpDirectCaptureSession session(
      capture_options, [&](packet_probe::PacketEvent const& event) {
        recorder->record(event);
        print_event(event, options.hex);
      });

  session.start();

  auto const interactive_stdin = stdin_is_terminal();
  std::string line;
  while (!g_stop_requested && !session.stopped() && std::getline(std::cin, line)) {
    auto payload = line_to_payload(line);
    if (!session.send(std::move(payload))) {
      std::cerr << "failed to send payload\n";
    }
  }

  while (!interactive_stdin && !g_stop_requested && !session.stopped()) {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }

  session.stop();
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  std::signal(SIGINT, handle_signal);
  std::signal(SIGTERM, handle_signal);

  try {
    auto const options = parse_args(argc, argv);
    if (options.help || argc == 1) {
      if (options.mode == "tcp-proxy") {
        print_tcp_proxy_help(std::cout);
      } else {
        print_help(std::cout);
      }
      return 0;
    }
    if (options.version) {
      std::cout << "packet-probe " << PACKET_PROBE_VERSION << '\n';
      return 0;
    }
    if (options.mode == "tcp-client") {
      return run_tcp_client(options);
    }
    if (options.mode == "tcp-proxy") {
      return run_tcp_proxy(options);
    }

    throw std::invalid_argument("unknown or missing mode: " + options.mode);
  } catch (std::exception const& ex) {
    std::cerr << "packet-probe: " << ex.what() << '\n';
    std::cerr << "Run 'packet-probe --help' for usage.\n";
    return 2;
  }
}
