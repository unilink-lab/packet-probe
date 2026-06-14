#include "packet_probe/tcp_direct_capture_session.hpp"

#include <chrono>
#include <stdexcept>
#include <utility>

#include "unilink/unilink.hpp"

namespace packet_probe {

struct TcpDirectCaptureSession::Impl {
  std::unique_ptr<unilink::TcpClient> client;
};

TcpDirectCaptureSession::TcpDirectCaptureSession(TcpDirectCaptureOptions options, EventCallback on_event)
    : options_(std::move(options)), on_event_(std::move(on_event)), impl_(std::make_unique<Impl>()) {}

TcpDirectCaptureSession::~TcpDirectCaptureSession() { stop(); }

void TcpDirectCaptureSession::start() {
  if (options_.host.empty()) {
    throw std::invalid_argument("tcp-client requires --host");
  }
  if (options_.port == 0) {
    throw std::invalid_argument("tcp-client requires --port");
  }

  impl_->client = std::make_unique<unilink::TcpClient>(options_.host, options_.port);
  impl_->client->max_retries(0).connection_timeout(std::chrono::milliseconds(2000));
  stopped_.store(false);
  impl_->client->on_data([this](unilink::MessageContext const& ctx) {
    auto payload = ctx.data_as_vector();
    emit(make_event(Direction::DeviceToApp, EventType::RawBytes, std::move(payload),
                    "RX " + std::to_string(ctx.data().size()) + " bytes"));
  });
  impl_->client->on_connect([this](unilink::ConnectionContext const& ctx) {
    auto summary = std::string("connected");
    if (!ctx.client_info().empty()) {
      summary += " " + ctx.client_info();
    }
    emit(make_event(Direction::DeviceToApp, EventType::StateChange, {}, std::move(summary)));
  });
  impl_->client->on_disconnect([this](unilink::ConnectionContext const& ctx) {
    auto summary = std::string("disconnected");
    if (!ctx.client_info().empty()) {
      summary += " " + ctx.client_info();
    }
    emit(make_event(Direction::DeviceToApp, EventType::StateChange, {}, std::move(summary)));
    stopped_.store(true);
  });
  impl_->client->on_error([this](unilink::ErrorContext const& ctx) {
    emit(make_event(Direction::DeviceToApp, EventType::Error, {}, std::string(ctx.message())));
    stopped_.store(true);
  });

  auto started = impl_->client->start();
  if (!started.get()) {
    stopped_.store(true);
    throw std::runtime_error("failed to start TCP client");
  }
}

void TcpDirectCaptureSession::stop() {
  if (stopped_.exchange(true)) {
    return;
  }
  if (impl_ && impl_->client) {
    impl_->client->stop();
    impl_->client.reset();
  }
}

bool TcpDirectCaptureSession::stopped() const { return stopped_.load(); }

bool TcpDirectCaptureSession::send(std::vector<std::uint8_t> payload) {
  if (!impl_->client || !impl_->client->connected()) {
    return false;
  }

  auto const size = payload.size();
  auto sent_payload = payload;
  auto accepted = impl_->client->send_move(std::move(payload));
  if (accepted) {
    emit(make_event(Direction::AppToDevice, EventType::RawBytes, std::move(sent_payload),
                    "TX " + std::to_string(size) + " bytes"));
  }
  return accepted;
}

PacketEvent TcpDirectCaptureSession::make_event(Direction direction, EventType type, std::vector<std::uint8_t> payload,
                                                std::string summary) {
  PacketEvent event;
  event.sequence = next_sequence_.fetch_add(1);
  event.timestamp_ns = now_ns();
  event.session_id = options_.session_id;
  event.transport = "tcp";
  event.direction = direction;
  event.type = type;
  event.payload = std::move(payload);
  event.summary = std::move(summary);
  return event;
}

void TcpDirectCaptureSession::emit(PacketEvent event) {
  if (on_event_) {
    on_event_(event);
  }
}

}  // namespace packet_probe
