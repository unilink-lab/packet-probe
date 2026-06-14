#pragma once

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "capture/capture_session.hpp"
#include "packet_probe/core/packet_event.hpp"
#include "capture/serial_options.hpp"

namespace packet_probe {

class SerialDirectCaptureSession : public CaptureSession {
 public:
  using EventCallback = std::function<void(PacketEvent const&)>;

  SerialDirectCaptureSession(SerialCaptureOptions options, EventCallback on_event);
  ~SerialDirectCaptureSession() override;

  SerialDirectCaptureSession(SerialDirectCaptureSession const&) = delete;
  SerialDirectCaptureSession& operator=(SerialDirectCaptureSession const&) = delete;

  void start() override;
  void stop() override;
  bool stopped() const;

  bool send(std::vector<std::uint8_t> payload);

 private:
  struct Impl;

  PacketEvent make_event(Direction direction, EventType type, std::vector<std::uint8_t> payload,
                         std::string source_endpoint, std::string destination_endpoint, std::string summary);
  void emit(PacketEvent const& event);

  SerialCaptureOptions options_;
  EventCallback on_event_;
  std::atomic<std::uint64_t> next_sequence_{1};
  std::atomic<bool> stopped_{true};
  std::unique_ptr<Impl> impl_;
};

}  // namespace packet_probe
