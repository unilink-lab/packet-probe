#pragma once

namespace packet_probe {

class CaptureSession {
 public:
  virtual ~CaptureSession() = default;

  virtual void start() = 0;
  virtual void stop() = 0;
};

}  // namespace packet_probe
