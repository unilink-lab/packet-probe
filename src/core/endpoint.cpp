#include "packet_probe/endpoint.hpp"

namespace packet_probe {

std::string format_endpoint(std::string const& host, std::uint16_t port) {
  return host + ":" + std::to_string(port);
}

std::string format_endpoint(Endpoint const& endpoint) { return format_endpoint(endpoint.host, endpoint.port); }

}  // namespace packet_probe
