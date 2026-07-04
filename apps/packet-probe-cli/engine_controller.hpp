#pragma once

#include <atomic>
#include <memory>
#include <mutex>
#include <string>
#include <string_view>

#include <nlohmann/json.hpp>

#include "cli_options.hpp"
#include "core/event_pipeline.hpp"
#include "ipc/ipc_event_server.hpp"
#include "packet_probe/core/sequence_allocator.hpp"
#include "recorder/jsonl_recorder.hpp"

namespace packet_probe::cli {

// Adapts one concrete capture session type (UdpDirectCaptureSession,
// TcpDirectCaptureSession, ...) to a single non-template interface so
// EngineController can hold "whichever session the current config selected"
// without exposing session-specific types outside this translation unit.
class IEngineSession {
 public:
  virtual ~IEngineSession() = default;
  virtual void stop() = 0;
  virtual bool stopped() const = 0;
  // Returns false if the session type does not support send() (e.g. tcp-proxy)
  // or if the underlying send failed.
  virtual bool send(std::vector<std::uint8_t> payload) = 0;
  virtual bool supports_send() const = 0;
};

// Owns the IPC control-protocol-v2 dispatcher and the currently active capture
// session (if any). Turns the CLI core into a long-lived "engine" process: a
// single IpcEventServer and SequenceAllocator persist across repeated
// configure/start_capture/stop_capture cycles, so changing capture settings
// from a viewer no longer requires restarting the packet-probe process.
//
// State machine: Idle <-> Capturing. "configure" is only accepted while Idle;
// "start_capture" builds and starts a session from the last configured
// options; "stop_capture" tears the session down and returns to Idle without
// losing the IPC connection or the configured options (so restarting after a
// config change does not require a fresh viewer-side reconnect).
class EngineController {
 public:
  EngineController(IpcEventServer* ipc_server, SharedSequenceAllocator seq_alloc);
  ~EngineController();

  EngineController(EngineController const&) = delete;
  EngineController& operator=(EngineController const&) = delete;

  // Registers this controller as ipc_server's command handler. Call once
  // before the IPC server starts accepting messages.
  void install();

  // Stops any active capture session. Safe to call even if idle.
  void shutdown();

 private:
  void handle_command(IpcClientId client_id, std::string_view line);

  void handle_configure(IpcClientId client_id, std::string const& id, nlohmann::json const& msg);
  void handle_start_capture(IpcClientId client_id, std::string const& id);
  void handle_stop_capture(IpcClientId client_id, std::string const& id);
  void handle_get_status(IpcClientId client_id, std::string const& id);
  void handle_list_serial_ports(IpcClientId client_id, std::string const& id);
  void handle_send(IpcClientId client_id, std::string const& id, nlohmann::json const& msg);

  void reply_result(IpcClientId client_id, std::string const& id, bool ok, std::string const& error = "");
  void broadcast_status_locked();
  // Builds session_/pipeline_/recorder_ from config_ and starts the session.
  // Throws on invalid/unsupported config; leaves members untouched on success,
  // caller is responsible for rolling back partial state on failure.
  void start_session_locked();
  void stop_capture_locked();

  IpcEventServer* ipc_server_;
  SharedSequenceAllocator seq_alloc_;

  std::mutex mutex_;
  bool capturing_ = false;
  bool has_config_ = false;
  CliOptions config_;
  std::atomic<std::uint64_t> events_seen_{0};

  // Declaration order matters: session_ (which calls back into pipeline_) is
  // destroyed first, then pipeline_ (which holds a reference to *recorder_),
  // then recorder_.
  std::unique_ptr<JsonlRecorder> recorder_;
  std::unique_ptr<EventPipeline> pipeline_;
  std::unique_ptr<IEngineSession> session_;
};

}  // namespace packet_probe::cli
