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
#include "core/event_pipeline.hpp"
#include "decoder/frame_decoder_factory.hpp"
#include "core/hex_dump.hpp"
#include "ipc/ipc_event_server.hpp"
#include "recorder/jsonl_recorder.hpp"
#include "core/send_input_parser.hpp"
#include "packet_probe/core/sequence_allocator.hpp"

namespace packet_probe::cli {

using StopRequested = std::function<bool()>;

bool stdin_is_terminal();
std::vector<std::uint8_t> parse_send_line(std::string const& line, SendInputOptions const& send_options);
void print_event(PacketEvent const& event, bool hex_raw_enabled, bool hex_frame_enabled);
std::unique_ptr<JsonlRecorder> make_recorder(CliOptions const& options);
std::unique_ptr<IpcEventServer> make_ipc_server(CliOptions const& options);
EventPipeline make_pipeline(CliOptions const& options, JsonlRecorder& recorder, IpcEventServer* ipc_server,
                            SharedSequenceAllocator seq_alloc);

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

namespace {

// Extract a string field value from a minimal JSON object.
// Only handles simple {"key":"value"} patterns without nesting or escaping.
inline std::string extract_json_string_field(std::string_view line, std::string_view key) {
  std::string pattern;
  pattern.reserve(key.size() + 4);
  pattern += '"';
  pattern += key;
  pattern += "\":\"";
  auto pos = line.find(pattern);
  if (pos == std::string_view::npos) return {};
  pos += pattern.size();
  auto end = line.find('"', pos);
  if (end == std::string_view::npos) return {};
  return std::string(line.substr(pos, end - pos));
}

}  // namespace

// Registers an IPC command handler that routes {"command":"send","payload_hex":"..."} to session.send().
template <typename Session>
void install_ipc_send_handler(IpcEventServer* ipc_server, Session& session) {
  if (!ipc_server) return;
  ipc_server->set_command_handler([&session](std::string_view line) {
    if (extract_json_string_field(line, "command") != "send") return;
    auto hex = extract_json_string_field(line, "payload_hex");
    if (hex.empty()) return;
    try {
      session.send(parse_hex_payload(hex));
    } catch (...) {
    }
  });
}

}  // namespace packet_probe::cli
