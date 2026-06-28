#pragma once

#include <functional>
#include <memory>
#include <string>
#include <string_view>

#include "packet_probe/core/packet_event.hpp"

namespace packet_probe {

struct IpcServerOptions {
  std::string socket_path;
  std::string tool_name = "packet-probe";
  std::string log_schema = "packet-probe.log.v1";
  std::string event_schema = "packet-probe.event.v1";
};

class IpcEventServer {
 public:
  using CommandHandler = std::function<void(std::string_view json_line)>;

  explicit IpcEventServer(IpcServerOptions options);
  ~IpcEventServer();

  IpcEventServer(IpcEventServer const&) = delete;
  IpcEventServer& operator=(IpcEventServer const&) = delete;

  void start();
  void stop();
  bool running() const;

  void broadcast_metadata();
  void broadcast(PacketEvent const& event);

  void set_command_handler(CommandHandler handler);

 private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace packet_probe
