import json
from PySide6.QtCore import QThread, Signal, QObject

try:
    import unilink
except ImportError as exc:
    unilink = None
    _UNILINK_IMPORT_ERROR = exc

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
        self._client = None

    def run(self):
        if unilink is None:
            self.error_occurred.emit(
                f"unilink-python is not installed or failed to import: {_UNILINK_IMPORT_ERROR}. "
                "Install viewer dependencies and ensure unilink runtime libraries are available."
            )
            self.status_changed.emit("disconnected")
            self.disconnected.emit()
            return

        self._running = True
        self.status_changed.emit("connecting")

        try:
            client = unilink.UdsClient(self.socket_path)
            client.auto_start(False)
            client.use_line_framer("\n", False, 65536)
            client.on_connect(self._on_connect)
            client.on_disconnect(self._on_disconnect)
            client.on_error(self._on_error)
            client.on_message(self._on_message)
            self._client = client

            started = client.start_sync()
            if not started:
                self.error_occurred.emit("Connection failed")
                self.status_changed.emit("disconnected")
                self.disconnected.emit()
                return

            self.status_changed.emit("connected")

            while self._running and client.connected():
                self.msleep(50)

        except Exception as exc:
            if self._running:
                self.error_occurred.emit(f"IPC error: {exc}")

        finally:
            self._cleanup()
            self.status_changed.emit("disconnected")
            self.disconnected.emit()

    def _on_connect(self, ctx):
        pass

    def _on_disconnect(self, ctx):
        self._running = False

    def _on_error(self, ctx):
        try:
            message = getattr(ctx, "message", "")
        except Exception:
            message = ""
        if message:
            self.error_occurred.emit(f"IPC error: {message}")
        else:
            self.error_occurred.emit("IPC error")

    def _on_message(self, ctx):
        try:
            line = bytes(ctx.data).decode("utf-8")
            if not line:
                return

            obj = json.loads(line)
            if not isinstance(obj, dict):
                self.error_occurred.emit("Received malformed JSON line (not an object)")
                return

            if obj.get("type") == "metadata":
                self.metadata_received.emit(obj)
            else:
                self.event_received.emit(obj)

        except json.JSONDecodeError:
            self.error_occurred.emit("Failed to decode JSON line")
        except Exception as exc:
            self.error_occurred.emit(f"Message handling error: {exc}")

    def send_command(self, cmd: dict) -> None:
        client = self._client
        if client is not None and self._running:
            try:
                client.send_line(json.dumps(cmd))
            except Exception as exc:
                self.error_occurred.emit(f"Failed to send IPC command: {exc}")

    def stop(self):
        self._running = False

        client = self._client
        if client is not None:
            try:
                client.stop()
            except Exception as exc:
                self.error_occurred.emit(f"IPC stop error: {exc}")

    def _cleanup(self):
        client = self._client
        self._client = None

        if client is not None:
            try:
                client.stop()
            except Exception:
                pass
