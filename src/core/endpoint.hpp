#pragma once

#include <cstdint>
#include <string>

namespace packet_probe {

struct Endpoint {
  std::string host;
  std::uint16_t port = 0;
};

std::string format_endpoint(std::string const& host, std::uint16_t port);
std::string format_endpoint(Endpoint const& endpoint);

}  // namespace packet_probe
