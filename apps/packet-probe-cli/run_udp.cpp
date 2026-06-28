#include "run_modes.hpp"

#include "capture/udp_direct_capture_session.hpp"

namespace packet_probe::cli {

int run_udp(CliOptions const& options, StopRequested const& stop_requested) {
  auto seq_alloc = make_sequence_allocator();
  auto recorder = make_recorder(options);
  auto ipc_server = make_ipc_server(options);
  auto pipeline = make_pipeline(options, *recorder, ipc_server.get(), seq_alloc);

  UdpDirectCaptureOptions capture_options;
  capture_options.bind_host = options.bind_host;
  capture_options.bind_port = options.bind_port;
  capture_options.target_host = options.target_host;
  capture_options.target_port = options.target_port;

  UdpDirectCaptureSession session(capture_options, [&](PacketEvent const& event) { pipeline.consume(event); }, seq_alloc);

  install_ipc_send_handler(ipc_server.get(), session);
  session.start();
  return run_sender_session(session, options.send_options, stop_requested);
}

}  // namespace packet_probe::cli
