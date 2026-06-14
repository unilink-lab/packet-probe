#pragma once

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "packet_probe/capture_session.hpp"
#include "packet_probe/packet_event.hpp"

namespace packet_probe {

struct UdpDirectCaptureOptions {
  std::string bind_host = "0.0.0.0";
  std::uint16_t bind_port = 0;
  std::string target_host;
  std::uint16_t target_port = 0;
  std::string session_id = "udp-1";
};

class UdpDirectCaptureSession : public CaptureSession {
 public:
  using EventCallback = std::function<void(PacketEvent const&)>;

  UdpDirectCaptureSession(UdpDirectCaptureOptions options, EventCallback on_event);
  ~UdpDirectCaptureSession() override;

  UdpDirectCaptureSession(UdpDirectCaptureSession const&) = delete;
  UdpDirectCaptureSession& operator=(UdpDirectCaptureSession const&) = delete;

  void start() override;
  void stop() override;
  bool stopped() const;

  bool send(std::vector<std::uint8_t> payload);

 private:
  PacketEvent make_event(Direction direction, EventType type, std::vector<std::uint8_t> payload,
                         std::string source_endpoint, std::string destination_endpoint, std::string summary);
  void emit(PacketEvent const& event);

  struct Impl;
  UdpDirectCaptureOptions options_;
  EventCallback on_event_;
  std::atomic<std::uint64_t> next_sequence_{1};
  std::atomic<bool> stopped_{true};
  std::unique_ptr<Impl> impl_;
};

}  // namespace packet_probe
