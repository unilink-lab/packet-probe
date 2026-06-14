#pragma once

#include <string>

#include "cli_options.hpp"

namespace packet_probe::cli {

bool parse_send_option(CliOptions& options, std::string const& arg, int& index, int argc, char** argv);

}  // namespace packet_probe::cli
