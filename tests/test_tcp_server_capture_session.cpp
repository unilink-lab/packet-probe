#include <cassert>
#include "capture/tcp_server_capture_session.hpp"

int main() {
  packet_probe::TcpServerCaptureOptions options;
  assert(options.session_id == "tcp-server-1");
  assert(options.listen_host == "0.0.0.0");
  assert(options.listen_port == 0);
  return 0;
}
