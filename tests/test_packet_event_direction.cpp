#include <cassert>
#include <string>

#include "packet_probe/packet_event.hpp"

int main() {
  assert(std::string(packet_probe::to_string(packet_probe::Direction::AppToDevice)) == "app_to_device");
  assert(std::string(packet_probe::to_string(packet_probe::Direction::DeviceToApp)) == "device_to_app");
  assert(std::string(packet_probe::to_string(packet_probe::Direction::Rx)) == "rx");
  assert(std::string(packet_probe::to_string(packet_probe::Direction::Tx)) == "tx");
  assert(std::string(packet_probe::to_string(packet_probe::EventType::Latency)) == "latency");

  return 0;
}
