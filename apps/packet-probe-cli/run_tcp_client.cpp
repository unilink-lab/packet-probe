#include "run_modes.hpp"

#include "capture/tcp_direct_capture_session.hpp"

namespace packet_probe::cli {

int run_tcp_client(CliOptions const& options, StopRequested const& stop_requested) {
  auto seq_alloc = make_sequence_allocator();
  auto recorder = make_recorder(options);
  auto ipc_server = make_ipc_server(options);
  auto pipeline = make_pipeline(options, *recorder, ipc_server.get(), seq_alloc);

  TcpDirectCaptureOptions capture_options;
  capture_options.host = options.host;
  capture_options.port = options.port;

  TcpDirectCaptureSession session(capture_options, [&](PacketEvent const& event) { pipeline.consume(event); }, seq_alloc);

  install_ipc_send_handler(ipc_server.get(), session);
  session.start();
  return run_sender_session(session, options.send_options, stop_requested, ipc_server.get());
}

}  // namespace packet_probe::cli
