#include "run_modes.hpp"

#include <chrono>
#include <stdexcept>
#include <thread>

#include "engine_controller.hpp"

namespace packet_probe::cli {

int run_engine(CliOptions const& options, StopRequested const& stop_requested) {
  if (options.ipc_path.empty()) {
    throw std::invalid_argument("engine mode requires --ipc <path>");
  }

  auto seq_alloc = make_sequence_allocator();
  auto ipc_server = make_ipc_server(options);

  EngineController controller(ipc_server.get(), seq_alloc);
  controller.install();

  while (!stop_requested()) {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }

  controller.shutdown();
  return 0;
}

}  // namespace packet_probe::cli
