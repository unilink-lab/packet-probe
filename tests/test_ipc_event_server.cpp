#include "ipc/ipc_event_server.hpp"
#include "unilink/unilink.hpp"

#include <iostream>
#include <chrono>
#include <filesystem>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
#include <cstdlib>

#define TEST_ASSERT(cond, msg) \
  if (!(cond)) { \
    std::cerr << "Assertion failed: " << #cond << " - " << msg << std::endl; \
    std::exit(1); \
  }

namespace {

std::filesystem::path make_temp_socket_path() {
  auto base = std::filesystem::temp_directory_path();
  auto name = "pp-ipc-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) + ".sock";
  return base / name;
}

void wait_until(std::function<bool()> const& predicate, std::string const& description, std::chrono::milliseconds timeout = std::chrono::seconds(5)) {
  auto deadline = std::chrono::steady_clock::now() + timeout;
  while (std::chrono::steady_clock::now() < deadline) {
    if (predicate()) {
      return;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  TEST_ASSERT(predicate(), "Timeout waiting for: " + description);
}

}  // namespace

int main() {
  auto socket_path = make_temp_socket_path();
  std::cout << "Using temporary socket path: " << socket_path << std::endl;

  packet_probe::IpcServerOptions options;
  options.socket_path = socket_path.string();

  packet_probe::IpcEventServer server(options);
  std::cout << "Starting IPC server..." << std::endl;
  server.start();
  TEST_ASSERT(server.running(), "Server should be running after start()");

  std::mutex mutex;
  std::vector<std::string> messages;

  unilink::UdsClient client(options.socket_path);
  client.framer(std::make_unique<unilink::framer::LineFramer>("\n", false, 65536));
  client.on_message([&](unilink::MessageContext const& ctx) {
    std::lock_guard<std::mutex> lock(mutex);
    std::cout << "Client received message: " << ctx.data() << std::endl;
    messages.emplace_back(ctx.data());
  });

  std::cout << "Starting UDS client..." << std::endl;
  bool client_started = client.start_sync();
  TEST_ASSERT(client_started, "Client start_sync() should return true");

  std::cout << "Waiting for metadata message..." << std::endl;
  // Wait for connection and metadata message
  wait_until([&] {
    std::lock_guard<std::mutex> lock(mutex);
    return !messages.empty();
  }, "metadata message");

  {
    std::lock_guard<std::mutex> lock(mutex);
    TEST_ASSERT(messages[0].find("\"type\":\"metadata\"") != std::string::npos, "First message must be metadata");
  }

  std::cout << "Broadcasting test event..." << std::endl;
  // Broadcast an event
  packet_probe::PacketEvent event;
  event.sequence = 1;
  event.session_id = "test";
  event.transport = "uds";
  event.summary = "test event";
  server.broadcast(event);

  std::cout << "Waiting for event message..." << std::endl;
  // Wait for the event message
  wait_until([&] {
    std::lock_guard<std::mutex> lock(mutex);
    return messages.size() >= 2;
  }, "event message");

  {
    std::lock_guard<std::mutex> lock(mutex);
    TEST_ASSERT(messages[1].find("\"seq\":1") != std::string::npos, "Event sequence should match");
    TEST_ASSERT(messages[1].find("\"summary\":\"test event\"") != std::string::npos, "Event summary should match");
  }

  std::cout << "Stopping client and server..." << std::endl;
  client.stop();
  server.stop();
  TEST_ASSERT(!server.running(), "Server should not be running after stop()");

  // Clean up socket file
  std::error_code ignored;
  std::filesystem::remove(socket_path, ignored);

  std::cout << "Test completed successfully!" << std::endl;
  return 0;
}
