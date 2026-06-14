#pragma once

#include <string>

#include "packet_probe/packet_event.hpp"

namespace packet_probe {

std::string serialize_metadata_jsonl();
std::string serialize_event_jsonl(PacketEvent const& event);

// Compatibility alias for existing recorder/tests.
std::string serialize_jsonl(PacketEvent const& event);

}  // namespace packet_probe
