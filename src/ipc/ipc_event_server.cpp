#include "ipc/ipc_event_server.hpp"

#include "packet_probe/core/jsonl_serializer.hpp"
#include "unilink/unilink.hpp"
#include "unilink/framer/line_framer.hpp"

#include <atomic>
#include <filesystem>
#include <mutex>
#include <stdexcept>
#include <utility>

namespace packet_probe {

struct IpcEventServer::Impl {
  explicit Impl(IpcServerOptions server_options) : options(std::move(server_options)) {}

  IpcServerOptions options;
  std::unique_ptr<unilink::UdsServer> server;
  std::atomic<bool> is_running{false};
  CommandHandler command_handler;
  std::mutex command_handler_mutex;

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
    if (std::filesystem::is_directory(path)) {
      throw std::runtime_error("IPC socket path is a directory: " + options.socket_path);
    }

    // Windows supports UDS via AF_UNIX as well.
    // Stale socket cleanup: UDS in Unix requires removing the socket file before binding.
    // unilink::UdsServer might not handle this or might throw, so let's clean it up if it exists.
    std::error_code remove_err;
    if (std::filesystem::exists(path) && !std::filesystem::is_directory(path)) {
      std::filesystem::remove(path, remove_err);
    }

    server = std::make_unique<unilink::UdsServer>(options.socket_path);
    server->max_clients(16);
    server->auto_start(false);

    // Enable line framing so on_message delivers complete newline-terminated commands
    server->framer([]() {
      return std::make_unique<unilink::framer::LineFramer>("\n", false, 65536);
    });

    server->on_connect([this](unilink::ConnectionContext const& ctx) {
      if (server) {
        auto metadata = serialize_metadata_jsonl() + '\n';
        server->send_to(ctx.client_id(), metadata);
      }
    });

    server->on_error([this](unilink::ErrorContext const& ctx) {
      // Do not stop the whole IPC server for a single client error.
    });

    server->on_message([this](unilink::MessageContext const& ctx) {
      CommandHandler handler_copy;
      {
        std::lock_guard<std::mutex> lock(command_handler_mutex);
        handler_copy = command_handler;
      }
      if (handler_copy) {
        handler_copy(ctx.data());
      }
    });

    auto started = server->start_sync();
    if (!started) {
      server.reset();
      is_running.store(false);
      throw std::runtime_error("failed to start IPC UDS server");
    }

    is_running.store(true);
  }

  void stop() {
    is_running.store(false);

    if (server) {
      server->stop();
      server.reset();
    }

    std::error_code ignored;
    std::filesystem::remove(options.socket_path, ignored);
  }

  bool running() const { return is_running.load(); }

  void broadcast_metadata() {
    if (!server || !is_running.load()) {
      return;
    }
    server->broadcast(serialize_metadata_jsonl() + '\n');
  }

  void broadcast(PacketEvent const& event) {
    if (!server || !is_running.load()) {
      return;
    }
    server->broadcast(serialize_event_jsonl(event) + '\n');
  }
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

void IpcEventServer::set_command_handler(CommandHandler handler) {
  std::lock_guard<std::mutex> lock(impl_->command_handler_mutex);
  impl_->command_handler = std::move(handler);
}

}  // namespace packet_probe
