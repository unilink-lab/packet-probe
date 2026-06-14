#include "packet_probe/jsonl_recorder.hpp"

#include <stdexcept>

namespace packet_probe {

JsonlRecorder::JsonlRecorder(std::string path) { open(std::move(path)); }

JsonlRecorder::~JsonlRecorder() { close(); }

void JsonlRecorder::open(std::string path) {
  std::lock_guard<std::mutex> lock(mutex_);
  output_.open(path, std::ios::out | std::ios::app);
  if (!output_) {
    throw std::runtime_error("failed to open JSONL log: " + path);
  }
  output_ << serialize_metadata_jsonl() << '\n';
  output_.flush();
}

void JsonlRecorder::close() {
  std::lock_guard<std::mutex> lock(mutex_);
  if (output_.is_open()) {
    output_.close();
  }
}

bool JsonlRecorder::is_open() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return output_.is_open();
}

void JsonlRecorder::record(PacketEvent const& event) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!output_.is_open()) {
    return;
  }
  output_ << serialize_event_jsonl(event) << '\n';
  output_.flush();
}

}  // namespace packet_probe
