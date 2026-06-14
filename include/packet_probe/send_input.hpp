#pragma once

#include <string>

namespace packet_probe {

enum class SendInputFormat {
  Text,
  Hex,
  File
};

struct SendInputOptions {
  SendInputFormat format = SendInputFormat::Text;
  std::string file_path;
};

}  // namespace packet_probe
