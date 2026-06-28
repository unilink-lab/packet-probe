#pragma once

#include <atomic>
#include <cstdint>
#include <memory>

namespace packet_probe {

class SequenceAllocator {
 public:
  std::uint64_t next() noexcept {
    return counter_.fetch_add(1, std::memory_order_relaxed);
  }

 private:
  std::atomic<std::uint64_t> counter_{1};
};

using SharedSequenceAllocator = std::shared_ptr<SequenceAllocator>;

inline SharedSequenceAllocator make_sequence_allocator() {
  return std::make_shared<SequenceAllocator>();
}

}  // namespace packet_probe
