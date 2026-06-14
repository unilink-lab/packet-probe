#pragma once

#include <memory>
#include <string>

#include "packet_probe/packet_event.hpp"

namespace packet_probe {

struct IpcServerOptions {
  std::string socket_path;
  std::string tool_name = "packet-probe";
  std::string log_schema = "packet-probe.log.v1";
  std::string event_schema = "packet-probe.event.v1";
};

class IpcEventServer {
 public:
  explicit IpcEventServer(IpcServerOptions options);
  ~IpcEventServer();

  IpcEventServer(IpcEventServer const&) = delete;
  IpcEventServer& operator=(IpcEventServer const&) = delete;

  void start();
  void stop();
  bool running() const;

  void broadcast_metadata();
  void broadcast(PacketEvent const& event);

 private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace packet_probe
