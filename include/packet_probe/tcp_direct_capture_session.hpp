#pragma once

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "packet_probe/capture_session.hpp"
#include "packet_probe/packet_event.hpp"

namespace packet_probe {

struct TcpDirectCaptureOptions {
  std::string host;
  std::uint16_t port = 0;
  std::string session_id = "tcp-client-1";
};

class TcpDirectCaptureSession : public CaptureSession {
 public:
  using EventCallback = std::function<void(PacketEvent const&)>;

  TcpDirectCaptureSession(TcpDirectCaptureOptions options, EventCallback on_event);
  ~TcpDirectCaptureSession() override;

  TcpDirectCaptureSession(TcpDirectCaptureSession const&) = delete;
  TcpDirectCaptureSession& operator=(TcpDirectCaptureSession const&) = delete;

  void start() override;
  void stop() override;
  bool stopped() const;
  bool send(std::vector<std::uint8_t> payload);

 private:
  struct Impl;

  PacketEvent make_event(Direction direction, EventType type, std::vector<std::uint8_t> payload,
                         std::string summary);
  void emit(PacketEvent event);

  TcpDirectCaptureOptions options_;
  EventCallback on_event_;
  std::atomic<std::uint64_t> next_sequence_{1};
  std::atomic<bool> stopped_{true};
  std::unique_ptr<Impl> impl_;
};

}  // namespace packet_probe
