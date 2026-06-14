#pragma once

#include <cstdint>
#include <string>

namespace packet_probe {

enum class SerialParity { None, Odd, Even };

enum class SerialFlowControl { None, Software, Hardware };

struct SerialCaptureOptions {
  std::string port;
  std::uint32_t baudrate = 115200;
  std::uint8_t data_bits = 8;
  std::uint8_t stop_bits = 1;
  SerialParity parity = SerialParity::None;
  SerialFlowControl flow_control = SerialFlowControl::None;
  std::string session_id = "serial-1";
};

SerialParity parse_serial_parity(std::string const& value);
SerialFlowControl parse_serial_flow_control(std::string const& value);
std::uint8_t parse_serial_data_bits(std::string const& value);
std::uint8_t parse_serial_stop_bits(std::string const& value);
std::uint32_t parse_serial_baudrate(std::string const& value);

const char* to_string(SerialParity parity);
const char* to_string(SerialFlowControl flow_control);

}  // namespace packet_probe
