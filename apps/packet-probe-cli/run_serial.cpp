#include "run_modes.hpp"

#include "capture/serial_direct_capture_session.hpp"

namespace packet_probe::cli {

int run_serial(CliOptions const& options, StopRequested const& stop_requested) {
  auto seq_alloc = make_sequence_allocator();
  auto recorder = make_recorder(options);
  auto ipc_server = make_ipc_server(options);
  auto pipeline = make_pipeline(options, *recorder, ipc_server.get(), seq_alloc);

  SerialCaptureOptions capture_options;
  capture_options.port = options.serial_port;
  capture_options.baudrate = options.baudrate;
  capture_options.data_bits = options.data_bits;
  capture_options.stop_bits = options.stop_bits;
  capture_options.parity = options.parity;
  capture_options.flow_control = options.flow_control;

  SerialDirectCaptureSession session(capture_options, [&](PacketEvent const& event) { pipeline.consume(event); }, seq_alloc);

  install_ipc_send_handler(ipc_server.get(), session);
  session.start();
  return run_sender_session(session, options.send_options, stop_requested, ipc_server.get());
}

}  // namespace packet_probe::cli
