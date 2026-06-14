#include "run_modes.hpp"

#include <chrono>
#include <thread>

#include "capture/tcp_proxy_capture_session.hpp"

namespace packet_probe::cli {

int run_tcp_proxy(CliOptions const& options, StopRequested const& stop_requested) {
  auto recorder = make_recorder(options);
  auto ipc_server = make_ipc_server(options);
  auto pipeline = make_pipeline(options, *recorder, ipc_server.get());

  TcpProxyConfig config;
  config.listen_host = options.listen_host;
  config.listen_port = options.listen_port;
  config.target_host = options.target_host;
  config.target_port = options.target_port;
  config.latency_enabled = options.latency;

  TcpProxyCaptureSession session(config, [&](PacketEvent const& event) { pipeline.consume(event); });

  session.start();
  while (!stop_requested() && !session.stopped()) {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }
  session.stop();
  return 0;
}

}  // namespace packet_probe::cli
