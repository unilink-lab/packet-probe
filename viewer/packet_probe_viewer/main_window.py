import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QTableView, QSplitter, QHeaderView, QMessageBox, QFileDialog,
    QPlainTextEdit, QGroupBox, QTabWidget
)
from PySide6.QtCore import Qt, QItemSelection, QModelIndex, QTimer
from .ipc_client import IpcClientWorker
from .event_model import PacketEvent
from .packet_table_model import PacketTableModel
from .widgets.hex_view import HexView
from .widgets.event_detail import EventDetailView
from .jsonl_log_loader import load_packet_probe_jsonl
from .ipc_path import make_default_ipc_path, resolve_initial_socket_path
from .capture_process import CaptureProcess

def format_metadata_message(metadata: dict | None) -> str:
    if not metadata:
        return ""
    schema = metadata.get("schema", "")
    event_schema = metadata.get("event_schema", "")
    version = metadata.get("version", "")
    return f"Metadata: schema={schema}, event_schema={event_schema}, version={version}"


class MainWindow(QMainWindow):
    def __init__(self, initial_socket_path: str = "/tmp/packet-probe.sock", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Packet Probe Viewer")
        self.resize(950, 800)  # Slightly taller layout for process logs

        self.generated_ipc_path = make_default_ipc_path()
        self.initial_socket_path = resolve_initial_socket_path(initial_socket_path)

        self.worker: IpcClientWorker | None = None
        self.capture_process = CaptureProcess(self)

        self._launcher_connect_pending = False
        self._launcher_connect_attempts = 0
        self._launcher_connect_max_attempts = 30

        self.is_paused = False
        self.pending_events: list[PacketEvent] = []

        self.setup_ui()
        self.set_mode("idle")

        # Connect capture process signals
        self.capture_process.started.connect(self.on_capture_started)
        self.capture_process.stopped.connect(self.on_capture_stopped)
        self.capture_process.error_occurred.connect(self.on_capture_error)
        self.capture_process.stdout_received.connect(self.on_capture_stdout)
        self.capture_process.stderr_received.connect(self.on_capture_stderr)

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Top Control Widget
        top_control_widget = QWidget(self)
        top_control_layout = QVBoxLayout(top_control_widget)
        top_control_layout.setContentsMargins(0, 0, 0, 0)

        # CLI Path Row
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("CLI Path:", self))
        default_cli = os.environ.get("PACKET_PROBE_CLI", "packet-probe")
        self.cli_path_edit = QLineEdit(default_cli, self)
        path_layout.addWidget(self.cli_path_edit)
        self.browse_cli_btn = QPushButton("Browse", self)
        self.browse_cli_btn.clicked.connect(self.browse_cli_path)
        path_layout.addWidget(self.browse_cli_btn)
        top_control_layout.addLayout(path_layout)

        # Args Row
        args_layout = QHBoxLayout()
        args_layout.addWidget(QLabel("Args:", self))
        self.cli_args_edit = QLineEdit("udp --bind-host 127.0.0.1 --bind-port 19000 --log udp.jsonl", self)
        args_layout.addWidget(self.cli_args_edit)
        top_control_layout.addLayout(args_layout)

        # Action Buttons Row
        action_btn_layout = QHBoxLayout()
        self.start_capture_btn = QPushButton("Start Capture", self)
        self.start_capture_btn.clicked.connect(self.start_capture)
        action_btn_layout.addWidget(self.start_capture_btn)

        self.stop_capture_btn = QPushButton("Stop Capture", self)
        self.stop_capture_btn.setEnabled(False)
        self.stop_capture_btn.clicked.connect(self.stop_capture)
        action_btn_layout.addWidget(self.stop_capture_btn)

        self.open_log_btn = QPushButton("Open Log", self)
        self.open_log_btn.clicked.connect(self.open_log_file)
        action_btn_layout.addWidget(self.open_log_btn)

        self.pause_btn = QPushButton("Pause", self)
        self.pause_btn.clicked.connect(self.toggle_pause)
        action_btn_layout.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.clicked.connect(self.clear_all)
        action_btn_layout.addWidget(self.clear_btn)
        action_btn_layout.addStretch()
        top_control_layout.addLayout(action_btn_layout)

        # IPC Status Row
        ipc_layout = QHBoxLayout()
        ipc_layout.addWidget(QLabel("Socket Path:", self))
        self.socket_path_edit = QLineEdit(self.initial_socket_path, self)
        ipc_layout.addWidget(self.socket_path_edit)

        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.clicked.connect(self.toggle_connection)
        ipc_layout.addWidget(self.connect_btn)
        top_control_layout.addLayout(ipc_layout)

        status_layout = QHBoxLayout()
        self.status_label = QLabel("Status: disconnected", self)
        status_layout.addWidget(self.status_label)
        self.mode_label = QLabel("Mode: idle", self)
        status_layout.addWidget(self.mode_label)
        status_layout.addStretch()
        top_control_layout.addLayout(status_layout)

        main_layout.addWidget(top_control_widget)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        
        open_action = file_menu.addAction("&Open Log...")
        open_action.triggered.connect(self.open_log_file)
        
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

        # Main Splitter
        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        main_layout.addWidget(main_splitter)

        self.table_model = PacketTableModel(self)
        self.table_view = QTableView(self)
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        main_splitter.addWidget(self.table_view)

        # Bottom Detail Tabs
        self.detail_tabs = QTabWidget(self)

        self.hex_view = HexView(self)
        self.detail_view = EventDetailView(self)
        self.process_output = QPlainTextEdit(self)
        self.process_output.setReadOnly(True)

        self.detail_tabs.addTab(self.hex_view, "Hex")
        self.detail_tabs.addTab(self.detail_view, "JSON")
        self.detail_tabs.addTab(self.process_output, "Process Log")

        main_splitter.addWidget(self.detail_tabs)

        main_splitter.setSizes([600, 220])

        self.message_label = QLabel("", self)
        main_layout.addWidget(self.message_label)

    def toggle_connection(self):
        if self.worker and self.worker.isRunning():
            self.disconnect_socket()
        else:
            self.connect_socket()

    def connect_socket(self):
        socket_path = self.socket_path_edit.text().strip()
        if not socket_path:
            QMessageBox.warning(self, "Warning", "Socket path is empty.")
            return

        # Synchronously update UI controls to connecting state to prevent duplicate clicks
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")
        self.socket_path_edit.setEnabled(False)
        self.message_label.setText("")

        self.worker = IpcClientWorker(socket_path, self)
        self.worker.status_changed.connect(self.on_status_changed)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.event_received.connect(self.on_event_received)
        self.worker.metadata_received.connect(self.on_metadata_received)
        self.worker.disconnected.connect(self.on_worker_finished)
        self.worker.start()

    def disconnect_socket(self):
        self._launcher_connect_pending = False
        if self.worker:
            self.worker.stop()
            self.worker = None

    def on_status_changed(self, status: str):
        self.status_label.setText(f"Status: {status}")
        if status == "connecting":
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText("Connecting...")
            self.message_label.setText("")
        elif status == "connected":
            self._launcher_connect_pending = False
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Disconnect")
            self.socket_path_edit.setEnabled(False)
            self.clear_all()
            self.message_label.setText("Live mode started")
            if self.capture_process.is_running():
                self.status_label.setText("Status: capture running")
                self.set_mode("launcher")
            else:
                self.status_label.setText("Status: connected")
                self.set_mode("live")
        elif status == "disconnected":
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Connect")
            self.socket_path_edit.setEnabled(True)
            if not self.capture_process.is_running():
                self.set_mode("idle")

    def set_mode(self, mode: str):
        self.mode_label.setText(f"Mode: {mode}")

    def on_error_occurred(self, error_msg: str):
        self.message_label.setText(f"Error: {error_msg}")

    def on_metadata_received(self, metadata: dict):
        self.message_label.setText(format_metadata_message(metadata))

    def on_event_received(self, event_dict: dict):
        event = PacketEvent(event_dict)
        if self.is_paused:
            self.pending_events.append(event)
        else:
            self.table_model.append_event(event)
            self.table_view.scrollToBottom()

    def on_worker_finished(self):
        self.on_status_changed("disconnected")
        self.worker = None

        if self._launcher_connect_pending and self.capture_process.is_running():
            if self._launcher_connect_attempts < self._launcher_connect_max_attempts:
                QTimer.singleShot(100, self._try_launcher_connect)
            else:
                self._launcher_connect_pending = False
                self.message_label.setText("Error: IPC socket was not ready after launcher retry timeout")
                self.set_mode("idle")
        else:
            if not self.capture_process.is_running():
                self.set_mode("idle")

    def _try_launcher_connect(self):
        if not self._launcher_connect_pending:
            return
        if not self.capture_process.is_running():
            self._launcher_connect_pending = False
            return
        if self.worker and self.worker.isRunning():
            return

        socket_path = self.socket_path_edit.text().strip()
        if not socket_path:
            self._launcher_connect_pending = False
            self.message_label.setText("Error: generated IPC socket path is empty")
            return

        self._launcher_connect_attempts += 1
        self.connect_socket()

    def _set_capture_controls_running(self, running: bool):
        self.start_capture_btn.setEnabled(not running)
        self.stop_capture_btn.setEnabled(running)
        self.cli_path_edit.setEnabled(not running)
        self.cli_args_edit.setEnabled(not running)
        self.browse_cli_btn.setEnabled(not running)

    def _restore_capture_controls(self):
        self._set_capture_controls_running(False)

    def toggle_pause(self):
        if self.is_paused:
            self.is_paused = False
            self.pause_btn.setText("Pause")
            for event in self.pending_events:
                self.table_model.append_event(event)
            self.pending_events.clear()
            self.table_view.scrollToBottom()
        else:
            self.is_paused = True
            self.pause_btn.setText("Resume")

    def clear_all(self):
        self.table_model.clear()
        self.pending_events.clear()
        self.hex_view.clear()
        self.detail_view.clear()

    def on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        indexes = selected.indexes()
        if not indexes:
            self.hex_view.clear()
            self.detail_view.clear()
            return

        row = indexes[0].row()
        event = self.table_model.event_at(row)
        if event:
            self.hex_view.set_payload_hex(event.payload_hex)
            self.detail_view.set_event(event)

    def browse_cli_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select packet-probe CLI executable",
            "",
            "Executables (*.exe *packet-probe*);;All Files (*)"
        )
        if path:
            self.cli_path_edit.setText(path)

    def start_capture(self):
        executable = self.cli_path_edit.text().strip()
        if not executable:
            QMessageBox.warning(self, "Warning", "CLI Path is empty.")
            return

        args_text = self.cli_args_edit.text().strip()

        from .ipc_path import make_default_ipc_path
        self.generated_ipc_path = make_default_ipc_path()
        self.socket_path_edit.setText(self.generated_ipc_path)

        from .capture_command import build_capture_command
        try:
            cmd = build_capture_command(executable, args_text, self.generated_ipc_path)
        except ValueError as exc:
            QMessageBox.warning(self, "Warning", str(exc))
            return

        if self.worker and self.worker.isRunning():
            self.disconnect_socket()

        self.clear_all()
        self.process_output.clear()

        # Clean up existing socket at the path (Unix stale socket requirement)
        from pathlib import Path
        try:
            Path(self.generated_ipc_path).unlink(missing_ok=True)
        except Exception:
            pass

        self.process_output.appendPlainText(f"[system] Starting CLI: {cmd.executable} " + " ".join(cmd.args))
        self._set_capture_controls_running(True)
        self.set_mode("launcher")
        self.status_label.setText("Status: launching")

        try:
            self.capture_process.start(cmd.executable, cmd.args)
        except Exception as exc:
            self.process_output.appendPlainText(f"[system] Failed to start process: {exc}")
            self.on_capture_stopped(-1, "FailedToStart")

    def stop_capture(self):
        self._launcher_connect_pending = False
        self.process_output.appendPlainText("[system] Stopping CLI process...")
        self.capture_process.stop()
        self.disconnect_socket()

    def on_capture_started(self):
        self.process_output.appendPlainText("[system] CLI process started successfully.")
        self._launcher_connect_pending = True
        self._launcher_connect_attempts = 0
        QTimer.singleShot(100, self._try_launcher_connect)

    def on_capture_stopped(self, exit_code, exit_status):
        self._launcher_connect_pending = False
        self.process_output.appendPlainText(f"[system] CLI process stopped. Exit code: {exit_code} ({exit_status})")
        self._restore_capture_controls()
        self.disconnect_socket()
        self.set_mode("idle")
        self.status_label.setText("Status: disconnected")

    def on_capture_error(self, msg):
        self.process_output.appendPlainText(f"[stderr] Process error: {msg}")
        if not self.capture_process.is_running():
            self._launcher_connect_pending = False
            self._restore_capture_controls()

    def on_capture_stdout(self, data):
        text = data.rstrip()
        if text:
            self.process_output.appendPlainText(f"[stdout] {text}")

    def on_capture_stderr(self, data):
        text = data.rstrip()
        if text:
            self.process_output.appendPlainText(f"[stderr] {text}")

    def open_log_file(self) -> None:
        if self.capture_process.is_running():
            reply = QMessageBox.question(
                self,
                "Capture Running",
                "Capture is running. Stop capture and open log?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_capture()
            else:
                return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Packet Probe JSONL Log",
            "",
            "JSONL Files (*.jsonl);;All Files (*)",
        )
        if not path:
            return

        if self.worker and self.worker.isRunning():
            self.disconnect_socket()

        self.clear_all()

        try:
            result = load_packet_probe_jsonl(path)
        except Exception as exc:
            self.message_label.setText(f"Error loading log: {exc}")
            return

        events = [PacketEvent(e) for e in result.events]
        self.table_model.set_events(events)

        self.set_mode("offline")
        self.status_label.setText("Status: offline log")

        meta_msg = format_metadata_message(result.metadata)
        filename = os.path.basename(path)
        count = len(result.events)
        malformed_count = len(result.malformed_lines)

        if malformed_count > 0:
            first_malformed_num = result.malformed_lines[0][0]
            msg = f"Loaded {count} events from {filename} with {malformed_count} malformed lines. First malformed line: {first_malformed_num}"
        else:
            msg = f"Loaded {count} events from {filename}"

        if meta_msg:
            self.message_label.setText(f"{meta_msg}\n{msg}")
        else:
            self.message_label.setText(msg)

    def closeEvent(self, event):
        self.stop_capture()
        self.disconnect_socket()
        event.accept()
