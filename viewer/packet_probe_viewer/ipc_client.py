import socket
import json
from PySide6.QtCore import QThread, Signal, QObject

class IpcClientWorker(QThread):
    metadata_received = Signal(dict)
    event_received = Signal(dict)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    disconnected = Signal()

    def __init__(self, socket_path: str, parent: QObject | None = None):
        super().__init__(parent)
        self.socket_path = socket_path
        self._running = False
        self._socket = None

    def run(self):
        self._running = True
        self.status_changed.emit("connecting")
        try:
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(self.socket_path)
            self._socket.settimeout(0.5)
            self.status_changed.emit("connected")
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {e}")
            self.cleanup()
            self.status_changed.emit("disconnected")
            self.disconnected.emit()
            return

        buffer = ""
        while self._running:
            try:
                data = self._socket.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if not isinstance(obj, dict):
                            self.error_occurred.emit("Received malformed JSON line (not an object)")
                            continue
                        if obj.get("type") == "metadata":
                            self.metadata_received.emit(obj)
                        else:
                            self.event_received.emit(obj)
                    except json.JSONDecodeError:
                        self.error_occurred.emit("Failed to decode JSON line")
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self.error_occurred.emit(f"Read error: {e}")
                break

        self.cleanup()
        self.status_changed.emit("disconnected")
        self.disconnected.emit()

    def stop(self):
        self._running = False
        sock = self._socket
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        if self.isRunning() and not self.wait(2000):
            self.error_occurred.emit("IPC worker did not stop within 2 seconds")

        self.cleanup()

    def cleanup(self):
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
