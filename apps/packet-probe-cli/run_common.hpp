#pragma once

#include <chrono>
#include <cstdint>
#include <functional>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#if defined(_WIN32)
#include <io.h>
#else
#include <unistd.h>
#endif

#include "cli_options.hpp"
#include "packet_probe/event_pipeline.hpp"
#include "packet_probe/frame_decoder_factory.hpp"
#include "packet_probe/hex_dump.hpp"
#include "packet_probe/ipc_event_server.hpp"
#include "packet_probe/jsonl_recorder.hpp"
#include "packet_probe/send_input_parser.hpp"

namespace packet_probe::cli {

using StopRequested = std::function<bool()>;

bool stdin_is_terminal();
std::vector<std::uint8_t> parse_send_line(std::string const& line, SendInputOptions const& send_options);
void print_event(PacketEvent const& event, bool hex_raw_enabled, bool hex_frame_enabled);
std::unique_ptr<JsonlRecorder> make_recorder(CliOptions const& options);
std::unique_ptr<IpcEventServer> make_ipc_server(CliOptions const& options);
EventPipeline make_pipeline(CliOptions const& options, JsonlRecorder& recorder, IpcEventServer* ipc_server);

template <typename Session>
int run_sender_session(Session& session, SendInputOptions const& send_options, StopRequested const& stop_requested) {
  if (send_options.format == SendInputFormat::File) {
    auto payload = read_binary_file(send_options.file_path);
    if (!session.send(std::move(payload))) {
      throw std::runtime_error("failed to send file payload");
    }
    session.stop();
    return 0;
  }

  auto const interactive_stdin = stdin_is_terminal();
  std::string line;
  while (!stop_requested() && !session.stopped() && std::getline(std::cin, line)) {
    auto payload = parse_send_line(line, send_options);
    if (!session.send(std::move(payload))) {
      std::cerr << "failed to send payload\n";
    }
  }

  while (!interactive_stdin && !stop_requested() && !session.stopped()) {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }

  if (!session.stopped()) {
    session.stop();
  }
  return 0;
}

}  // namespace packet_probe::cli
