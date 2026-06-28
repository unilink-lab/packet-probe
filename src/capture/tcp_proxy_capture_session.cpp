#include "capture/tcp_proxy_capture_session.hpp"

#include <array>
#include <boost/asio.hpp>
#include <exception>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <utility>

#include "core/endpoint.hpp"
#include "core/latency_tracker.hpp"

namespace packet_probe {

namespace {

using boost::asio::ip::tcp;

std::string endpoint_to_string(tcp::endpoint const& endpoint) {
  return endpoint.address().to_string() + ":" + std::to_string(endpoint.port());
}

std::string direction_summary(Direction direction, std::size_t size) {
  auto prefix = direction == Direction::AppToDevice ? "APP -> DEVICE " : "DEVICE -> APP ";
  return std::string(prefix) + std::to_string(size) + " bytes";
}

}  // namespace

struct TcpProxyCaptureSession::Impl {
  boost::asio::io_context io_context;
  std::unique_ptr<tcp::acceptor> acceptor;
  std::unique_ptr<tcp::socket> app_socket;
  std::unique_ptr<tcp::socket> device_socket;
  std::thread accept_thread;
  std::thread app_to_device_thread;
  std::thread device_to_app_thread;
  std::mutex socket_mutex;
  std::mutex latency_mutex;
  LatencyTracker latency_tracker;
};

TcpProxyCaptureSession::TcpProxyCaptureSession(TcpProxyConfig config, EventCallback on_event, SharedSequenceAllocator seq_alloc)
    : config_(std::move(config)), on_event_(std::move(on_event)), seq_alloc_(std::move(seq_alloc)), impl_(std::make_unique<Impl>()) {}

TcpProxyCaptureSession::~TcpProxyCaptureSession() { stop(); }

void TcpProxyCaptureSession::start() {
  if (config_.listen_host.empty()) {
    throw std::invalid_argument("tcp-proxy requires --listen-host");
  }
  if (config_.listen_port == 0) {
    throw std::invalid_argument("tcp-proxy requires --listen-port");
  }
  if (config_.target_host.empty()) {
    throw std::invalid_argument("tcp-proxy requires --target-host");
  }
  if (config_.target_port == 0) {
    throw std::invalid_argument("tcp-proxy requires --target-port");
  }

  boost::system::error_code ec;
  auto listen_address = boost::asio::ip::make_address(config_.listen_host, ec);
  if (ec) {
    throw std::runtime_error("invalid --listen-host: " + config_.listen_host);
  }

  auto endpoint = tcp::endpoint(listen_address, config_.listen_port);
  impl_->acceptor = std::make_unique<tcp::acceptor>(impl_->io_context);
  impl_->acceptor->open(endpoint.protocol(), ec);
  if (ec) {
    throw std::runtime_error("failed to open tcp-proxy listener: " + ec.message());
  }
  impl_->acceptor->set_option(boost::asio::socket_base::reuse_address(true), ec);
  impl_->acceptor->bind(endpoint, ec);
  if (ec) {
    throw std::runtime_error("failed to bind tcp-proxy listener: " + ec.message());
  }
  impl_->acceptor->listen(boost::asio::socket_base::max_listen_connections, ec);
  if (ec) {
    throw std::runtime_error("failed to listen for tcp-proxy: " + ec.message());
  }

  stopped_.store(false);
  emit(make_event(Direction::AppToDevice, EventType::StateChange, {}, format_endpoint(config_.listen_host, config_.listen_port),
                  format_endpoint(config_.target_host, config_.target_port),
                  "listening " + format_endpoint(config_.listen_host, config_.listen_port)));

  impl_->accept_thread = std::thread([this] {
    try {
      auto app_socket = std::make_unique<tcp::socket>(impl_->io_context);
      boost::system::error_code ec;
      impl_->acceptor->accept(*app_socket, ec);
      if (ec) {
        if (!stopped_.load()) {
          emit(make_event(Direction::AppToDevice, EventType::Error, {}, {}, {}, "accept failed: " + ec.message()));
        }
        stopped_.store(true);
        return;
      }

      tcp::resolver resolver(impl_->io_context);
      auto target_endpoints = resolver.resolve(config_.target_host, std::to_string(config_.target_port), ec);
      if (ec) {
        emit(make_event(Direction::AppToDevice, EventType::Error, {}, endpoint_to_string(app_socket->remote_endpoint()),
                        format_endpoint(config_.target_host, config_.target_port),
                        "target resolve failed: " + ec.message()));
        stopped_.store(true);
        return;
      }

      auto device_socket = std::make_unique<tcp::socket>(impl_->io_context);
      boost::asio::connect(*device_socket, target_endpoints, ec);
      if (ec) {
        emit(make_event(Direction::AppToDevice, EventType::Error, {}, endpoint_to_string(app_socket->remote_endpoint()),
                        format_endpoint(config_.target_host, config_.target_port),
                        "target connect failed: " + ec.message()));
        stopped_.store(true);
        return;
      }

      auto app_endpoint = endpoint_to_string(app_socket->remote_endpoint());
      auto proxy_to_device_endpoint = endpoint_to_string(device_socket->remote_endpoint());
      {
        std::lock_guard<std::mutex> lock(impl_->socket_mutex);
        impl_->app_socket = std::move(app_socket);
        impl_->device_socket = std::move(device_socket);
      }

      emit(make_event(Direction::AppToDevice, EventType::StateChange, {}, app_endpoint, proxy_to_device_endpoint,
                      "proxy connected"));

      auto forward = [this](Direction direction, tcp::socket& input, tcp::socket& output, std::string source,
                            std::string destination) {
        std::array<std::uint8_t, 4096> buffer{};
        while (!stopped_.load()) {
          boost::system::error_code read_ec;
          auto const bytes = input.read_some(boost::asio::buffer(buffer), read_ec);
          if (read_ec) {
            break;
          }

          std::vector<std::uint8_t> payload(buffer.begin(), buffer.begin() + static_cast<std::ptrdiff_t>(bytes));
          auto raw_event =
              make_event(direction, EventType::RawBytes, payload, source, destination, direction_summary(direction, bytes));
          emit(raw_event);
          observe_latency(raw_event);

          boost::system::error_code write_ec;
          boost::asio::write(output, boost::asio::buffer(payload), write_ec);
          if (write_ec) {
            break;
          }
        }
        auto was_stopped = stopped_.exchange(true);
        {
          std::lock_guard<std::mutex> lock(impl_->socket_mutex);
          boost::system::error_code ec;
          if (impl_->app_socket) {
            impl_->app_socket->shutdown(tcp::socket::shutdown_both, ec);
            impl_->app_socket->close(ec);
          }
          if (impl_->device_socket) {
            impl_->device_socket->shutdown(tcp::socket::shutdown_both, ec);
            impl_->device_socket->close(ec);
          }
        }
        if (!was_stopped) {
          emit(make_event(Direction::DeviceToApp, EventType::StateChange, {}, source, destination, "proxy stopped"));
        }
      };

      impl_->app_to_device_thread = std::thread(forward, Direction::AppToDevice, std::ref(*impl_->app_socket),
                                                std::ref(*impl_->device_socket), app_endpoint,
                                                proxy_to_device_endpoint);
      impl_->device_to_app_thread = std::thread(forward, Direction::DeviceToApp, std::ref(*impl_->device_socket),
                                                std::ref(*impl_->app_socket), proxy_to_device_endpoint,
                                                app_endpoint);
    } catch (std::exception const& ex) {
      if (!stopped_.load()) {
        emit(make_event(Direction::AppToDevice, EventType::Error, {}, {}, {}, ex.what()));
      }
      stopped_.store(true);
    }
  });
}

void TcpProxyCaptureSession::stop() {
  auto was_stopped = stopped_.exchange(true);

  {
    std::lock_guard<std::mutex> lock(impl_->socket_mutex);
    boost::system::error_code ec;
    if (impl_->acceptor) {
      impl_->acceptor->close(ec);
    }
    if (impl_->app_socket) {
      impl_->app_socket->shutdown(tcp::socket::shutdown_both, ec);
      impl_->app_socket->close(ec);
    }
    if (impl_->device_socket) {
      impl_->device_socket->shutdown(tcp::socket::shutdown_both, ec);
      impl_->device_socket->close(ec);
    }
  }

  auto this_id = std::this_thread::get_id();
  if (impl_->app_to_device_thread.joinable() && impl_->app_to_device_thread.get_id() != this_id) {
    impl_->app_to_device_thread.join();
  }
  if (impl_->device_to_app_thread.joinable() && impl_->device_to_app_thread.get_id() != this_id) {
    impl_->device_to_app_thread.join();
  }
  if (impl_->accept_thread.joinable() && impl_->accept_thread.get_id() != this_id) {
    impl_->accept_thread.join();
  }

  if (!was_stopped) {
    emit(make_event(Direction::DeviceToApp, EventType::StateChange, {}, {}, {}, "proxy stopped"));
  }
}

bool TcpProxyCaptureSession::stopped() const { return stopped_.load(); }

PacketEvent TcpProxyCaptureSession::make_event(Direction direction, EventType type, std::vector<std::uint8_t> payload,
                                               std::string source_endpoint, std::string destination_endpoint,
                                               std::string summary) {
  PacketEvent event;
  event.sequence = seq_alloc_->next();
  event.timestamp_ns = now_ns();
  event.session_id = config_.session_id;
  event.transport = "tcp";
  event.direction = direction;
  event.type = type;
  event.source_endpoint = std::move(source_endpoint);
  event.destination_endpoint = std::move(destination_endpoint);
  event.payload = std::move(payload);
  event.summary = std::move(summary);
  return event;
}

PacketEvent TcpProxyCaptureSession::make_latency_event(PacketEvent const& response, std::uint64_t request_sequence,
                                                       std::int64_t latency_ns, std::size_t request_size,
                                                       std::size_t response_size) {
  PacketEvent event;
  event.sequence = seq_alloc_->next();
  event.timestamp_ns = response.timestamp_ns;
  event.session_id = config_.session_id;
  event.transport = "tcp";
  event.direction = Direction::DeviceToApp;
  event.type = EventType::Latency;
  event.source_endpoint = response.source_endpoint;
  event.destination_endpoint = response.destination_endpoint;
  event.request_sequence = request_sequence;
  event.response_sequence = response.sequence;
  event.latency_ns = latency_ns;
  event.request_size = request_size;
  event.response_size = response_size;
  event.summary = "response latency " + std::to_string(latency_ns / 1000) + " us";
  return event;
}

void TcpProxyCaptureSession::observe_latency(PacketEvent const& raw_event) {
  if (!config_.latency_enabled) {
    return;
  }

  std::lock_guard<std::mutex> lock(impl_->latency_mutex);
  auto measurement = impl_->latency_tracker.observe(raw_event);
  if (measurement) {
    emit(make_latency_event(raw_event, measurement->request_sequence, measurement->latency_ns, measurement->request_size,
                            measurement->response_size));
  }
}

void TcpProxyCaptureSession::emit(PacketEvent const& event) {
  if (!on_event_) {
    return;
  }
  try {
    on_event_(event);
  } catch (...) {
  }
}

}  // namespace packet_probe
