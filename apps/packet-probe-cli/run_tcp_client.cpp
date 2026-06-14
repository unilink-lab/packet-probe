#include "run_modes.hpp"

#include "packet_probe/tcp_direct_capture_session.hpp"

namespace packet_probe::cli {

int run_tcp_client(CliOptions const& options, StopRequested const& stop_requested) {
  auto recorder = make_recorder(options);
  auto pipeline = make_pipeline(options, *recorder);

  TcpDirectCaptureOptions capture_options;
  capture_options.host = options.host;
  capture_options.port = options.port;

  TcpDirectCaptureSession session(capture_options, [&](PacketEvent const& event) { pipeline.consume(event); });

  session.start();
  return run_sender_session(session, options.send_options, stop_requested);
}

}  // namespace packet_probe::cli
