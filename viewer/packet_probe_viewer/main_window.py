import json
import os
import re
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QTableView, QSplitter, QHeaderView, QMessageBox, QFileDialog,
    QPlainTextEdit, QGroupBox, QTabWidget, QComboBox, QRadioButton, QStackedWidget,
    QSpinBox, QCheckBox, QGridLayout, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QItemSelection, QModelIndex, QTimer, QSettings
from PySide6.QtGui import QFont, QIntValidator
from .ipc_client import IpcClientWorker
from .event_model import PacketEvent
from .packet_table_model import PacketTableModel, PacketFilterProxyModel
from .widgets.hex_view import HexView
from .widgets.event_detail import EventDetailView
from .jsonl_log_loader import load_packet_probe_jsonl
from .ipc_path import make_default_ipc_path, resolve_initial_socket_path
from .capture_process import CaptureProcess
from .capture_command import build_capture_config, build_decoder_config, engine_mode_for_ui, supports_send
from .styles import DARK_THEME_QSS
from .viewer_settings import ViewerState, ViewerSettingsManager
from .ipc_connector import IpcConnector


def find_packet_probe_binary() -> str:
    # 1. Check environment variable
    env_path = os.environ.get("PACKET_PROBE_CLI")
    if env_path:
        return env_path

    # 2. Check workspace build directory relative to this file
    try:
        current_dir = Path(__file__).resolve().parent
        workspace_root = current_dir.parents[1]

        build_bin = workspace_root / "build" / "packet-probe"
        if build_bin.exists() and os.access(build_bin, os.X_OK):
            return str(build_bin)

        build_bin_alt = workspace_root / "build" / "apps" / "packet-probe-cli" / "packet-probe"
        if build_bin_alt.exists() and os.access(build_bin_alt, os.X_OK):
            return str(build_bin_alt)
    except Exception:
        pass

    return "packet-probe"


def format_metadata_message(metadata: dict | None) -> str:
    if not metadata:
        return ""
    schema = metadata.get("schema", "")
    event_schema = metadata.get("event_schema", "")
    version = metadata.get("version", "")
    return f"Metadata: schema={schema}, event_schema={event_schema}, version={version}"


class MainWindow(QMainWindow):
    def __init__(self, initial_socket_path: str = "/tmp/packet-probe.sock", settings_org: str = "UnilinkLab", settings_app: str = "PacketProbeViewer", parent=None):
        super().__init__(parent)
        self.setStyleSheet(DARK_THEME_QSS)
        self.setWindowTitle("Packet Probe Viewer")
        self.resize(950, 800)

        self.generated_ipc_path = make_default_ipc_path()
        self.initial_socket_path = resolve_initial_socket_path(initial_socket_path)

        self.worker: IpcClientWorker | None = None
        self.capture_process = CaptureProcess(self)
        self._ipc_connector: IpcConnector | None = None
        self._ipc_connected = False
        self._active_capture_mode = ""

        # Engine control protocol v2 state (see docs/ipc-protocol.md). Once connected,
        # the viewer drives capture entirely through configure/start_capture/
        # stop_capture commands rather than process spawn/kill, so a config change no
        # longer requires restarting the packet-probe process.
        self._engine_state = "idle"
        # command id -> intent, so on_result_received can react per-command
        # ("configure", "start_capture", "stop_capture", "send").
        self._pending_commands: dict[str, str] = {}
        # True once the viewer itself has issued start_capture and is waiting for
        # engine confirmation; distinguishes "we're starting" from "someone else's
        # capture is already running" when a status broadcast arrives.
        self._starting_capture = False
        # Config queued by start_capture() while we wait for the engine
        # process/connection to come up, applied once on_status_changed("connected") fires.
        self._pending_config_to_start: dict | None = None

        self.is_paused = False
        self.pending_events: list[PacketEvent] = []
        self._event_count = 0
        self._error_count = 0

        self.setup_ui()
        self._settings_manager = ViewerSettingsManager(settings_org, settings_app)
        self.load_settings()
        self.set_mode("idle")
        self.update_status("Status: disconnected")
        self.update_port("-")
        self.update_conn_mode(self.mode_combo.currentText())

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

        # Row 1: Action Buttons, Status Indicators & Settings Toggle
        action_btn_layout = QHBoxLayout()
        self.start_capture_btn = QPushButton("Start Capture", self)
        self.start_capture_btn.setObjectName("start_capture_btn")
        self.start_capture_btn.clicked.connect(self.start_capture)
        action_btn_layout.addWidget(self.start_capture_btn)

        self.stop_capture_btn = QPushButton("Stop Capture", self)
        self.stop_capture_btn.setObjectName("stop_capture_btn")
        self.stop_capture_btn.setEnabled(False)
        self.stop_capture_btn.clicked.connect(self.stop_capture)
        action_btn_layout.addWidget(self.stop_capture_btn)

        self.pause_btn = QPushButton("Pause", self)
        self.pause_btn.clicked.connect(self.toggle_pause)
        action_btn_layout.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.clicked.connect(self.clear_all)
        action_btn_layout.addWidget(self.clear_btn)

        action_btn_layout.addStretch()

        self.toggle_settings_btn = QPushButton("⚙️ Settings", self)
        self.toggle_settings_btn.clicked.connect(self.open_settings_dialog)
        action_btn_layout.addWidget(self.toggle_settings_btn)

        top_control_layout.addLayout(action_btn_layout)

        # Connection Config Group (Collapsible, Split Layout internally)
        self.conn_group = QGroupBox("Configuration", self)
        conn_layout = QVBoxLayout(self.conn_group)

        # Split Config into Left (Connection) and Right (Decoder)
        split_config_layout = QHBoxLayout()

        # Left Widget: Connection Settings
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:", self))
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(["UDP", "TCP Client", "TCP Server", "TCP Proxy", "Serial"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        left_layout.addLayout(mode_layout)

        self.mode_help_label = QLabel(self)
        self.mode_help_label.setWordWrap(True)
        self.mode_help_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        left_layout.addWidget(self.mode_help_label)

        # Parameter Stacked Widget
        self.param_stack = QStackedWidget(self)
        left_layout.addWidget(self.param_stack)

        # 1. UDP Panel
        udp_widget = QWidget(self)
        udp_grid = QGridLayout(udp_widget)
        udp_grid.setContentsMargins(0, 5, 0, 5)
        udp_grid.setSpacing(6)
        udp_grid.addWidget(QLabel("Bind Host:", self), 0, 0)
        self.udp_bind_host = QLineEdit("0.0.0.0", self)
        self.udp_bind_host.textChanged.connect(self.update_config_preview)
        udp_grid.addWidget(self.udp_bind_host, 0, 1)
        udp_grid.addWidget(QLabel("Bind Port:", self), 0, 2)
        self.udp_bind_port = QLineEdit("19000", self)
        self.udp_bind_port.setValidator(QIntValidator(1, 65535, self))
        self.udp_bind_port.textChanged.connect(self.update_config_preview)
        udp_grid.addWidget(self.udp_bind_port, 0, 3)
        udp_grid.addWidget(QLabel("Target Host:", self), 1, 0)
        self.udp_target_host = QLineEdit("127.0.0.1", self)
        self.udp_target_host.textChanged.connect(self.update_config_preview)
        udp_grid.addWidget(self.udp_target_host, 1, 1)
        udp_grid.addWidget(QLabel("Target Port:", self), 1, 2)
        self.udp_target_port = QLineEdit("19085", self)
        self.udp_target_port.setValidator(QIntValidator(1, 65535, self))
        self.udp_target_port.textChanged.connect(self.update_config_preview)
        udp_grid.addWidget(self.udp_target_port, 1, 3)
        self.param_stack.addWidget(udp_widget)

        # 2. TCP Client Panel
        tcp_client_widget = QWidget(self)
        tcp_client_grid = QGridLayout(tcp_client_widget)
        tcp_client_grid.setContentsMargins(0, 5, 0, 5)
        tcp_client_grid.setSpacing(6)
        tcp_client_grid.addWidget(QLabel("Remote Host:", self), 0, 0)
        self.tcp_cli_host = QLineEdit("127.0.0.1", self)
        self.tcp_cli_host.textChanged.connect(self.update_config_preview)
        tcp_client_grid.addWidget(self.tcp_cli_host, 0, 1)
        tcp_client_grid.addWidget(QLabel("Remote Port:", self), 0, 2)
        self.tcp_cli_port = QLineEdit("19085", self)
        self.tcp_cli_port.setValidator(QIntValidator(1, 65535, self))
        self.tcp_cli_port.textChanged.connect(self.update_config_preview)
        tcp_client_grid.addWidget(self.tcp_cli_port, 0, 3)
        self.param_stack.addWidget(tcp_client_widget)

        # 3. TCP Server Panel
        tcp_server_widget = QWidget(self)
        tcp_server_grid = QGridLayout(tcp_server_widget)
        tcp_server_grid.setContentsMargins(0, 5, 0, 5)
        tcp_server_grid.setSpacing(6)
        tcp_server_grid.addWidget(QLabel("Listen Host:", self), 0, 0)
        self.tcp_srv_host = QLineEdit("0.0.0.0", self)
        self.tcp_srv_host.textChanged.connect(self.update_config_preview)
        tcp_server_grid.addWidget(self.tcp_srv_host, 0, 1)
        tcp_server_grid.addWidget(QLabel("Listen Port:", self), 0, 2)
        self.tcp_srv_port = QLineEdit("19085", self)
        self.tcp_srv_port.setValidator(QIntValidator(1, 65535, self))
        self.tcp_srv_port.textChanged.connect(self.update_config_preview)
        tcp_server_grid.addWidget(self.tcp_srv_port, 0, 3)
        self.param_stack.addWidget(tcp_server_widget)

        # 4. TCP Proxy Panel
        tcp_proxy_widget = QWidget(self)
        tcp_proxy_grid = QGridLayout(tcp_proxy_widget)
        tcp_proxy_grid.setContentsMargins(0, 5, 0, 5)
        tcp_proxy_grid.setSpacing(6)
        tcp_proxy_grid.addWidget(QLabel("Listen Host:", self), 0, 0)
        self.tcp_prx_listen_host = QLineEdit("127.0.0.1", self)
        self.tcp_prx_listen_host.textChanged.connect(self.update_config_preview)
        tcp_proxy_grid.addWidget(self.tcp_prx_listen_host, 0, 1)
        tcp_proxy_grid.addWidget(QLabel("Listen Port:", self), 0, 2)
        self.tcp_prx_listen_port = QLineEdit("19000", self)
        self.tcp_prx_listen_port.setValidator(QIntValidator(1, 65535, self))
        self.tcp_prx_listen_port.textChanged.connect(self.update_config_preview)
        tcp_proxy_grid.addWidget(self.tcp_prx_listen_port, 0, 3)
        tcp_proxy_grid.addWidget(QLabel("Target Host:", self), 1, 0)
        self.tcp_prx_target_host = QLineEdit("127.0.0.1", self)
        self.tcp_prx_target_host.textChanged.connect(self.update_config_preview)
        tcp_proxy_grid.addWidget(self.tcp_prx_target_host, 1, 1)
        tcp_proxy_grid.addWidget(QLabel("Target Port:", self), 1, 2)
        self.tcp_prx_target_port = QLineEdit("19085", self)
        self.tcp_prx_target_port.setValidator(QIntValidator(1, 65535, self))
        self.tcp_prx_target_port.textChanged.connect(self.update_config_preview)
        tcp_proxy_grid.addWidget(self.tcp_prx_target_port, 1, 3)
        self.param_stack.addWidget(tcp_proxy_widget)

        # 5. Serial Panel
        serial_widget = QWidget(self)
        serial_grid = QGridLayout(serial_widget)
        serial_grid.setContentsMargins(0, 5, 0, 5)
        serial_grid.setSpacing(6)
        serial_grid.addWidget(QLabel("Port Path:", self), 0, 0)
        self.ser_port = QComboBox(self)
        self.ser_port.setEditable(True)
        self.ser_port.addItem("/dev/ttyUSB0")
        self.ser_port.setCurrentText("/dev/ttyUSB0")
        self.ser_port.currentIndexChanged.connect(self.update_config_preview)
        self.ser_port.editTextChanged.connect(self.update_config_preview)
        serial_grid.addWidget(self.ser_port, 0, 1)
        self.ser_port_refresh_btn = QPushButton("Refresh", self)
        self.ser_port_refresh_btn.setToolTip(
            "Ask the connected engine to list available serial ports (list_serial_ports command)."
        )
        self.ser_port_refresh_btn.clicked.connect(self.refresh_serial_ports)
        serial_grid.addWidget(self.ser_port_refresh_btn, 0, 4)
        serial_grid.addWidget(QLabel("Baud Rate:", self), 0, 2)
        self.ser_baud = QComboBox(self)
        self.ser_baud.setEditable(True)
        self.ser_baud.addItems([
            "1200", "2400", "4800", "9600", "19200", "38400",
            "57600", "115200", "230400", "460800", "921600"
        ])
        self.ser_baud.setCurrentText("115200")
        self.ser_baud.currentIndexChanged.connect(self.update_config_preview)
        self.ser_baud.editTextChanged.connect(self.update_config_preview)
        serial_grid.addWidget(self.ser_baud, 0, 3)
        self.param_stack.addWidget(serial_widget)

        split_config_layout.addWidget(left_widget, 1)

        # Right Widget: Frame Decoder Settings
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        dec_combo_layout = QHBoxLayout()
        dec_combo_layout.addWidget(QLabel("Decoder:", self))
        self.decoder_combo = QComboBox(self)
        self.decoder_combo.addItems(["raw", "fixed", "delimiter", "length-prefix"])
        self.decoder_combo.currentIndexChanged.connect(self.on_decoder_changed)
        dec_combo_layout.addWidget(self.decoder_combo)
        dec_combo_layout.addStretch()
        right_layout.addLayout(dec_combo_layout)

        # Decoder parameters stack
        self.decoder_param_stack = QStackedWidget(self)
        right_layout.addWidget(self.decoder_param_stack)

        # Decoder Stack 1: Raw (Empty)
        dec_raw_widget = QWidget(self)
        dec_raw_layout = QHBoxLayout(dec_raw_widget)
        dec_raw_layout.setContentsMargins(0, 5, 0, 5)
        dec_raw_layout.addWidget(QLabel("Raw bytes mode - no frame boundary detection", self))
        dec_raw_layout.addStretch()
        self.decoder_param_stack.addWidget(dec_raw_widget)

        # Decoder Stack 2: Fixed Size
        dec_fixed_widget = QWidget(self)
        dec_fixed_layout = QHBoxLayout(dec_fixed_widget)
        dec_fixed_layout.setContentsMargins(0, 5, 0, 5)
        dec_fixed_layout.addWidget(QLabel("Frame Size:", self))
        self.dec_fixed_size = QSpinBox(self)
        self.dec_fixed_size.setRange(1, 1000000)
        self.dec_fixed_size.setValue(16)
        self.dec_fixed_size.valueChanged.connect(self.update_config_preview)
        dec_fixed_layout.addWidget(self.dec_fixed_size)
        dec_fixed_layout.addStretch()
        self.decoder_param_stack.addWidget(dec_fixed_widget)

        # Decoder Stack 3: Delimiter
        dec_delim_widget = QWidget(self)
        dec_delim_layout = QHBoxLayout(dec_delim_widget)
        dec_delim_layout.setContentsMargins(0, 5, 0, 5)
        dec_delim_layout.addWidget(QLabel("Delimiter (Hex):", self))
        self.dec_delim_edit = QLineEdit("0A", self)
        self.dec_delim_edit.setPlaceholderText("e.g. 0A or 0D0A")
        self.dec_delim_edit.textChanged.connect(self.update_config_preview)
        dec_delim_layout.addWidget(self.dec_delim_edit)
        self.dec_delim_inc_cb = QCheckBox("Include Delimiter", self)
        self.dec_delim_inc_cb.setChecked(False)
        self.dec_delim_inc_cb.toggled.connect(self.update_config_preview)
        dec_delim_layout.addWidget(self.dec_delim_inc_cb)
        self.decoder_param_stack.addWidget(dec_delim_widget)

        # Decoder Stack 4: Length-Prefix
        dec_len_widget = QWidget(self)
        dec_len_layout = QHBoxLayout(dec_len_widget)
        dec_len_layout.setContentsMargins(0, 5, 0, 5)
        dec_len_layout.addWidget(QLabel("Length Size:", self))
        self.dec_len_size_combo = QComboBox(self)
        self.dec_len_size_combo.addItems(["1", "2", "4"])
        self.dec_len_size_combo.setCurrentText("2")
        self.dec_len_size_combo.currentIndexChanged.connect(self.update_config_preview)
        dec_len_layout.addWidget(self.dec_len_size_combo)

        dec_len_layout.addWidget(QLabel("Endian:", self))
        self.dec_len_endian_combo = QComboBox(self)
        self.dec_len_endian_combo.addItems(["big", "little"])
        self.dec_len_endian_combo.setCurrentText("big")
        self.dec_len_endian_combo.currentIndexChanged.connect(self.update_config_preview)
        dec_len_layout.addWidget(self.dec_len_endian_combo)

        self.dec_len_inc_hdr_cb = QCheckBox("Includes Header", self)
        self.dec_len_inc_hdr_cb.setChecked(False)
        self.dec_len_inc_hdr_cb.toggled.connect(self.update_config_preview)
        dec_len_layout.addWidget(self.dec_len_inc_hdr_cb)
        self.decoder_param_stack.addWidget(dec_len_widget)

        split_config_layout.addWidget(right_widget, 1)
        conn_layout.addLayout(split_config_layout)

        # Common Row (Log File - opt-in, off by default so a first run doesn't
        # silently write a JSONL file the user didn't ask for)
        common_layout = QHBoxLayout()
        self.log_file_cb = QCheckBox("Record to JSONL:", self)
        self.log_file_cb.setChecked(False)
        self.log_file_cb.toggled.connect(self._on_log_file_toggled)
        self.log_file_cb.toggled.connect(self.update_config_preview)
        common_layout.addWidget(self.log_file_cb)
        self.log_file_edit = QLineEdit("capture.jsonl", self)
        self.log_file_edit.setEnabled(False)
        self.log_file_edit.textChanged.connect(self.update_config_preview)
        common_layout.addWidget(self.log_file_edit)
        self.browse_log_btn = QPushButton("Browse", self)
        self.browse_log_btn.setEnabled(False)
        self.browse_log_btn.clicked.connect(self.browse_log_path)
        common_layout.addWidget(self.browse_log_btn)
        conn_layout.addLayout(common_layout)

        # Advanced/developer-facing fields (engine executable path, IPC socket path,
        # generated config preview) live in a separate Settings dialog rather than
        # always-on-screen - see open_settings_dialog(). The widgets themselves stay
        # attributes of MainWindow so the rest of the class can keep using them
        # unchanged; only where they're placed in the layout changes.
        self.cli_path_edit = QLineEdit(self)
        self.browse_cli_btn = QPushButton("Browse", self)
        self.browse_cli_btn.clicked.connect(self.browse_cli_path)
        self.socket_path_edit = QLineEdit(self.initial_socket_path, self)
        self.connect_btn = QPushButton("Attach", self)
        self.connect_btn.setToolTip("Attach to an already-running 'packet-probe engine' at this socket path.")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.config_preview_edit = QLineEdit(self)
        self.config_preview_edit.setReadOnly(True)
        self._build_settings_dialog()

        top_control_layout.addWidget(self.conn_group)

        main_layout.addWidget(top_control_widget)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        open_action = file_menu.addAction("&Open Log...")
        open_action.triggered.connect(self.open_log_file)

        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)

        # Filter Bar (direction / event type / text search over the live event table)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:", self))
        self.filter_direction_combo = QComboBox(self)
        self.filter_direction_combo.addItem("All Directions", "all")
        self.filter_direction_combo.addItem("App -> Device", "app_to_device")
        self.filter_direction_combo.addItem("Device -> App", "device_to_app")
        self.filter_direction_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_direction_combo)

        self.filter_type_combo = QComboBox(self)
        self.filter_type_combo.addItem("All Types", "all")
        for event_type in ("raw_bytes", "frame", "latency", "error", "state_change"):
            self.filter_type_combo.addItem(event_type, event_type)
        self.filter_type_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_type_combo)

        self.filter_text_edit = QLineEdit(self)
        self.filter_text_edit.setPlaceholderText("Search summary/hex...")
        self.filter_text_edit.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_text_edit)
        main_layout.addLayout(filter_layout)

        # Main Splitter
        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        main_layout.addWidget(main_splitter)

        self.table_model = PacketTableModel(self)
        self.filter_proxy = PacketFilterProxyModel(self)
        self.filter_proxy.setSourceModel(self.table_model)
        self.table_view = QTableView(self)
        self.table_view.setModel(self.filter_proxy)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        main_splitter.addWidget(self.table_view)

        # Send Panel
        self.send_group = QGroupBox("Send Message (to Target Device)", self)
        self.send_group.setEnabled(False)
        send_layout = QHBoxLayout(self.send_group)

        send_layout.addWidget(QLabel("Format:", self))
        self.text_radio = QRadioButton("Text", self)
        self.text_radio.setChecked(True)
        self.text_radio.toggled.connect(self.on_send_format_changed)
        send_layout.addWidget(self.text_radio)

        self.hex_radio = QRadioButton("Hex", self)
        send_layout.addWidget(self.hex_radio)

        send_layout.addWidget(QLabel("Data:", self))
        self.send_input = QLineEdit(self)
        self.send_input.setPlaceholderText("Type message to send...")
        self.send_input.returnPressed.connect(self.send_data)
        send_layout.addWidget(self.send_input)

        send_layout.addWidget(QLabel("EOL:", self))
        self.eol_combo = QComboBox(self)
        self.eol_combo.addItems(["None", "LF (\\n)", "CR (\\r)", "CRLF (\\r\\n)"])
        self.eol_combo.setCurrentIndex(0)
        send_layout.addWidget(self.eol_combo)

        self.send_btn = QPushButton("Send", self)
        self.send_btn.setObjectName("send_btn")
        self.send_btn.clicked.connect(self.send_data)
        send_layout.addWidget(self.send_btn)

        self.send_feedback_label = QLabel(self)
        send_layout.addWidget(self.send_feedback_label)

        # Bottom Detail Tabs
        self.detail_tabs = QTabWidget(self)

        self.hex_view = HexView(self)

        self.text_view = QPlainTextEdit(self)
        self.text_view.setReadOnly(True)
        text_font = QFont("Courier New", 10)
        text_font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_view.setFont(text_font)
        self.text_view.setPlaceholderText("Text View")

        self.detail_view = EventDetailView(self)
        self.process_output = QPlainTextEdit(self)
        self.process_output.setReadOnly(True)

        self.detail_tabs.addTab(self.hex_view, "Hex")
        self.detail_tabs.addTab(self.text_view, "Text")
        self.detail_tabs.addTab(self.detail_view, "JSON")
        self.detail_tabs.addTab(self.process_output, "Process Log")

        main_splitter.addWidget(self.send_group)
        main_splitter.addWidget(self.detail_tabs)

        main_splitter.setSizes([450, 75, 275])

        self.message_label = QLabel("", self)
        main_layout.addWidget(self.message_label)

        # Status Bar: consolidates the connection/capture/mode/port/counter indicators
        # that used to be four separate QLabels crowding the action button row.
        status_bar = self.statusBar()
        self.status_label = QLabel(self)
        status_bar.addWidget(self.status_label)
        self.state_label = QLabel(self)
        status_bar.addWidget(self.state_label)
        self.conn_mode_label = QLabel(self)
        status_bar.addWidget(self.conn_mode_label)
        self.port_label = QLabel(self)
        status_bar.addWidget(self.port_label)
        self.event_count_label = QLabel("Events: 0", self)
        status_bar.addPermanentWidget(self.event_count_label)
        self.error_count_label = QLabel("Errors: 0", self)
        status_bar.addPermanentWidget(self.error_count_label)

    # ── Connection management ──────────────────────────────────────────────

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

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")
        self.socket_path_edit.setEnabled(False)
        self._set_message("")

        self.worker = IpcClientWorker(socket_path, self)
        self.worker.status_changed.connect(self.on_status_changed)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.event_received.connect(self.on_event_received)
        self.worker.metadata_received.connect(self.on_metadata_received)
        self.worker.result_received.connect(self.on_result_received)
        self.worker.status_received.connect(self.on_status_received)
        self.worker.disconnected.connect(self.on_worker_finished)
        self.worker.unilink_unavailable.connect(self.on_unilink_unavailable)
        self.worker.start()

    def disconnect_socket(self):
        self._ipc_connected = False
        self._pending_commands.clear()
        if self._ipc_connector:
            self._ipc_connector.cancel()
            self._ipc_connector = None
        if self.worker:
            worker = self.worker
            self.worker = None
            worker.stop()

    def on_status_changed(self, status: str):
        if status == "connecting":
            self._ipc_connected = False
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText("Connecting...")
            self._set_message("")
            self.update_status("Status: connecting")
        elif status == "connected":
            self._ipc_connected = True
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Detach")
            self.socket_path_edit.setEnabled(False)
            self.clear_all()
            if self._starting_capture and self._pending_config_to_start is not None:
                # We connected as part of our own Start Capture request - chain
                # straight into configure/start_capture instead of settling on "live".
                config = self._pending_config_to_start
                self._pending_config_to_start = None
                self._set_message("Connected to engine, configuring...")
                self._configure_and_start(config)
            else:
                # A plain Attach (or a reconnect): sync UI with whatever the engine
                # is actually doing rather than assuming idle.
                self._set_message("Connected to engine")
                self._request_status_sync()
        elif status == "disconnected":
            self._ipc_connected = False
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Attach")
            self.socket_path_edit.setEnabled(True)
            self._pending_commands.clear()
            if not self.capture_process.is_running():
                self._engine_state = "idle"
                self._starting_capture = False
                self._set_capture_controls_running(False)
                self.set_mode("idle")
                self.update_status("Status: disconnected")

    def on_error_occurred(self, error_msg: str):
        self._set_message(f"Error: {error_msg}", is_error=True)
        self.update_status("Status: failed")
        self._bump_error_count()

    def _bump_error_count(self):
        self._error_count += 1
        self.error_count_label.setText(f"Errors: {self._error_count}")

    def on_unilink_unavailable(self, message: str):
        # Unlike a transient IPC error, this never resolves on its own: the CLI process
        # (if any) keeps running, but the live event table will stay empty for the rest
        # of this session. Make that permanent, non-retryable state hard to miss.
        # (The status badge itself will settle back to the neutral "disconnected" style a
        # moment later via the worker's own status_changed/disconnected signals - the
        # persistent signal here is the message banner, dialog, and state label below.)
        self._set_message(f"Error: {message}", is_error=True)
        self.set_mode("no live view")
        QMessageBox.critical(
            self,
            "Live View Unavailable",
            "unilink-python is not installed or failed to import, so the viewer cannot "
            "subscribe to the live IPC event stream:\n\n"
            f"{message}\n\n"
            "The CLI process (if running) is unaffected and will keep capturing/recording, "
            "but no events will appear in this table until unilink-python is installed and "
            "the viewer reconnects."
        )

    def on_metadata_received(self, metadata: dict):
        self._set_message(format_metadata_message(metadata))

    def on_event_received(self, event_dict: dict):
        event = PacketEvent(event_dict)
        self._event_count += 1
        self.event_count_label.setText(f"Events: {self._event_count}")
        if event.type == "error":
            self._bump_error_count()
        if self.is_paused:
            self.pending_events.append(event)
        else:
            self.table_model.append_event(event)
            self.table_view.scrollToBottom()

    def on_worker_finished(self):
        self.on_status_changed("disconnected")
        self.worker = None
        if not self.capture_process.is_running():
            self.set_mode("idle")

    # ── Status indicator helpers ───────────────────────────────────────────

    def _set_message(self, text: str, is_error: bool = False):
        self.message_label.setText(text)
        self.message_label.setStyleSheet("color: #fca5a5; font-weight: 600;" if is_error else "")

    def update_status(self, text: str):
        self.status_label.setText(text)
        lower_text = text.lower()
        # "disconnected" and "failed"/"error" must be checked before the generic
        # "connected"/"running" match below, since "disconnected" contains "connected"
        # as a substring and would otherwise get the same "success" styling.
        if "disconnected" in lower_text:
            self.status_label.setStyleSheet(
                "background-color: #1f2937; color: #9ca3af; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #374151;"
            )
        elif "failed" in lower_text or "error" in lower_text:
            self.status_label.setStyleSheet(
                "background-color: #991b1b; color: #fca5a5; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #dc2626;"
            )
        elif "connecting" in lower_text or "launching" in lower_text:
            self.status_label.setStyleSheet(
                "background-color: #78350f; color: #fbbf24; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #d97706;"
            )
        elif "offline" in lower_text:
            self.status_label.setStyleSheet(
                "background-color: #312e81; color: #a5b4fc; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #4f46e5;"
            )
        elif "connected" in lower_text or "running" in lower_text:
            self.status_label.setStyleSheet(
                "background-color: #064e3b; color: #34d399; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #059669;"
            )
        else:
            self.status_label.setStyleSheet(
                "background-color: #1f2937; color: #9ca3af; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #374151;"
            )

    def set_mode(self, mode: str):
        self.state_label.setText(f"State: {mode}")
        lower_mode = mode.lower()
        if lower_mode == "live":
            self.state_label.setStyleSheet(
                "background-color: #064e3b; color: #34d399; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #059669;"
            )
        elif lower_mode == "launcher":
            self.state_label.setStyleSheet(
                "background-color: #78350f; color: #fbbf24; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #d97706;"
            )
        elif lower_mode == "offline":
            self.state_label.setStyleSheet(
                "background-color: #312e81; color: #a5b4fc; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #4f46e5;"
            )
        elif lower_mode == "no live view":
            self.state_label.setStyleSheet(
                "background-color: #991b1b; color: #fca5a5; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #dc2626;"
            )
        else:  # "idle"
            self.state_label.setStyleSheet(
                "background-color: #1f2937; color: #9ca3af; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #374151;"
            )

    def update_port(self, port_str: str):
        self.port_label.setText(f"Port: {port_str}")
        if port_str == "-":
            self.port_label.setStyleSheet(
                "background-color: #111827; color: #6b7280; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #1f2937;"
            )
        else:
            self.port_label.setStyleSheet(
                "background-color: #0c4a6e; color: #38bdf8; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #0284c7;"
            )

    def update_conn_mode(self, mode: str):
        self.conn_mode_label.setText(f"Mode: {mode}")
        lower_mode = mode.lower()
        if lower_mode == "udp":
            self.conn_mode_label.setStyleSheet(
                "background-color: #134e5e; color: #e0f7fa; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #00acc1;"
            )
        elif lower_mode == "tcp client":
            self.conn_mode_label.setStyleSheet(
                "background-color: #1e3a8a; color: #dbeafe; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #3b82f6;"
            )
        elif lower_mode == "tcp server":
            self.conn_mode_label.setStyleSheet(
                "background-color: #312e81; color: #e0e7ff; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #6366f1;"
            )
        elif lower_mode == "tcp proxy":
            self.conn_mode_label.setStyleSheet(
                "background-color: #4c1d95; color: #f3e8ff; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #8b5cf6;"
            )
        elif lower_mode == "serial":
            self.conn_mode_label.setStyleSheet(
                "background-color: #7c2d12; color: #ffedd5; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #f97316;"
            )
        else:
            self.conn_mode_label.setStyleSheet(
                "background-color: #1f2937; color: #9ca3af; border-radius: 6px; padding: 4px 10px; font-weight: bold; border: 1px solid #374151;"
            )

    # ── Capture lifecycle ──────────────────────────────────────────────────

    # Capture modes where the CLI accepts no send input at all (no stdin loop,
    # no IPC command handler) - see run_tcp_proxy.cpp.
    _SEND_UNSUPPORTED_MODES = ("TCP Proxy",)

    def _refresh_send_group_enabled(self, active: bool):
        send_capable = active and self._active_capture_mode not in self._SEND_UNSUPPORTED_MODES
        self.send_group.setEnabled(send_capable)
        if active and not send_capable:
            self.send_group.setToolTip(
                f"{self._active_capture_mode} mode forwards traffic between an existing client and "
                "target; it does not support sending messages from the viewer."
            )
        elif not active:
            self.send_group.setToolTip("Start a capture session before sending.")
        else:
            self.send_group.setToolTip("")
        self.send_feedback_label.clear()

    def _show_send_feedback(self, ok: bool, error: str):
        if ok:
            self.send_feedback_label.setText("✓ Sent")
            self.send_feedback_label.setStyleSheet("color: #34d399;")
        else:
            self.send_feedback_label.setText(f"✗ {error or 'Send failed'}")
            self.send_feedback_label.setStyleSheet("color: #fca5a5;")
        QTimer.singleShot(4000, self.send_feedback_label.clear)

    def _set_capture_controls_running(self, running: bool):
        self.start_capture_btn.setEnabled(not running and not self._starting_capture)
        self.stop_capture_btn.setEnabled(running)
        self.conn_group.setEnabled(not running)
        self._refresh_send_group_enabled(running)

    def _restore_capture_controls(self):
        self._starting_capture = False
        self._set_capture_controls_running(False)

    # ── Engine control protocol v2 (configure/start_capture/stop_capture) ──

    def _configure_and_start(self, config: dict):
        cmd_id = self.worker.send_command({"type": "command", "command": "configure", "config": config})
        self._pending_commands[cmd_id] = "configure"

    def _request_status_sync(self):
        if self.worker is None:
            return
        cmd_id = self.worker.send_command({"type": "command", "command": "get_status"})
        self._pending_commands[cmd_id] = "get_status"

    def _apply_engine_state(self, engine_state: str):
        self._engine_state = engine_state
        capturing = engine_state == "capturing"
        self._set_capture_controls_running(capturing)
        self.set_mode("live" if capturing else "idle")
        self.update_status("Status: capturing" if capturing else "Status: connected")

    def on_result_received(self, result: dict):
        cmd_id = result.get("id", "")
        intent = self._pending_commands.pop(cmd_id, None)
        ok = bool(result.get("ok", False))
        error = result.get("error", "")

        if intent == "configure":
            if ok:
                self._set_message("Configured, starting capture...")
                start_id = self.worker.send_command({"type": "command", "command": "start_capture"})
                self._pending_commands[start_id] = "start_capture"
            else:
                self._restore_capture_controls()
                self._set_message(f"Error: configure failed: {error}", is_error=True)
                QMessageBox.warning(self, "Configure Failed", error or "Unknown error")
        elif intent == "start_capture":
            self._starting_capture = False
            if ok:
                self._apply_engine_state("capturing")
                self._set_message("Capture started")
            else:
                self._set_capture_controls_running(False)
                self._set_message(f"Error: start_capture failed: {error}", is_error=True)
                QMessageBox.warning(self, "Start Capture Failed", error or "Unknown error")
        elif intent == "stop_capture":
            self._apply_engine_state("idle" if ok else self._engine_state)
            if ok:
                self._set_message("Capture stopped")
            else:
                self._set_message(f"Error: stop_capture failed: {error}", is_error=True)
        elif intent == "get_status":
            if ok:
                self._apply_engine_state(result.get("engine_state", "idle"))
            self._set_message("" if ok else f"Error: get_status failed: {error}", is_error=not ok)
        elif intent == "send":
            self._set_message("Sent" if ok else f"Error: send failed: {error}", is_error=not ok)
            self._show_send_feedback(ok, error)
        elif intent == "list_serial_ports":
            self.ser_port_refresh_btn.setEnabled(True)
            if ok:
                current = self.ser_port.currentText()
                ports = result.get("ports", [])
                self.ser_port.clear()
                self.ser_port.addItems(ports)
                if current:
                    self.ser_port.setCurrentText(current)
                self._set_message(f"Found {len(ports)} serial port(s)" if ports else "No serial ports found")
            else:
                self._set_message(f"Error: list_serial_ports failed: {error}", is_error=True)

    def refresh_serial_ports(self):
        if not (self._ipc_connected and self.worker is not None):
            QMessageBox.warning(
                self, "Warning", "Not connected to an engine yet - click Start Capture or Attach first."
            )
            return
        self.ser_port_refresh_btn.setEnabled(False)
        cmd_id = self.worker.send_command({"type": "command", "command": "list_serial_ports"})
        self._pending_commands[cmd_id] = "list_serial_ports"

    def on_status_received(self, status: dict):
        # Broadcast to all clients on every engine state change (see docs/ipc-protocol.md).
        # Ignore it while we have our own configure/start_capture in flight so we don't
        # show a stale state in between our own request and its result.
        if self._starting_capture:
            return
        self._apply_engine_state(status.get("engine_state", self._engine_state))

    # ── Capture lifecycle ────────────────────────────────────────────────

    def start_capture(self):
        try:
            config = self._collect_capture_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Warning", str(exc))
            return

        self._active_capture_mode = self.mode_combo.currentText()
        self._starting_capture = True
        self._set_capture_controls_running(False)
        self.set_mode("launcher")
        self.update_status("Status: launching")

        if self._ipc_connected and self.worker is not None:
            self._configure_and_start(config)
            return

        self._pending_config_to_start = config

        if self.capture_process.is_running():
            # Engine process is already up but we're not connected - just (re)connect;
            # on_status_changed("connected") will pick up _pending_config_to_start.
            self.connect_socket()
            return

        executable = self.cli_path_edit.text().strip()
        if not executable:
            QMessageBox.warning(self, "Warning", "CLI Path is empty.")
            self._restore_capture_controls()
            return

        resolved_path = shutil.which(executable)
        if not resolved_path:
            QMessageBox.warning(self, "Warning", f"CLI executable not found or not executable:\n{executable}")
            self._restore_capture_controls()
            return

        self.generated_ipc_path = make_default_ipc_path()
        self.socket_path_edit.setText(self.generated_ipc_path)

        self.clear_all()
        self.process_output.clear()

        # Remove stale socket before launch
        try:
            Path(self.generated_ipc_path).unlink(missing_ok=True)
        except Exception:
            pass

        self.process_output.appendPlainText(f"[system] Starting engine: {executable} engine --ipc {self.generated_ipc_path}")

        try:
            self.capture_process.start(executable, ["engine", "--ipc", self.generated_ipc_path])
        except Exception as exc:
            self.process_output.appendPlainText(f"[system] Failed to start process: {exc}")
            self.on_capture_stopped(-1, "FailedToStart")

    def stop_capture(self):
        if self._ipc_connected and self.worker is not None:
            self.stop_capture_btn.setEnabled(False)
            cmd_id = self.worker.send_command({"type": "command", "command": "stop_capture"})
            self._pending_commands[cmd_id] = "stop_capture"
            return

        # No IPC connection to send stop_capture over (e.g. the engine hung before
        # ever accepting a connection) - fall back to killing the process outright.
        if self._ipc_connector:
            self._ipc_connector.cancel()
            self._ipc_connector = None
        self.process_output.appendPlainText("[system] Stopping engine process...")
        self.capture_process.stop()
        self._restore_capture_controls()

    def on_capture_started(self):
        self.process_output.appendPlainText("[system] Engine process started successfully.")
        self._ipc_connector = IpcConnector(
            self.generated_ipc_path,
            max_attempts=30,
            interval_ms=100,
            parent=self,
        )
        self._ipc_connector.ready.connect(self._on_ipc_socket_ready)
        self._ipc_connector.failed.connect(self._on_ipc_socket_failed)
        self._ipc_connector.start()

    def _on_ipc_socket_ready(self):
        self._ipc_connector = None
        self.connect_socket()

    def _on_ipc_socket_failed(self, reason: str):
        self._ipc_connector = None
        self._pending_config_to_start = None
        self._set_message(f"Error: {reason}", is_error=True)
        self.stop_capture()
        self._restore_capture_controls()
        self.set_mode("idle")
        self.update_status("Status: failed")

    def on_capture_stopped(self, exit_code, exit_status):
        if self._ipc_connector:
            self._ipc_connector.cancel()
            self._ipc_connector = None
        self._pending_config_to_start = None
        self.process_output.appendPlainText(f"[system] Engine process stopped. Exit code: {exit_code} ({exit_status})")
        self._restore_capture_controls()
        self.disconnect_socket()
        self.set_mode("idle")
        self.update_status("Status: disconnected")

    def on_capture_error(self, msg):
        self.process_output.appendPlainText(f"[stderr] Process error: {msg}")
        if not self.capture_process.is_running():
            if self._ipc_connector:
                self._ipc_connector.cancel()
                self._ipc_connector = None
            self._pending_config_to_start = None
            self._restore_capture_controls()
            self.disconnect_socket()
            self.set_mode("idle")
            self.update_status("Status: disconnected")

    def on_capture_stdout(self, data):
        text = data.rstrip()
        if text:
            self.process_output.appendPlainText(f"[stdout] {text}")

    def on_capture_stderr(self, data):
        text = data.rstrip()
        if text:
            self.process_output.appendPlainText(f"[stderr] {text}")

    # ── UI actions ────────────────────────────────────────────────────────

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
        self.text_view.clear()
        self.detail_view.clear()
        self._event_count = 0
        self._error_count = 0
        self.event_count_label.setText("Events: 0")
        self.error_count_label.setText("Errors: 0")

    def _on_filter_changed(self):
        self.filter_proxy.set_direction_filter(self.filter_direction_combo.currentData())
        self.filter_proxy.set_type_filter(self.filter_type_combo.currentData())
        self.filter_proxy.set_text_filter(self.filter_text_edit.text())

    def on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        indexes = selected.indexes()
        if not indexes:
            self.hex_view.clear()
            self.text_view.clear()
            self.detail_view.clear()
            return

        source_index = self.filter_proxy.mapToSource(indexes[0])
        event = self.table_model.event_at(source_index.row())
        if event:
            self.hex_view.set_payload_hex(event.payload_hex)
            self.detail_view.set_event(event)

            if event.payload_hex:
                clean_hex = re.sub(r'[\s:\-]', '', event.payload_hex)
                try:
                    raw_bytes = bytes.fromhex(clean_hex)
                    chars = []
                    for b in raw_bytes:
                        if 32 <= b <= 126 or b == 10 or b == 13 or b == 9:
                            chars.append(chr(b))
                        else:
                            chars.append(".")
                    self.text_view.setPlainText("".join(chars))
                except Exception as e:
                    self.text_view.setPlainText(f"Failed to decode text: {e}")
            else:
                self.text_view.clear()

    def browse_cli_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select packet-probe CLI executable",
            "",
            "Executables (*.exe *packet-probe*);;All Files (*)"
        )
        if path:
            self.cli_path_edit.setText(path)

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
            self._set_message(f"Error loading log: {exc}", is_error=True)
            return

        events = [PacketEvent(e) for e in result.events]
        self.table_model.set_events(events)

        self.set_mode("offline")
        self.update_status("Status: offline log")

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
            self._set_message(f"{meta_msg}\n{msg}")
        else:
            self._set_message(msg)

    def on_send_format_changed(self):
        is_hex = self.hex_radio.isChecked()
        self.eol_combo.setEnabled(not is_hex)
        if is_hex:
            self.send_input.setPlaceholderText("Enter hex bytes (e.g. AA BB CC 00)...")
        else:
            self.send_input.setPlaceholderText("Type message to send...")

    def _clean_hex_input(self, text: str) -> str | None:
        clean_hex = re.sub(r'(0x|0X|[\s:\-])', '', text).lower()
        if not clean_hex or not all(c in '0123456789abcdefABCDEF' for c in clean_hex) or len(clean_hex) % 2 != 0:
            QMessageBox.warning(
                self,
                "Invalid Hex",
                "Please enter a valid hex string (e.g. AA BB CC or AABBCC).\n"
                "Note: Each byte must have two hex digits."
            )
            return None
        return clean_hex

    def send_data(self):
        if not (self._ipc_connected and self.worker is not None):
            QMessageBox.warning(self, "Warning", "Cannot send data: not connected to the engine.")
            return
        if self._engine_state != "capturing":
            QMessageBox.warning(self, "Warning", "Cannot send data: capture is not running.")
            return

        text = self.send_input.text().strip()
        if not text:
            return

        if self.hex_radio.isChecked():
            clean_hex = self._clean_hex_input(text)
            if clean_hex is None:
                return
            payload_hex = clean_hex
        else:
            eol_idx = self.eol_combo.currentIndex()
            raw = text
            if eol_idx == 1:
                raw += "\n"
            elif eol_idx == 2:
                raw += "\r"
            elif eol_idx == 3:
                raw += "\r\n"
            try:
                payload_hex = raw.encode("utf-8").hex()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"Failed to encode text: {exc}")
                return

        cmd_id = self.worker.send_command({"type": "command", "command": "send", "payload_hex": payload_hex})
        self._pending_commands[cmd_id] = "send"
        self.send_input.clear()

    # ── Settings ──────────────────────────────────────────────────────────

    def load_settings(self):
        defaults = ViewerState(
            cli_path=find_packet_probe_binary(),
            socket_path=self.initial_socket_path,
        )
        state = self._settings_manager.load(defaults)

        self.cli_path_edit.setText(state.cli_path)
        self.socket_path_edit.setText(state.socket_path)
        if state.send_in_hex:
            self.hex_radio.setChecked(True)
        else:
            self.text_radio.setChecked(True)
        self.eol_combo.setCurrentIndex(state.eol_index)

        self.mode_combo.setCurrentIndex(state.mode_index)
        self.udp_bind_host.setText(state.udp_bind_host)
        self.udp_bind_port.setText(state.udp_bind_port)
        self.udp_target_host.setText(state.udp_target_host)
        self.udp_target_port.setText(state.udp_target_port)
        self.tcp_cli_host.setText(state.tcp_cli_host)
        self.tcp_cli_port.setText(state.tcp_cli_port)
        self.tcp_srv_host.setText(state.tcp_srv_host)
        self.tcp_srv_port.setText(state.tcp_srv_port)
        self.tcp_prx_listen_host.setText(state.tcp_prx_listen_host)
        self.tcp_prx_listen_port.setText(state.tcp_prx_listen_port)
        self.tcp_prx_target_host.setText(state.tcp_prx_target_host)
        self.tcp_prx_target_port.setText(state.tcp_prx_target_port)
        self.ser_port.setCurrentText(state.ser_port)
        self.ser_baud.setCurrentText(state.ser_baud)

        self.decoder_combo.setCurrentIndex(state.decoder_index)
        self.decoder_param_stack.setCurrentIndex(state.decoder_index)
        self.dec_fixed_size.setValue(state.dec_fixed_size)
        self.dec_delim_edit.setText(state.dec_delim)
        self.dec_delim_inc_cb.setChecked(state.dec_delim_inc)
        self.dec_len_size_combo.setCurrentText(state.dec_len_size)
        self.dec_len_endian_combo.setCurrentText(state.dec_len_endian)
        self.dec_len_inc_hdr_cb.setChecked(state.dec_len_inc_hdr)
        self.log_file_edit.setText(state.log_file)
        self.log_file_cb.setChecked(state.log_enabled)

        # setCurrentIndex() above only fires on_mode_changed (and its help-text update)
        # if the index actually changed - call it explicitly so a saved/default mode of
        # 0 (UDP) still gets its help text populated.
        self.mode_help_label.setText(self._MODE_HELP_TEXT.get(self.mode_combo.currentText(), ""))

        self.update_config_preview()

    def save_settings(self):
        state = ViewerState(
            cli_path=self.cli_path_edit.text().strip(),
            socket_path=self.socket_path_edit.text().strip(),
            send_in_hex=self.hex_radio.isChecked(),
            eol_index=self.eol_combo.currentIndex(),
            mode_index=self.mode_combo.currentIndex(),
            udp_bind_host=self.udp_bind_host.text().strip(),
            udp_bind_port=self.udp_bind_port.text().strip(),
            udp_target_host=self.udp_target_host.text().strip(),
            udp_target_port=self.udp_target_port.text().strip(),
            tcp_cli_host=self.tcp_cli_host.text().strip(),
            tcp_cli_port=self.tcp_cli_port.text().strip(),
            tcp_srv_host=self.tcp_srv_host.text().strip(),
            tcp_srv_port=self.tcp_srv_port.text().strip(),
            tcp_prx_listen_host=self.tcp_prx_listen_host.text().strip(),
            tcp_prx_listen_port=self.tcp_prx_listen_port.text().strip(),
            tcp_prx_target_host=self.tcp_prx_target_host.text().strip(),
            tcp_prx_target_port=self.tcp_prx_target_port.text().strip(),
            ser_port=self.ser_port.currentText().strip(),
            ser_baud=self.ser_baud.currentText().strip(),
            decoder_index=self.decoder_combo.currentIndex(),
            dec_fixed_size=self.dec_fixed_size.value(),
            dec_delim=self.dec_delim_edit.text().strip(),
            dec_delim_inc=self.dec_delim_inc_cb.isChecked(),
            dec_len_size=self.dec_len_size_combo.currentText(),
            dec_len_endian=self.dec_len_endian_combo.currentText(),
            dec_len_inc_hdr=self.dec_len_inc_hdr_cb.isChecked(),
            log_file=self.log_file_edit.text().strip(),
            log_enabled=self.log_file_cb.isChecked(),
        )
        self._settings_manager.save(state)

    # ── Mode / decoder combo handlers ────────────────────────────────────

    _MODE_HELP_TEXT = {
        "UDP": "Binds a local UDP socket and inspects datagrams to/from an optional target.",
        "TCP Client": "Connects directly to a TCP server device and inspects the traffic.",
        "TCP Server": "Listens for one incoming TCP client connection and inspects the traffic.",
        "TCP Proxy": "Sits between an existing client and a target device, forwarding traffic both ways (no Send).",
        "Serial": "Connects directly to a serial (COM/tty) target device.",
    }

    def on_mode_changed(self, index: int):
        self.param_stack.setCurrentIndex(index)
        mode = self.mode_combo.currentText()
        self.update_conn_mode(mode)
        self.mode_help_label.setText(self._MODE_HELP_TEXT.get(mode, ""))
        if mode == "UDP":
            self.log_file_edit.setText("udp.jsonl")
        elif mode == "TCP Client":
            self.log_file_edit.setText("tcp_client.jsonl")
        elif mode == "TCP Server":
            self.log_file_edit.setText("tcp_server.jsonl")
        elif mode == "TCP Proxy":
            self.log_file_edit.setText("tcp_proxy.jsonl")
        elif mode == "Serial":
            self.log_file_edit.setText("serial.jsonl")
        self.update_config_preview()

    def _collect_capture_config(self) -> dict:
        """Builds the "config" object for a "configure" command from the current
        form values. Raises ValueError (with a user-facing message) on invalid
        input, e.g. a non-numeric port."""
        mode = self.mode_combo.currentText()

        if mode == "UDP":
            fields = {
                "bind_host": self.udp_bind_host.text(),
                "bind_port": self.udp_bind_port.text(),
                "target_host": self.udp_target_host.text(),
                "target_port": self.udp_target_port.text(),
            }
        elif mode == "TCP Client":
            fields = {"host": self.tcp_cli_host.text(), "port": self.tcp_cli_port.text()}
        elif mode == "TCP Server":
            fields = {"listen_host": self.tcp_srv_host.text(), "listen_port": self.tcp_srv_port.text()}
        elif mode == "TCP Proxy":
            fields = {
                "listen_host": self.tcp_prx_listen_host.text(),
                "listen_port": self.tcp_prx_listen_port.text(),
                "target_host": self.tcp_prx_target_host.text(),
                "target_port": self.tcp_prx_target_port.text(),
            }
        elif mode == "Serial":
            fields = {"serial_port": self.ser_port.currentText(), "baudrate": self.ser_baud.currentText()}
        else:
            fields = {}

        decoder_kind = self.decoder_combo.currentText()
        decoder = build_decoder_config(
            decoder_kind,
            frame_size=self.dec_fixed_size.value(),
            delimiter_hex=self.dec_delim_edit.text().strip(),
            include_delimiter=self.dec_delim_inc_cb.isChecked(),
            length_size=int(self.dec_len_size_combo.currentText()),
            length_endian=self.dec_len_endian_combo.currentText(),
            length_includes_header=self.dec_len_inc_hdr_cb.isChecked(),
        )

        common = {
            "log_path": self.log_file_edit.text().strip() if self.log_file_cb.isChecked() else "",
            "hex_raw": False,
            "hex_frame": False,
            "latency": True,
        }

        return build_capture_config(mode, fields, decoder, common)

    def update_config_preview(self):
        mode = self.mode_combo.currentText()

        try:
            config = self._collect_capture_config()
        except ValueError as exc:
            self.config_preview_edit.setText(f"(invalid: {exc})")
        else:
            self.config_preview_edit.setText(json.dumps(config))

        # Update Port label
        active_port = "-"
        if mode == "UDP":
            bind_p = self.udp_bind_port.text().strip()
            target_p = self.udp_target_port.text().strip()
            active_port = f"Bind {bind_p}" if bind_p else "-"
            if target_p:
                active_port += f" (Target {target_p})"
        elif mode == "TCP Client":
            active_port = self.tcp_cli_port.text().strip()
        elif mode == "TCP Server":
            active_port = self.tcp_srv_port.text().strip()
        elif mode == "TCP Proxy":
            lp = self.tcp_prx_listen_port.text().strip()
            tp = self.tcp_prx_target_port.text().strip()
            active_port = f"Proxy {lp} -> {tp}"
        elif mode == "Serial":
            active_port = self.ser_port.currentText().strip()

        self.update_port(active_port or "-")

    def on_decoder_changed(self, index: int):
        self.decoder_param_stack.setCurrentIndex(index)
        self.update_config_preview()

    def _build_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumWidth(480)
        layout = QVBoxLayout(dialog)

        paths_layout = QHBoxLayout()
        paths_layout.addWidget(QLabel("CLI Path:", dialog))
        paths_layout.addWidget(self.cli_path_edit)
        paths_layout.addWidget(self.browse_cli_btn)
        layout.addLayout(paths_layout)

        socket_layout = QHBoxLayout()
        socket_layout.addWidget(QLabel("Socket Path:", dialog))
        socket_layout.addWidget(self.socket_path_edit)
        socket_layout.addWidget(self.connect_btn)
        layout.addLayout(socket_layout)

        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("Config Preview:", dialog))
        preview_layout.addWidget(self.config_preview_edit)
        layout.addLayout(preview_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        buttons.rejected.connect(dialog.close)
        buttons.accepted.connect(dialog.close)
        layout.addWidget(buttons)

        self.settings_dialog = dialog

    def open_settings_dialog(self):
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _on_log_file_toggled(self, checked: bool):
        self.log_file_edit.setEnabled(checked)
        self.browse_log_btn.setEnabled(checked)

    def browse_log_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Choose JSONL Log File", self.log_file_edit.text(), "JSONL Files (*.jsonl);;All Files (*)"
        )
        if path:
            self.log_file_edit.setText(path)

    def closeEvent(self, event):
        self.save_settings()
        self.disconnect_socket()
        # stop_capture() alone would only send a stop_capture IPC command, leaving an
        # engine process we spawned running in the background forever. Only kill the
        # process if we're the one who spawned it - an Attach-only session must leave
        # someone else's engine process alone.
        if self.capture_process.is_running():
            self.capture_process.stop()
        event.accept()
