#pragma once

#include "cli_options.hpp"
#include "run_common.hpp"

namespace packet_probe::cli {

int run_tcp_client(CliOptions const& options, StopRequested const& stop_requested);
int run_tcp_server(CliOptions const& options, StopRequested const& stop_requested);
int run_tcp_proxy(CliOptions const& options, StopRequested const& stop_requested);
int run_serial(CliOptions const& options, StopRequested const& stop_requested);
int run_udp(CliOptions const& options, StopRequested const& stop_requested);

}  // namespace packet_probe::cli
