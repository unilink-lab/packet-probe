#include "packet_probe/core/jsonl_serializer.hpp"

#include "core/hex_dump.hpp"
#include "packet_probe/ipc/ipc_protocol.hpp"
#include "packet_probe/version.hpp"

namespace packet_probe {

namespace {

std::string escape_json(std::string const& value) {
  std::string escaped;
  escaped.reserve(value.size());
  for (char ch : value) {
    auto const byte = static_cast<unsigned char>(ch);
    switch (ch) {
      case '"':
        escaped += "\\\"";
        break;
      case '\\':
        escaped += "\\\\";
        break;
      case '\b':
        escaped += "\\b";
        break;
      case '\f':
        escaped += "\\f";
        break;
      case '\n':
        escaped += "\\n";
        break;
      case '\r':
        escaped += "\\r";
        break;
      case '\t':
        escaped += "\\t";
        break;
      default:
        if (byte < 0x20) {
          constexpr char digits[] = "0123456789ABCDEF";
          escaped += "\\u00";
          escaped += digits[(byte >> 4) & 0x0F];
          escaped += digits[byte & 0x0F];
        } else {
          escaped += ch;
        }
        break;
    }
  }
  return escaped;
}

}  // namespace

std::string serialize_metadata_jsonl() {
  std::string line;
  line += "{\"type\":\"metadata\",\"schema\":\"";
  line += kPacketProbeLogSchema;
  line += "\",\"event_schema\":\"";
  line += kPacketProbeEventSchema;
  line += "\",";
  line += "\"tool\":\"packet-probe\",\"version\":\"";
  line += PACKET_PROBE_VERSION;
  line += "\"}";
  return line;
}

std::string serialize_event_jsonl(PacketEvent const& event) {
  std::string line;
  line += "{\"seq\":";
  line += std::to_string(event.sequence);
  line += ",\"parent_seq\":";
  line += std::to_string(event.parent_sequence);
  line += ",\"time_ns\":";
  line += std::to_string(event.timestamp_ns);
  line += ",\"session\":\"";
  line += escape_json(event.session_id);
  line += "\",\"transport\":\"";
  line += escape_json(event.transport);
  line += "\",\"direction\":\"";
  line += to_string(event.direction);
  if (!event.source_endpoint.empty()) {
    line += "\",\"source\":\"";
    line += escape_json(event.source_endpoint);
  }
  if (!event.destination_endpoint.empty()) {
    line += "\",\"destination\":\"";
    line += escape_json(event.destination_endpoint);
  }
  line += "\",\"type\":\"";
  line += to_string(event.type);
  line += "\",\"size\":";
  line += std::to_string(event.payload.size());
  line += ",\"payload_hex\":\"";
  line += to_hex(event.payload, false);
  line += "\",\"summary\":\"";
  line += escape_json(event.summary);
  line += '"';
  if (!event.decoded_json.empty()) {
    line += ",\"decoded\":";
    line += event.decoded_json;
  }
  if (event.type == EventType::Latency) {
    line += ",\"request_seq\":";
    line += std::to_string(event.request_sequence);
    line += ",\"response_seq\":";
    line += std::to_string(event.response_sequence);
    line += ",\"latency_ns\":";
    line += std::to_string(event.latency_ns);
    line += ",\"latency_us\":";
    line += std::to_string(event.latency_ns / 1000);
    line += ",\"request_size\":";
    line += std::to_string(event.request_size);
    line += ",\"response_size\":";
    line += std::to_string(event.response_size);
  }
  line += '}';
  return line;
}

std::string serialize_jsonl(PacketEvent const& event) { return serialize_event_jsonl(event); }

}  // namespace packet_probe
