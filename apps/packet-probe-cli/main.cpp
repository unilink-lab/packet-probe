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
#include "packet_probe/event_pipeline.hpp"
#include "packet_probe/frame_decoder_factory.hpp"
#include "packet_probe/jsonl_recorder.hpp"
#include "packet_probe/serial_direct_capture_session.hpp"
#include "packet_probe/tcp_direct_capture_session.hpp"
#include "packet_probe/tcp_proxy_capture_session.hpp"
#include "packet_probe/udp_direct_capture_session.hpp"
#include "packet_probe/version.hpp"

namespace {

std::sig_atomic_t g_stop_requested = 0;

void handle_signal(int) { g_stop_requested = 1; }

struct CliOptions {
  std::string mode;
  std::string host;
  std::uint16_t port = 0;
  std::string serial_port;
  std::uint32_t baudrate = 115200;
  std::uint8_t data_bits = 8;
  std::uint8_t stop_bits = 1;
  packet_probe::SerialParity parity = packet_probe::SerialParity::None;
  packet_probe::SerialFlowControl flow_control = packet_probe::SerialFlowControl::None;
  std::string listen_host;
  std::uint16_t listen_port = 0;
  std::string bind_host = "0.0.0.0";
  std::uint16_t bind_port = 0;
  std::string target_host;
  std::uint16_t target_port = 0;
  std::string log_path;
  packet_probe::DecoderConfig decoder_config;
  bool hex_raw = false;
  bool hex_frame = false;
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
      << "  packet-probe serial --port <path> --baudrate <rate> [--log <path>] [--hex]\n"
      << "  packet-probe udp --bind-host <host> --bind-port <port> [--target-host <host>] "
         "[--target-port <port>] [--log <path>] [--hex]\n"
      << "\n"
      << "Modes:\n"
      << "  tcp-client    Connect directly to a TCP target device\n"
      << "  tcp-proxy     Listen locally and proxy one TCP client to a target device\n"
      << "  serial        Connect directly to a serial target device\n"
      << "  udp           Bind a UDP socket and inspect datagrams\n"
      << "\n"
      << "Options:\n"
      << "  --host <host>     Target host for tcp-client mode\n"
      << "  --port <port>     Target TCP port for tcp-client mode\n"
      << "  --listen-host <host>  Local listen host for tcp-proxy mode\n"
      << "  --listen-port <port>  Local listen port for tcp-proxy mode\n"
      << "  --bind-host <host>    UDP bind host, default: 0.0.0.0\n"
      << "  --bind-port <port>    UDP bind port\n"
      << "  --target-host <host>  Target host for tcp-proxy or UDP send mode\n"
      << "  --target-port <port>  Target port for tcp-proxy or UDP send mode\n"
      << "  --baudrate <rate>     Serial baudrate for serial mode\n"
      << "  --data-bits <5|6|7|8> Serial data bits, default: 8\n"
      << "  --stop-bits <1|2>     Serial stop bits, default: 1\n"
      << "  --parity <none|odd|even>  Serial parity, default: none\n"
      << "  --flow-control <none|software|hardware>  Serial flow control, default: none\n"
      << "  --decoder <raw|fixed|delimiter|length-prefix>  Frame decoder, default: raw\n"
      << "  --frame-size <bytes>  Fixed-size frame length\n"
      << "  --delimiter <hex|CRLF|LF>  Delimiter frame boundary\n"
      << "  --include-delimiter   Include delimiter in delimiter frames, default: enabled\n"
      << "  --length-size <1|2|4> Length-prefix field size, default: 2\n"
      << "  --length-endian <little|big>  Length-prefix endian, default: big\n"
      << "  --length-includes-header  Length includes the prefix bytes\n"
      << "  --log <path>      Write events as JSONL\n"
      << "  --hex             Print one-line hex output for raw byte events\n"
      << "  --hex-raw         Print one-line hex output for raw byte events\n"
      << "  --hex-frame       Print one-line hex output for frame events\n"
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
      << "  --decoder <raw|fixed|delimiter|length-prefix>\n"
      << "  --log <path>          Write events as JSONL\n"
      << "  --hex                 Print one-line hex output for raw byte events\n"
      << "  --hex-frame           Print one-line hex output for frame events\n"
      << "  --latency             Enable heuristic request/response latency events\n"
      << "  --help                Show this help\n";
}

void print_serial_help(std::ostream& out) {
  out << "Usage:\n"
      << "  packet-probe serial --port <path> --baudrate <rate> [options]\n"
      << "\n"
      << "Options:\n"
      << "  --port <path>              Serial port path, e.g. /dev/ttyUSB0 or COM3\n"
      << "  --baudrate <rate>          Serial baudrate, e.g. 9600, 115200, 921600\n"
      << "  --data-bits <5|6|7|8>      Data bits, default: 8\n"
      << "  --stop-bits <1|2>          Stop bits, default: 1\n"
      << "  --parity <none|odd|even>   Parity, default: none\n"
      << "  --flow-control <none|software|hardware>\n"
      << "  --decoder <raw|fixed|delimiter|length-prefix>\n"
      << "  --delimiter <hex|CRLF|LF>  Delimiter frame boundary\n"
      << "  --log <path>               Write events as JSONL\n"
      << "  --hex                      Print one-line hex output for raw byte events\n"
      << "  --hex-frame                Print one-line hex output for frame events\n"
      << "  --help                     Show this help\n";
}

void print_udp_help(std::ostream& out) {
  out << "Usage:\n"
      << "  packet-probe udp --bind-host <host> --bind-port <port> [options]\n"
      << "\n"
      << "Options:\n"
      << "  --bind-host <host>         UDP bind host, default: 0.0.0.0\n"
      << "  --bind-port <port>         UDP bind port\n"
      << "  --target-host <host>       Optional UDP target host for stdin sends\n"
      << "  --target-port <port>       Optional UDP target port for stdin sends\n"
      << "  --decoder <raw|fixed|delimiter|length-prefix>\n"
      << "  --log <path>               Write events as JSONL\n"
      << "  --hex                      Print one-line hex output for raw byte events\n"
      << "  --hex-frame                Print one-line hex output for frame events\n"
      << "  --help                     Show this help\n";
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
    } else if (arg == "--hex" || arg == "--hex-raw") {
      options.hex_raw = true;
    } else if (arg == "--hex-frame") {
      options.hex_frame = true;
    } else if (arg == "--latency") {
      options.latency = true;
    } else if (arg == "--decoder") {
      if (++i >= argc) {
        throw std::invalid_argument("--decoder requires a value");
      }
      options.decoder_config.decoder = argv[i];
    } else if (arg == "--frame-size") {
      if (++i >= argc) {
        throw std::invalid_argument("--frame-size requires a value");
      }
      options.decoder_config.frame_size = std::stoul(argv[i]);
    } else if (arg == "--delimiter") {
      if (++i >= argc) {
        throw std::invalid_argument("--delimiter requires a value");
      }
      options.decoder_config.delimiter = packet_probe::parse_delimiter_bytes(argv[i]);
    } else if (arg == "--include-delimiter") {
      options.decoder_config.include_delimiter = true;
    } else if (arg == "--length-size") {
      if (++i >= argc) {
        throw std::invalid_argument("--length-size requires a value");
      }
      options.decoder_config.length_size = std::stoul(argv[i]);
    } else if (arg == "--length-endian") {
      if (++i >= argc) {
        throw std::invalid_argument("--length-endian requires a value");
      }
      options.decoder_config.length_endian = argv[i];
    } else if (arg == "--length-includes-header") {
      options.decoder_config.length_includes_header = true;
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
      options.baudrate = packet_probe::parse_serial_baudrate(argv[i]);
    } else if (arg == "--data-bits") {
      if (++i >= argc) {
        throw std::invalid_argument("--data-bits requires a value");
      }
      options.data_bits = packet_probe::parse_serial_data_bits(argv[i]);
    } else if (arg == "--stop-bits") {
      if (++i >= argc) {
        throw std::invalid_argument("--stop-bits requires a value");
      }
      options.stop_bits = packet_probe::parse_serial_stop_bits(argv[i]);
    } else if (arg == "--parity") {
      if (++i >= argc) {
        throw std::invalid_argument("--parity requires a value");
      }
      options.parity = packet_probe::parse_serial_parity(argv[i]);
    } else if (arg == "--flow-control") {
      if (++i >= argc) {
        throw std::invalid_argument("--flow-control requires a value");
      }
      options.flow_control = packet_probe::parse_serial_flow_control(argv[i]);
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

template <typename Session>
int run_line_sender_session(Session& session) {
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

void print_event(packet_probe::PacketEvent const& event, bool hex_raw_enabled, bool hex_frame_enabled) {
  if (event.type == packet_probe::EventType::RawBytes && hex_raw_enabled) {
    auto direction = event.direction == packet_probe::Direction::AppToDevice ? "APP -> DEVICE" : "DEVICE -> APP";
    std::cout << packet_probe::format_event_line(event.timestamp_ns, direction, event.payload.size(), event.payload)
              << '\n';
    return;
  }

  if (event.type == packet_probe::EventType::Frame && hex_frame_enabled) {
    auto direction = event.direction == packet_probe::Direction::AppToDevice ? "APP -> DEVICE" : "DEVICE -> APP";
    std::cout << "[frame] parent=" << event.parent_sequence << ' ' << direction << ' ' << event.payload.size()
              << " bytes";
    auto const hex = packet_probe::to_hex(event.payload, true);
    if (!hex.empty()) {
      std::cout << "  " << hex;
    }
    std::cout << '\n';
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

std::unique_ptr<packet_probe::JsonlRecorder> make_recorder(CliOptions const& options) {
  auto recorder = std::make_unique<packet_probe::JsonlRecorder>();
  if (!options.log_path.empty()) {
    recorder->open(options.log_path);
  }
  return recorder;
}

packet_probe::EventPipeline make_pipeline(CliOptions const& options, packet_probe::JsonlRecorder& recorder) {
  (void)packet_probe::create_frame_decoder(options.decoder_config);
  return packet_probe::EventPipeline(
      packet_probe::make_frame_decoder_factory(options.decoder_config),
      [&](packet_probe::PacketEvent const& event) {
        recorder.record(event);
        print_event(event, options.hex_raw, options.hex_frame);
      });
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

  auto recorder = make_recorder(options);
  auto pipeline = make_pipeline(options, *recorder);

  packet_probe::TcpProxyConfig config;
  config.listen_host = options.listen_host;
  config.listen_port = options.listen_port;
  config.target_host = options.target_host;
  config.target_port = options.target_port;
  config.latency_enabled = options.latency;

  packet_probe::TcpProxyCaptureSession session(config, [&](packet_probe::PacketEvent const& event) {
    pipeline.consume(event);
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

  auto recorder = make_recorder(options);
  auto pipeline = make_pipeline(options, *recorder);

  packet_probe::TcpDirectCaptureOptions capture_options;
  capture_options.host = options.host;
  capture_options.port = options.port;

  packet_probe::TcpDirectCaptureSession session(
      capture_options, [&](packet_probe::PacketEvent const& event) {
        pipeline.consume(event);
      });

  session.start();
  return run_line_sender_session(session);
}

int run_serial(CliOptions const& options) {
  if (options.serial_port.empty()) {
    throw std::invalid_argument("serial requires --port");
  }
  if (options.baudrate == 0) {
    throw std::invalid_argument("serial requires --baudrate");
  }

  auto recorder = make_recorder(options);
  auto pipeline = make_pipeline(options, *recorder);

  packet_probe::SerialCaptureOptions capture_options;
  capture_options.port = options.serial_port;
  capture_options.baudrate = options.baudrate;
  capture_options.data_bits = options.data_bits;
  capture_options.stop_bits = options.stop_bits;
  capture_options.parity = options.parity;
  capture_options.flow_control = options.flow_control;

  packet_probe::SerialDirectCaptureSession session(
      capture_options, [&](packet_probe::PacketEvent const& event) {
        pipeline.consume(event);
      });

  session.start();
  return run_line_sender_session(session);
}

int run_udp(CliOptions const& options) {
  if (options.bind_host.empty()) {
    throw std::invalid_argument("udp requires --bind-host");
  }
  if (options.bind_port == 0) {
    throw std::invalid_argument("udp requires --bind-port");
  }

  auto recorder = make_recorder(options);
  auto pipeline = make_pipeline(options, *recorder);

  packet_probe::UdpDirectCaptureOptions capture_options;
  capture_options.bind_host = options.bind_host;
  capture_options.bind_port = options.bind_port;
  capture_options.target_host = options.target_host;
  capture_options.target_port = options.target_port;

  packet_probe::UdpDirectCaptureSession session(
      capture_options, [&](packet_probe::PacketEvent const& event) {
        pipeline.consume(event);
      });

  session.start();
  return run_line_sender_session(session);
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
      } else if (options.mode == "serial") {
        print_serial_help(std::cout);
      } else if (options.mode == "udp") {
        print_udp_help(std::cout);
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
    if (options.mode == "serial") {
      return run_serial(options);
    }
    if (options.mode == "udp") {
      return run_udp(options);
    }

    throw std::invalid_argument("unknown or missing mode: " + options.mode);
  } catch (std::exception const& ex) {
    std::cerr << "packet-probe: " << ex.what() << '\n';
    std::cerr << "Run 'packet-probe --help' for usage.\n";
    return 2;
  }
}
