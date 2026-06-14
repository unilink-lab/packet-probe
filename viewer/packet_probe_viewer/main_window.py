import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QTableView, QSplitter, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, QItemSelection, QModelIndex
from .ipc_client import IpcClientWorker
from .event_model import PacketEvent
from .packet_table_model import PacketTableModel
from .widgets.hex_view import HexView
from .widgets.event_detail import EventDetailView

class MainWindow(QMainWindow):
    def __init__(self, initial_socket_path: str = "/tmp/packet-probe.sock", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Packet Probe Viewer")
        self.resize(950, 700)

        self.initial_socket_path = initial_socket_path
        self.worker: IpcClientWorker | None = None

        self.is_paused = False
        self.pending_events: list[PacketEvent] = []

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        ctrl_layout = QHBoxLayout()

        ctrl_layout.addWidget(QLabel("Socket Path:"))
        self.socket_path_edit = QLineEdit(self.initial_socket_path, self)
        ctrl_layout.addWidget(self.socket_path_edit)

        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.clicked.connect(self.toggle_connection)
        ctrl_layout.addWidget(self.connect_btn)

        self.status_label = QLabel("Status: disconnected", self)
        ctrl_layout.addWidget(self.status_label)

        self.pause_btn = QPushButton("Pause", self)
        self.pause_btn.clicked.connect(self.toggle_pause)
        ctrl_layout.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.clicked.connect(self.clear_all)
        ctrl_layout.addWidget(self.clear_btn)

        main_layout.addLayout(ctrl_layout)

        self.message_label = QLabel("", self)
        main_layout.addWidget(self.message_label)

        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        main_layout.addWidget(main_splitter)

        self.table_model = PacketTableModel(self)
        self.table_view = QTableView(self)
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.SectionResizeMode.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        main_splitter.addWidget(self.table_view)

        detail_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_splitter.addWidget(detail_splitter)

        self.hex_view = HexView(self)
        detail_splitter.addWidget(self.hex_view)

        self.detail_view = EventDetailView(self)
        detail_splitter.addWidget(self.detail_view)

        main_splitter.setSizes([400, 250])
        detail_splitter.setSizes([475, 475])

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
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Disconnect")
            self.socket_path_edit.setEnabled(False)
        elif status == "disconnected":
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Connect")
            self.socket_path_edit.setEnabled(True)

    def on_error_occurred(self, error_msg: str):
        self.message_label.setText(f"Error: {error_msg}")

    def on_metadata_received(self, metadata: dict):
        schema = metadata.get("schema", "")
        event_schema = metadata.get("event_schema", "")
        version = metadata.get("version", "")
        self.message_label.setText(
            f"Metadata: schema={schema}, event_schema={event_schema}, version={version}"
        )

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

    def closeEvent(self, event):
        self.disconnect_socket()
        event.accept()
