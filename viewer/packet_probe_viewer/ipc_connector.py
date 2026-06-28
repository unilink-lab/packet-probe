import os
from PySide6.QtCore import QObject, QTimer, Signal


class IpcConnector(QObject):
    """Polls for a UDS socket file and signals when ready to connect."""
    ready = Signal()
    failed = Signal(str)

    def __init__(self, socket_path: str, max_attempts: int = 30, interval_ms: int = 100, parent=None):
        super().__init__(parent)
        self._socket_path = socket_path
        self._max_attempts = max_attempts
        self._interval_ms = interval_ms
        self._attempts = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._attempts = 0
        self._timer.start(self._interval_ms)

    def cancel(self) -> None:
        self._timer.stop()

    def _poll(self) -> None:
        self._attempts += 1
        if os.path.exists(self._socket_path):
            self._timer.stop()
            self.ready.emit()
            return
        if self._attempts >= self._max_attempts:
            self._timer.stop()
            self.failed.emit(
                f"IPC socket file was not created after {self._max_attempts} attempts: {self._socket_path}"
            )
