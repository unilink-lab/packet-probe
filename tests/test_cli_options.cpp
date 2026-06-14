#include <cassert>
#include <initializer_list>
#include <stdexcept>
#include <string>
#include <vector>

#include "../apps/packet-probe-cli/cli_options.hpp"

namespace {

bool throws_invalid_argument(auto fn) {
  try {
    fn();
  } catch (std::invalid_argument const&) {
    return true;
  }
  return false;
}

packet_probe::cli::CliOptions parse(std::initializer_list<char const*> args) {
  auto storage = std::vector<char const*>(args.begin(), args.end());
  return packet_probe::cli::parse_args(static_cast<int>(storage.size()), const_cast<char**>(storage.data()));
}

}  // namespace

int main() {
  auto defaults = parse({"packet-probe", "tcp-client", "--host", "127.0.0.1", "--port", "9000"});
  assert(defaults.send_options.format == packet_probe::SendInputFormat::Text);
  assert(defaults.send_options.file_path.empty());
  packet_probe::cli::validate_options(defaults);

  auto ipc = parse({"packet-probe", "udp", "--bind-host", "127.0.0.1", "--bind-port", "9000", "--ipc",
                    "/tmp/packet-probe.sock"});
  assert(ipc.ipc_path == "/tmp/packet-probe.sock");
  packet_probe::cli::validate_options(ipc);

  assert(throws_invalid_argument([] {
    (void)parse({"packet-probe", "tcp-client", "--host", "127.0.0.1", "--port", "9000", "--send-text",
                 "--send-hex"});
  }));

  assert(throws_invalid_argument([] {
    (void)parse({"packet-probe", "serial", "--port", "/dev/ttyUSB0", "--baudrate", "115200", "--send-file",
                 "command.bin", "--send-hex"});
  }));

  assert(throws_invalid_argument([] {
    (void)parse({"packet-probe", "serial", "--port", "/dev/ttyUSB0", "--baudrate", "115200", "--send-file"});
  }));

  auto file = parse({"packet-probe", "serial", "--port", "/dev/ttyUSB0", "--baudrate", "115200", "--send-file",
                     "command.bin"});
  assert(file.send_options.format == packet_probe::SendInputFormat::File);
  assert(file.send_options.file_path == "command.bin");
  packet_probe::cli::validate_options(file);

  assert(throws_invalid_argument([] {
    auto options = parse({"packet-probe", "udp", "--bind-host", "127.0.0.1", "--bind-port", "9000", "--send-hex"});
    packet_probe::cli::validate_options(options);
  }));

  assert(throws_invalid_argument([] {
    auto options =
        parse({"packet-probe", "udp", "--bind-host", "127.0.0.1", "--bind-port", "9000", "--target-host", "127.0.0.1"});
    packet_probe::cli::validate_options(options);
  }));

  assert(throws_invalid_argument([] {
    auto options = parse({"packet-probe", "udp", "--bind-host", "127.0.0.1", "--bind-port", "9000",
                          "--target-port", "9100"});
    packet_probe::cli::validate_options(options);
  }));

  assert(throws_invalid_argument([] {
    auto options = parse({"packet-probe", "udp", "--bind-host", "127.0.0.1", "--bind-port", "9000", "--send-file",
                          "command.bin"});
    packet_probe::cli::validate_options(options);
  }));

  auto udp_target = parse({"packet-probe", "udp", "--bind-host", "127.0.0.1", "--bind-port", "9000",
                           "--target-host", "127.0.0.1", "--target-port", "9100"});
  packet_probe::cli::validate_options(udp_target);

  return 0;
}
