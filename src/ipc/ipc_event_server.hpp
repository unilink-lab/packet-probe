#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <string_view>

#include "packet_probe/core/packet_event.hpp"

namespace packet_probe {

// Mirrors unilink::ClientId without exposing unilink types in this public-ish header.
using IpcClientId = std::uint64_t;

struct IpcServerOptions {
  std::string socket_path;
  std::string tool_name = "packet-probe";
  std::string log_schema = "packet-probe.log.v1";
  std::string event_schema = "packet-probe.event.v1";
};

class IpcEventServer {
 public:
  using CommandHandler = std::function<void(IpcClientId client_id, std::string_view json_line)>;

  explicit IpcEventServer(IpcServerOptions options);
  ~IpcEventServer();

  IpcEventServer(IpcEventServer const&) = delete;
  IpcEventServer& operator=(IpcEventServer const&) = delete;

  void start();
  void stop();
  bool running() const;

  void broadcast_metadata();
  void broadcast(PacketEvent const& event);

  // Broadcasts a single arbitrary JSONL line (e.g. an engine "status" message) to
  // every connected client. Appends the trailing newline.
  void broadcast_raw(std::string const& line);

  // Sends a single JSONL line to one client (e.g. a command result/ack). Appends the
  // trailing newline. Returns false if the client is unknown or the write fails.
  bool send_to_client(IpcClientId client_id, std::string const& line);

  void set_command_handler(CommandHandler handler);

 private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace packet_probe
