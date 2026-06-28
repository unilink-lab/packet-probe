#pragma once

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>

#include "capture/capture_session.hpp"
#include "packet_probe/core/packet_event.hpp"
#include "packet_probe/core/sequence_allocator.hpp"

namespace packet_probe {

struct TcpProxyConfig {
  std::string listen_host;
  std::uint16_t listen_port = 0;

  std::string target_host;
  std::uint16_t target_port = 0;

  std::string session_id = "tcp-proxy-1";
  bool latency_enabled = true;
};

class TcpProxyCaptureSession : public CaptureSession {
 public:
  using EventCallback = std::function<void(PacketEvent const&)>;

  TcpProxyCaptureSession(TcpProxyConfig config, EventCallback on_event, SharedSequenceAllocator seq_alloc);
  ~TcpProxyCaptureSession() override;

  TcpProxyCaptureSession(TcpProxyCaptureSession const&) = delete;
  TcpProxyCaptureSession& operator=(TcpProxyCaptureSession const&) = delete;

  void start() override;
  void stop() override;
  bool stopped() const;

 private:
  struct Impl;

  PacketEvent make_event(Direction direction, EventType type, std::vector<std::uint8_t> payload,
                         std::string source_endpoint, std::string destination_endpoint, std::string summary);
  PacketEvent make_latency_event(PacketEvent const& response, std::uint64_t request_sequence,
                                 std::int64_t latency_ns, std::size_t request_size, std::size_t response_size);
  void observe_latency(PacketEvent const& raw_event);
  void emit(PacketEvent const& event);

  TcpProxyConfig config_;
  EventCallback on_event_;
  SharedSequenceAllocator seq_alloc_;
  std::atomic<bool> stopped_{true};
  std::unique_ptr<Impl> impl_;
};

}  // namespace packet_probe
