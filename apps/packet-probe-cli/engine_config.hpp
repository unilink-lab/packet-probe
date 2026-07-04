#pragma once

#include <nlohmann/json.hpp>

#include "cli_options.hpp"

namespace packet_probe::cli {

// Converts capture-relevant CliOptions fields to/from the "configure" command's
// "config" JSON object. Mirrors the CLI's own option surface (see cli_options.hpp,
// cli_decoder_options.cpp) so a single set of parsing/validation rules applies to
// both process argv and IPC-driven engine configuration.
nlohmann::json engine_config_to_json(CliOptions const& options);
CliOptions engine_config_from_json(nlohmann::json const& config);

}  // namespace packet_probe::cli
