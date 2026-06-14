#pragma once

#include <fstream>
#include <mutex>
#include <string>

#include "packet_probe/jsonl_serializer.hpp"
#include "packet_probe/packet_event.hpp"

namespace packet_probe {

class JsonlRecorder {
 public:
  JsonlRecorder() = default;
  explicit JsonlRecorder(std::string path);
  ~JsonlRecorder();

  JsonlRecorder(JsonlRecorder const&) = delete;
  JsonlRecorder& operator=(JsonlRecorder const&) = delete;

  void open(std::string path);
  void close();
  bool is_open() const;
  void record(PacketEvent const& event);

 private:
  mutable std::mutex mutex_;
  std::ofstream output_;
};

}  // namespace packet_probe
