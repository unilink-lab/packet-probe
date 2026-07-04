from PySide6.QtCore import QObject, QProcess, Signal

class CaptureProcess(QObject):
    started = Signal()
    stopped = Signal(int, str)  # exit_code, exit_status_str
    error_occurred = Signal(str)
    stdout_received = Signal(str)
    stderr_received = Signal(str)
    state_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._handle_stdout)
        self._process.readyReadStandardError.connect(self._handle_stderr)
        self._process.started.connect(self.started.emit)
        self._process.finished.connect(self._handle_finished)
        self._process.errorOccurred.connect(self._handle_error)
        self._process.stateChanged.connect(self._handle_state_changed)

    def start(self, executable: str, args: list[str], working_dir: str | None = None) -> None:
        if working_dir:
            self._process.setWorkingDirectory(working_dir)
        self._process.start(executable, args)

    def stop(self, timeout_ms: int = 3000) -> None:
        if self._process.state() == QProcess.ProcessState.NotRunning:
            return

        # The engine (packet-probe engine --ipc ...) doesn't read stdin; it exits on
        # SIGTERM via terminate() below. closeWriteChannel() is a harmless no-op here,
        # kept for parity with QProcess children that do read stdin.
        self._process.closeWriteChannel()
        self._process.terminate()
        if not self._process.waitForFinished(timeout_ms):
            self._process.kill()
            self._process.waitForFinished(1000)

    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def _handle_stdout(self):
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self.stdout_received.emit(data)

    def _handle_stderr(self):
        data = self._process.readAllStandardError().data().decode("utf-8", errors="replace")
        self.stderr_received.emit(data)

    def _handle_finished(self, exit_code, exit_status):
        status_str = "NormalExit" if exit_status == QProcess.ExitStatus.NormalExit else "CrashExit"
        self.stopped.emit(exit_code, status_str)

    def _handle_error(self, error):
        error_msgs = {
            QProcess.ProcessError.FailedToStart: "The process failed to start. Either the invoked program is missing, or you may have insufficient permissions.",
            QProcess.ProcessError.Crashed: "The process crashed some time after starting successfully.",
            QProcess.ProcessError.Timedout: "The last waitFor...() function timed out.",
            QProcess.ProcessError.WriteError: "An error occurred when attempting to write to the process.",
            QProcess.ProcessError.ReadError: "An error occurred when attempting to read from the process.",
            QProcess.ProcessError.UnknownError: "An unknown error occurred."
        }
        msg = error_msgs.get(error, f"Unknown process error code {error}")
        self.error_occurred.emit(msg)

    def _handle_state_changed(self, state):
        state_strs = {
            QProcess.ProcessState.NotRunning: "NotRunning",
            QProcess.ProcessState.Starting: "Starting",
            QProcess.ProcessState.Running: "Running"
        }
        self.state_changed.emit(state_strs.get(state, "Unknown"))
