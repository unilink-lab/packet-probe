#include "ipc/ipc_event_server.hpp"

#include "packet_probe/core/jsonl_serializer.hpp"

#include <atomic>
#include <cerrno>
#include <cstring>
#include <filesystem>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <utility>
#include <vector>

#if !defined(_WIN32)
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#endif

namespace packet_probe {

namespace {

#if !defined(_WIN32)
void close_fd(int& fd) {
  if (fd >= 0) {
    ::close(fd);
    fd = -1;
  }
}

std::string errno_message(std::string const& prefix) { return prefix + ": " + std::strerror(errno); }

bool send_all(int fd, std::string const& line) {
  std::size_t sent = 0;
  while (sent < line.size()) {
#if defined(MSG_NOSIGNAL)
    constexpr int flags = MSG_NOSIGNAL;
#else
    constexpr int flags = 0;
#endif
    auto const n = ::send(fd, line.data() + sent, line.size() - sent, flags);
    if (n <= 0) {
      return false;
    }
    sent += static_cast<std::size_t>(n);
  }
  return true;
}
#endif

}  // namespace

struct IpcEventServer::Impl {
  explicit Impl(IpcServerOptions server_options) : options(std::move(server_options)) {}

  IpcServerOptions options;

#if !defined(_WIN32)
  int server_fd = -1;
  std::atomic<bool> is_running{false};
  std::thread accept_thread;
  mutable std::mutex clients_mutex;
  std::vector<int> clients;

  void start() {
    if (options.socket_path.empty()) {
      throw std::invalid_argument("--ipc requires a socket path");
    }
    if (is_running.load()) {
      return;
    }

    auto const path = std::filesystem::path(options.socket_path);
    auto const parent = path.parent_path();
    if (!parent.empty() && !std::filesystem::exists(parent)) {
      throw std::runtime_error("IPC socket parent directory does not exist: " + parent.string());
    }

    std::error_code status_error;
    auto const status = std::filesystem::symlink_status(path, status_error);
    if (!status_error && std::filesystem::exists(status)) {
      if (std::filesystem::is_directory(status)) {
        throw std::runtime_error("IPC socket path is a directory: " + options.socket_path);
      }
      if (status.type() != std::filesystem::file_type::socket) {
        throw std::runtime_error("IPC socket path exists and is not a socket: " + options.socket_path);
      }
      std::error_code remove_error;
      std::filesystem::remove(path, remove_error);
      if (remove_error) {
        throw std::runtime_error("failed to remove stale IPC socket: " + remove_error.message());
      }
    }

    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    if (options.socket_path.size() >= sizeof(address.sun_path)) {
      throw std::runtime_error("IPC socket path is too long: " + options.socket_path);
    }
    std::strncpy(address.sun_path, options.socket_path.c_str(), sizeof(address.sun_path) - 1);

    server_fd = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (server_fd < 0) {
      throw std::runtime_error(errno_message("failed to create IPC socket"));
    }

    if (::bind(server_fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0) {
      auto const message = errno_message("failed to bind IPC socket");
      close_fd(server_fd);
      std::filesystem::remove(path);
      throw std::runtime_error(message);
    }

    if (::listen(server_fd, 16) != 0) {
      auto const message = errno_message("failed to listen on IPC socket");
      close_fd(server_fd);
      std::filesystem::remove(path);
      throw std::runtime_error(message);
    }

    is_running.store(true);
    accept_thread = std::thread([this] { accept_loop(); });
  }

  void stop() {
    if (!is_running.exchange(false) && server_fd < 0) {
      return;
    }

    wake_accept();
    close_fd(server_fd);
    if (accept_thread.joinable()) {
      accept_thread.join();
    }

    {
      std::lock_guard<std::mutex> lock(clients_mutex);
      for (auto& client : clients) {
        close_fd(client);
      }
      clients.clear();
    }

    std::error_code ignored;
    std::filesystem::remove(options.socket_path, ignored);
  }

  bool running() const { return is_running.load(); }

  void broadcast_metadata() { broadcast_line(serialize_metadata_jsonl() + '\n'); }

  void broadcast(PacketEvent const& event) { broadcast_line(serialize_event_jsonl(event) + '\n'); }

  void accept_loop() {
    while (is_running.load()) {
      int client_fd = ::accept(server_fd, nullptr, nullptr);
      if (client_fd < 0) {
        if (errno == EINTR) {
          continue;
        }
        if (!is_running.load()) {
          break;
        }
        continue;
      }

      auto metadata = serialize_metadata_jsonl() + '\n';
      if (!send_all(client_fd, metadata)) {
        ::close(client_fd);
        continue;
      }

      std::lock_guard<std::mutex> lock(clients_mutex);
      clients.push_back(client_fd);
    }
  }

  void wake_accept() const {
    if (server_fd < 0 || options.socket_path.empty()) {
      return;
    }

    int wake_fd = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (wake_fd < 0) {
      return;
    }

    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    if (options.socket_path.size() < sizeof(address.sun_path)) {
      std::strncpy(address.sun_path, options.socket_path.c_str(), sizeof(address.sun_path) - 1);
      (void)::connect(wake_fd, reinterpret_cast<sockaddr*>(&address), sizeof(address));
    }
    ::close(wake_fd);
  }

  void broadcast_line(std::string const& line) {
    std::lock_guard<std::mutex> lock(clients_mutex);
    auto out = clients.begin();
    for (auto it = clients.begin(); it != clients.end(); ++it) {
      if (send_all(*it, line)) {
        *out++ = *it;
      } else {
        int fd = *it;
        close_fd(fd);
      }
    }
    clients.erase(out, clients.end());
  }
#else
  std::atomic<bool> is_running{false};

  void start() { throw std::runtime_error("UDS IPC is not supported on this platform yet"); }
  void stop() { is_running.store(false); }
  bool running() const { return false; }
  void broadcast_metadata() {}
  void broadcast(PacketEvent const&) {}
#endif
};

IpcEventServer::IpcEventServer(IpcServerOptions options) : impl_(std::make_unique<Impl>(std::move(options))) {}

IpcEventServer::~IpcEventServer() { stop(); }

void IpcEventServer::start() { impl_->start(); }

void IpcEventServer::stop() { impl_->stop(); }

bool IpcEventServer::running() const { return impl_->running(); }

void IpcEventServer::broadcast_metadata() {
  try {
    impl_->broadcast_metadata();
  } catch (...) {
  }
}

void IpcEventServer::broadcast(PacketEvent const& event) {
  try {
    impl_->broadcast(event);
  } catch (...) {
  }
}

}  // namespace packet_probe
