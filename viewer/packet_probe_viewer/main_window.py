import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QTableView, QSplitter, QHeaderView, QMessageBox, QFileDialog,
    QPlainTextEdit, QGroupBox, QTabWidget, QComboBox, QRadioButton, QStackedWidget,
    QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QItemSelection, QModelIndex, QTimer, QSettings
from PySide6.QtGui import QFont
from .ipc_client import IpcClientWorker
from .event_model import PacketEvent
from .packet_table_model import PacketTableModel
from .widgets.hex_view import HexView
from .widgets.event_detail import EventDetailView
from .jsonl_log_loader import load_packet_probe_jsonl
from .ipc_path import make_default_ipc_path, resolve_initial_socket_path
from .capture_process import CaptureProcess

def find_packet_probe_binary() -> str:
    # 1. Check environment variable
    env_path = os.environ.get("PACKET_PROBE_CLI")
    if env_path:
        return env_path
    
    # 2. Check workspace build directory relative to this file
    try:
        current_dir = Path(__file__).resolve().parent
        # Go up to workspace root (viewer/packet_probe_viewer/.. -> packet-probe/)
        workspace_root = current_dir.parents[1]
        
        # Look in build/
        build_bin = workspace_root / "build" / "packet-probe"
        if build_bin.exists() and os.access(build_bin, os.X_OK):
            return str(build_bin)
            
        # Also look in build/apps/packet-probe-cli/packet-probe
        build_bin_alt = workspace_root / "build" / "apps" / "packet-probe-cli" / "packet-probe"
        if build_bin_alt.exists() and os.access(build_bin_alt, os.X_OK):
            return str(build_bin_alt)
    except Exception:
        pass
        
    return "packet-probe"

DARK_THEME_QSS = """
/* General background and text */
QMainWindow {
    background-color: #1a1a24;
}
QWidget {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    color: #e2e8f0;
}
QLabel {
    color: #cbd5e0;
    font-weight: 500;
}

/* Group Boxes */
QGroupBox {
    border: 1px solid #2d3748;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    color: #319795; /* Teal header */
    padding-top: 15px;
    background-color: #23232f;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
}

/* Text LineEdits & SpinBoxes */
QLineEdit, QComboBox, QSpinBox {
    background-color: #1e1e26;
    border: 1px solid #4a5568;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f7fafc;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #319795;
    background-color: #171720;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background-color: #2d3748;
    color: #718096;
    border: 1px solid #2d3748;
}

/* Combo Box Dropdown items */
QComboBox QAbstractItemView {
    background-color: #1a1a24;
    border: 1px solid #4a5568;
    selection-background-color: #319795;
    selection-color: #ffffff;
    color: #cbd5e0;
}

/* Buttons */
QPushButton {
    background-color: #2d3748;
    border: 1px solid #4a5568;
    border-radius: 6px;
    padding: 6px 14px;
    color: #e2e8f0;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #4a5568;
    border: 1px solid #718096;
}
QPushButton:pressed {
    background-color: #1a202c;
}
QPushButton:disabled {
    background-color: #1a1a24;
    color: #718096;
    border: 1px solid #2d3748;
}

/* Accent Buttons (Primary actions like Start Capture, Send) */
QPushButton#start_capture_btn, QPushButton#send_btn {
    background-color: #319795;
    border: 1px solid #2b6cb0;
    color: #ffffff;
}
QPushButton#start_capture_btn:hover, QPushButton#send_btn:hover {
    background-color: #4db6ac;
}
QPushButton#start_capture_btn:pressed, QPushButton#send_btn:pressed {
    background-color: #00796b;
}

QPushButton#stop_capture_btn {
    background-color: #c53030;
    border: 1px solid #9b2c2c;
    color: #ffffff;
}
QPushButton#stop_capture_btn:hover {
    background-color: #e53e3e;
}
QPushButton#stop_capture_btn:pressed {
    background-color: #9b2c2c;
}

/* Tables */
QTableView {
    background-color: #15151e;
    border: 1px solid #2d3748;
    gridline-color: #2d3748;
    border-radius: 6px;
    color: #e2e8f0;
}
QTableView::item:selected {
    background-color: #2c3e50;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #23232f;
    color: #cbd5e0;
    padding: 6px;
    border: 1px solid #2d3748;
    font-weight: bold;
}

/* Tab Widgets */
QTabWidget::pane {
    border: 1px solid #2d3748;
    background-color: #1e1e26;
    border-radius: 6px;
    position: absolute;
    top: -1px;
}
QTabBar::tab {
    background-color: #2d3748;
    color: #a0aec0;
    border: 1px solid #2d3748;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1e1e26;
    color: #319795;
    font-weight: bold;
    border: 1px solid #2d3748;
    border-bottom: 1px solid #1e1e26;
}
QTabBar::tab:hover:!selected {
    background-color: #4a5568;
    color: #e2e8f0;
}

/* PlainTextEdit for Logs */
QPlainTextEdit {
    background-color: #15151e;
    border: 1px solid #2d3748;
    border-radius: 6px;
    color: #e2e8f0;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #1a1a24;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #4a5568;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #718096;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #1a1a24;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #4a5568;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #718096;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Radio Buttons */
QRadioButton {
    color: #cbd5e0;
    font-weight: 500;
    spacing: 6px;
}
QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 8px;
    border: 1px solid #4a5568;
    background-color: #1e1e26;
}
QRadioButton::indicator:checked {
    background-color: #319795;
    border: 1px solid #319795;
}
QRadioButton::indicator:hover {
    border: 1px solid #319795;
}

/* Splitters */
QSplitter::handle {
    background-color: #2d3748;
}
QSplitter::handle:horizontal {
    width: 4px;
}
QSplitter::handle:vertical {
    height: 4px;
}

/* Menu Bar and Menus */
QMenuBar {
    background-color: #1a1a24;
    border-bottom: 1px solid #2d3748;
}
QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
    color: #cbd5e0;
}
QMenuBar::item:selected {
    background-color: #2d3748;
    border-radius: 4px;
    color: #ffffff;
}
QMenu {
    background-color: #1e1e26;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
    color: #cbd5e0;
}
QMenu::item:selected {
    background-color: #319795;
    color: #ffffff;
}

/* Checkboxes */
QCheckBox {
    color: #cbd5e0;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #4a5568;
    background-color: #1e1e26;
}
QCheckBox::indicator:checked {
    background-color: #319795;
    border: 1px solid #319795;
}
QCheckBox::indicator:hover {
    border: 1px solid #319795;
}

/* Checked PushButtons (e.g. settings toggle active) */
QPushButton:checked {
    background-color: #319795;
    color: #ffffff;
    border: 1px solid #2b6cb0;
}
"""

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
        self.settings = QSettings(settings_org, settings_app)
        self.load_settings()
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

        # Row 1: CLI Path & Socket Path & Settings Toggle (Compact 1 Row)
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("CLI Path:", self))
        self.cli_path_edit = QLineEdit(self)
        header_layout.addWidget(self.cli_path_edit)
        self.browse_cli_btn = QPushButton("Browse", self)
        self.browse_cli_btn.clicked.connect(self.browse_cli_path)
        header_layout.addWidget(self.browse_cli_btn)

        header_layout.addWidget(QLabel("Socket Path:", self))
        self.socket_path_edit = QLineEdit(self.initial_socket_path, self)
        header_layout.addWidget(self.socket_path_edit)
        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.clicked.connect(self.toggle_connection)
        header_layout.addWidget(self.connect_btn)

        self.toggle_settings_btn = QPushButton("⚙️ Settings", self)
        self.toggle_settings_btn.setCheckable(True)
        self.toggle_settings_btn.setChecked(True)
        self.toggle_settings_btn.clicked.connect(self.toggle_settings_visibility)
        header_layout.addWidget(self.toggle_settings_btn)
        top_control_layout.addLayout(header_layout)

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

        # Parameter Stacked Widget
        self.param_stack = QStackedWidget(self)
        left_layout.addWidget(self.param_stack)

        # 1. UDP Panel
        udp_widget = QWidget(self)
        udp_layout = QHBoxLayout(udp_widget)
        udp_layout.setContentsMargins(0, 5, 0, 5)
        udp_layout.addWidget(QLabel("Bind Host:", self))
        self.udp_bind_host = QLineEdit("0.0.0.0", self)
        self.udp_bind_host.textChanged.connect(self.update_generated_args)
        udp_layout.addWidget(self.udp_bind_host)
        udp_layout.addWidget(QLabel("Bind Port:", self))
        self.udp_bind_port = QLineEdit("19000", self)
        self.udp_bind_port.textChanged.connect(self.update_generated_args)
        udp_layout.addWidget(self.udp_bind_port)
        udp_layout.addWidget(QLabel("Target Host:", self))
        self.udp_target_host = QLineEdit("127.0.0.1", self)
        self.udp_target_host.textChanged.connect(self.update_generated_args)
        udp_layout.addWidget(self.udp_target_host)
        udp_layout.addWidget(QLabel("Target Port:", self))
        self.udp_target_port = QLineEdit("19085", self)
        self.udp_target_port.textChanged.connect(self.update_generated_args)
        udp_layout.addWidget(self.udp_target_port)
        self.param_stack.addWidget(udp_widget)

        # 2. TCP Client Panel
        tcp_client_widget = QWidget(self)
        tcp_client_layout = QHBoxLayout(tcp_client_widget)
        tcp_client_layout.setContentsMargins(0, 5, 0, 5)
        tcp_client_layout.addWidget(QLabel("Remote Host:", self))
        self.tcp_cli_host = QLineEdit("127.0.0.1", self)
        self.tcp_cli_host.textChanged.connect(self.update_generated_args)
        tcp_client_layout.addWidget(self.tcp_cli_host)
        tcp_client_layout.addWidget(QLabel("Remote Port:", self))
        self.tcp_cli_port = QLineEdit("19085", self)
        self.tcp_cli_port.textChanged.connect(self.update_generated_args)
        tcp_client_layout.addWidget(self.tcp_cli_port)
        self.param_stack.addWidget(tcp_client_widget)

        # 3. TCP Server Panel
        tcp_server_widget = QWidget(self)
        tcp_server_layout = QHBoxLayout(tcp_server_widget)
        tcp_server_layout.setContentsMargins(0, 5, 0, 5)
        tcp_server_layout.addWidget(QLabel("Listen Host:", self))
        self.tcp_srv_host = QLineEdit("0.0.0.0", self)
        self.tcp_srv_host.textChanged.connect(self.update_generated_args)
        tcp_server_layout.addWidget(self.tcp_srv_host)
        tcp_server_layout.addWidget(QLabel("Listen Port:", self))
        self.tcp_srv_port = QLineEdit("19085", self)
        self.tcp_srv_port.textChanged.connect(self.update_generated_args)
        tcp_server_layout.addWidget(self.tcp_srv_port)
        self.param_stack.addWidget(tcp_server_widget)

        # 4. TCP Proxy Panel
        tcp_proxy_widget = QWidget(self)
        tcp_proxy_layout = QHBoxLayout(tcp_proxy_widget)
        tcp_proxy_layout.setContentsMargins(0, 5, 0, 5)
        tcp_proxy_layout.addWidget(QLabel("Listen Host:", self))
        self.tcp_prx_listen_host = QLineEdit("127.0.0.1", self)
        self.tcp_prx_listen_host.textChanged.connect(self.update_generated_args)
        tcp_proxy_layout.addWidget(self.tcp_prx_listen_host)
        tcp_proxy_layout.addWidget(QLabel("Listen Port:", self))
        self.tcp_prx_listen_port = QLineEdit("19000", self)
        self.tcp_prx_listen_port.textChanged.connect(self.update_generated_args)
        tcp_proxy_layout.addWidget(self.tcp_prx_listen_port)
        tcp_proxy_layout.addWidget(QLabel("Target Host:", self))
        self.tcp_prx_target_host = QLineEdit("127.0.0.1", self)
        self.tcp_prx_target_host.textChanged.connect(self.update_generated_args)
        tcp_proxy_layout.addWidget(self.tcp_prx_target_host)
        tcp_proxy_layout.addWidget(QLabel("Target Port:", self))
        self.tcp_prx_target_port = QLineEdit("19085", self)
        self.tcp_prx_target_port.textChanged.connect(self.update_generated_args)
        tcp_proxy_layout.addWidget(self.tcp_prx_target_port)
        self.param_stack.addWidget(tcp_proxy_widget)

        # 5. Serial Panel
        serial_widget = QWidget(self)
        serial_layout = QHBoxLayout(serial_widget)
        serial_layout.setContentsMargins(0, 5, 0, 5)
        serial_layout.addWidget(QLabel("Port Path:", self))
        self.ser_port = QLineEdit("/dev/ttyUSB0", self)
        self.ser_port.textChanged.connect(self.update_generated_args)
        serial_layout.addWidget(self.ser_port)
        serial_layout.addWidget(QLabel("Baud Rate:", self))
        self.ser_baud = QComboBox(self)
        self.ser_baud.setEditable(True)
        self.ser_baud.addItems([
            "1200", "2400", "4800", "9600", "19200", "38400",
            "57600", "115200", "230400", "460800", "921600"
        ])
        self.ser_baud.setCurrentText("115200")
        self.ser_baud.currentIndexChanged.connect(self.update_generated_args)
        self.ser_baud.editTextChanged.connect(self.update_generated_args)
        serial_layout.addWidget(self.ser_baud)
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
        self.dec_fixed_size.valueChanged.connect(self.update_generated_args)
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
        self.dec_delim_edit.textChanged.connect(self.update_generated_args)
        dec_delim_layout.addWidget(self.dec_delim_edit)
        self.dec_delim_inc_cb = QCheckBox("Include Delimiter", self)
        self.dec_delim_inc_cb.setChecked(False)
        self.dec_delim_inc_cb.toggled.connect(self.update_generated_args)
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
        self.dec_len_size_combo.currentIndexChanged.connect(self.update_generated_args)
        dec_len_layout.addWidget(self.dec_len_size_combo)

        dec_len_layout.addWidget(QLabel("Endian:", self))
        self.dec_len_endian_combo = QComboBox(self)
        self.dec_len_endian_combo.addItems(["big", "little"])
        self.dec_len_endian_combo.setCurrentText("big")
        self.dec_len_endian_combo.currentIndexChanged.connect(self.update_generated_args)
        dec_len_layout.addWidget(self.dec_len_endian_combo)

        self.dec_len_inc_hdr_cb = QCheckBox("Includes Header", self)
        self.dec_len_inc_hdr_cb.setChecked(False)
        self.dec_len_inc_hdr_cb.toggled.connect(self.update_generated_args)
        dec_len_layout.addWidget(self.dec_len_inc_hdr_cb)
        self.decoder_param_stack.addWidget(dec_len_widget)

        split_config_layout.addWidget(right_widget, 1)
        conn_layout.addLayout(split_config_layout)

        # Common Row (Log File & Extra Args)
        common_layout = QHBoxLayout()
        common_layout.addWidget(QLabel("Log File:", self))
        self.log_file_edit = QLineEdit("udp.jsonl", self)
        self.log_file_edit.textChanged.connect(self.update_generated_args)
        common_layout.addWidget(self.log_file_edit)

        common_layout.addWidget(QLabel("Extra Args:", self))
        self.extra_args_edit = QLineEdit("", self)
        self.extra_args_edit.setPlaceholderText("e.g. --latency")
        self.extra_args_edit.textChanged.connect(self.update_generated_args)
        common_layout.addWidget(self.extra_args_edit)
        conn_layout.addLayout(common_layout)

        # Generated Args Row (Read-only preview)
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("Args Preview:", self))
        self.cli_args_edit = QLineEdit(self)
        self.cli_args_edit.setReadOnly(True)
        preview_layout.addWidget(self.cli_args_edit)
        conn_layout.addLayout(preview_layout)

        top_control_layout.addWidget(self.conn_group)

        # Row 2: Action Buttons & Status Indicators (Compact 1 Row)
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

        self.open_log_btn = QPushButton("Open Log", self)
        self.open_log_btn.clicked.connect(self.open_log_file)
        action_btn_layout.addWidget(self.open_log_btn)

        self.pause_btn = QPushButton("Pause", self)
        self.pause_btn.clicked.connect(self.toggle_pause)
        action_btn_layout.addWidget(self.pause_btn)

        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.clicked.connect(self.clear_all)
        action_btn_layout.addWidget(self.clear_btn)

        action_btn_layout.addSpacing(20)
        self.status_label = QLabel("Status: disconnected", self)
        action_btn_layout.addWidget(self.status_label)
        self.mode_label = QLabel("Mode: idle", self)
        action_btn_layout.addWidget(self.mode_label)
        action_btn_layout.addStretch()
        top_control_layout.addLayout(action_btn_layout)

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

        main_splitter.addWidget(self.detail_tabs)

        main_splitter.setSizes([600, 220])

        # Send Panel (CuteCom style)
        self.send_group = QGroupBox("Send Message (to Target Device via CLI Stdin)", self)
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

        main_layout.addWidget(self.send_group)

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
            worker = self.worker
            self.worker = None
            worker.stop()

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
        self.browse_cli_btn.setEnabled(not running)
        self.conn_group.setEnabled(not running)
        self.send_group.setEnabled(running)

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
        self.text_view.clear()
        self.detail_view.clear()

    def on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        indexes = selected.indexes()
        if not indexes:
            self.hex_view.clear()
            self.text_view.clear()
            self.detail_view.clear()
            return

        row = indexes[0].row()
        event = self.table_model.event_at(row)
        if event:
            self.hex_view.set_payload_hex(event.payload_hex)
            self.detail_view.set_event(event)
            
            # Decode text representation for the Text tab
            if event.payload_hex:
                import re
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

    def start_capture(self):
        executable = self.cli_path_edit.text().strip()
        if not executable:
            QMessageBox.warning(self, "Warning", "CLI Path is empty.")
            return

        import shutil
        resolved_path = shutil.which(executable)
        if not resolved_path:
            QMessageBox.warning(
                self,
                "Warning",
                f"CLI executable not found or not executable:\n{executable}"
            )
            return

        args_text = self.cli_args_edit.text().strip()

        from .ipc_path import make_default_ipc_path
        self.generated_ipc_path = make_default_ipc_path()
        self.socket_path_edit.setText(self.generated_ipc_path)

        from .capture_command import build_capture_command
        try:
            cmd = build_capture_command(executable, args_text, self.generated_ipc_path)
            self.active_cmd_args = cmd.args
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
            self.disconnect_socket()
            self.set_mode("idle")
            self.status_label.setText("Status: disconnected")

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

    def on_send_format_changed(self):
        is_hex = self.hex_radio.isChecked()
        self.eol_combo.setEnabled(not is_hex)
        if is_hex:
            self.send_input.setPlaceholderText("Enter hex bytes (e.g. AA BB CC 00)...")
        else:
            self.send_input.setPlaceholderText("Type message to send...")

    def send_data(self):
        if not self.capture_process.is_running():
            QMessageBox.warning(self, "Warning", "Cannot send data: CLI capture process is not running.")
            return

        text = self.send_input.text().strip()
        if not text:
            return

        is_hex = self.hex_radio.isChecked()

        # Check active CLI flags
        is_cli_hex = True  # Default to True because build_capture_command auto-appends --send-hex
        if hasattr(self, "active_cmd_args"):
            if "--send-text" in self.active_cmd_args:
                is_cli_hex = False
            elif "--send-hex" in self.active_cmd_args:
                is_cli_hex = True

        if is_cli_hex:
            if is_hex:
                # Validate and clean hex input
                import re
                clean_hex = re.sub(r'(0x|0X|[\s:\-])', '', text).lower()
                if not clean_hex or not all(c in '0123456789abcdefABCDEF' for c in clean_hex) or len(clean_hex) % 2 != 0:
                    QMessageBox.warning(
                        self,
                        "Invalid Hex",
                        "Please enter a valid hex string (e.g. AA BB CC or AABBCC).\n"
                        "Note: Each byte must have two hex digits."
                    )
                    return
                write_payload = clean_hex + "\n"
            else:
                # Prepare text with EOL and encode to Hex
                eol_idx = self.eol_combo.currentIndex()
                # 0: None, 1: LF (\n), 2: CR (\r), 3: CRLF (\r\n)
                if eol_idx == 1:
                    text += "\n"
                elif eol_idx == 2:
                    text += "\r"
                elif eol_idx == 3:
                    text += "\r\n"
                
                try:
                    write_payload = text.encode("utf-8").hex() + "\n"
                except Exception as exc:
                    QMessageBox.critical(self, "Error", f"Failed to encode text to hex bytes: {exc}")
                    return
        else:
            # CLI is running in --send-text mode
            if is_hex:
                QMessageBox.warning(
                    self,
                    "Incompatible Mode",
                    "CLI is running in --send-text mode, which cannot receive raw hex bytes.\n"
                    "Please remove '--send-text' from Args to allow dynamic hex sending."
                )
                return
            else:
                # Prepare text with EOL
                eol_idx = self.eol_combo.currentIndex()
                if eol_idx == 1:
                    text += "\n"
                elif eol_idx == 2:
                    text += "\r"
                elif eol_idx == 3:
                    text += "\r\n"
                write_payload = text + "\n"

        try:
            self.capture_process.write_stdin(write_payload.encode("utf-8"))
            self.send_input.clear()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to send data: {exc}")

    def load_settings(self):
        default_cli = find_packet_probe_binary()
        cli_path = self.settings.value("cli_path", default_cli)
        self.cli_path_edit.setText(cli_path)

        socket_path = self.settings.value("socket_path", self.initial_socket_path)
        self.socket_path_edit.setText(socket_path)

        send_in_hex = self.settings.value("send_in_hex", "false") == "true"
        if send_in_hex:
            self.hex_radio.setChecked(True)
        else:
            self.text_radio.setChecked(True)

        eol_index = int(self.settings.value("eol_index", 0))
        self.eol_combo.setCurrentIndex(eol_index)

        # Load Connection mode and fields
        mode_idx = int(self.settings.value("mode_index", 0))
        self.mode_combo.setCurrentIndex(mode_idx)

        # UDP fields
        self.udp_bind_host.setText(self.settings.value("udp_bind_host", "0.0.0.0"))
        self.udp_bind_port.setText(self.settings.value("udp_bind_port", "19000"))
        self.udp_target_host.setText(self.settings.value("udp_target_host", "127.0.0.1"))
        self.udp_target_port.setText(self.settings.value("udp_target_port", "19085"))

        # TCP Client fields
        self.tcp_cli_host.setText(self.settings.value("tcp_cli_host", "127.0.0.1"))
        self.tcp_cli_port.setText(self.settings.value("tcp_cli_port", "19085"))

        # TCP Server fields
        self.tcp_srv_host.setText(self.settings.value("tcp_srv_host", "0.0.0.0"))
        self.tcp_srv_port.setText(self.settings.value("tcp_srv_port", "19085"))

        # TCP Proxy fields
        self.tcp_prx_listen_host.setText(self.settings.value("tcp_prx_listen_host", "127.0.0.1"))
        self.tcp_prx_listen_port.setText(self.settings.value("tcp_prx_listen_port", "19000"))
        self.tcp_prx_target_host.setText(self.settings.value("tcp_prx_target_host", "127.0.0.1"))
        self.tcp_prx_target_port.setText(self.settings.value("tcp_prx_target_port", "19085"))

        # Serial fields
        self.ser_port.setText(self.settings.value("ser_port", "/dev/ttyUSB0"))
        self.ser_baud.setCurrentText(self.settings.value("ser_baud", "115200"))

        # Load Decoder fields
        dec_idx = int(self.settings.value("decoder_index", 0))
        self.decoder_combo.setCurrentIndex(dec_idx)
        self.decoder_param_stack.setCurrentIndex(dec_idx)

        self.dec_fixed_size.setValue(int(self.settings.value("dec_fixed_size", 16)))
        self.dec_delim_edit.setText(self.settings.value("dec_delim", "0A"))
        self.dec_delim_inc_cb.setChecked(self.settings.value("dec_delim_inc", "false") == "true")
        self.dec_len_size_combo.setCurrentText(self.settings.value("dec_len_size", "2"))
        self.dec_len_endian_combo.setCurrentText(self.settings.value("dec_len_endian", "big"))
        self.dec_len_inc_hdr_cb.setChecked(self.settings.value("dec_len_inc_hdr", "false") == "true")

        settings_visible = self.settings.value("settings_visible", "true") == "true"
        self.toggle_settings_btn.setChecked(settings_visible)
        self.conn_group.setVisible(settings_visible)

        # Common fields
        self.log_file_edit.setText(self.settings.value("log_file", "udp.jsonl"))
        self.extra_args_edit.setText(self.settings.value("extra_args", ""))

        self.update_generated_args()

    def save_settings(self):
        self.settings.setValue("cli_path", self.cli_path_edit.text().strip())
        self.settings.setValue("socket_path", self.socket_path_edit.text().strip())
        self.settings.setValue("send_in_hex", "true" if self.hex_radio.isChecked() else "false")
        self.settings.setValue("eol_index", self.eol_combo.currentIndex())

        # Save Connection fields
        self.settings.setValue("mode_index", self.mode_combo.currentIndex())
        self.settings.setValue("udp_bind_host", self.udp_bind_host.text().strip())
        self.settings.setValue("udp_bind_port", self.udp_bind_port.text().strip())
        self.settings.setValue("udp_target_host", self.udp_target_host.text().strip())
        self.settings.setValue("udp_target_port", self.udp_target_port.text().strip())

        self.settings.setValue("tcp_cli_host", self.tcp_cli_host.text().strip())
        self.settings.setValue("tcp_cli_port", self.tcp_cli_port.text().strip())

        self.settings.setValue("tcp_srv_host", self.tcp_srv_host.text().strip())
        self.settings.setValue("tcp_srv_port", self.tcp_srv_port.text().strip())

        self.settings.setValue("tcp_prx_listen_host", self.tcp_prx_listen_host.text().strip())
        self.settings.setValue("tcp_prx_listen_port", self.tcp_prx_listen_port.text().strip())
        self.settings.setValue("tcp_prx_target_host", self.tcp_prx_target_host.text().strip())
        self.settings.setValue("tcp_prx_target_port", self.tcp_prx_target_port.text().strip())

        self.settings.setValue("ser_port", self.ser_port.text().strip())
        self.settings.setValue("ser_baud", self.ser_baud.currentText().strip())

        # Save Decoder fields
        self.settings.setValue("decoder_index", self.decoder_combo.currentIndex())
        self.settings.setValue("dec_fixed_size", self.dec_fixed_size.value())
        self.settings.setValue("dec_delim", self.dec_delim_edit.text().strip())
        self.settings.setValue("dec_delim_inc", "true" if self.dec_delim_inc_cb.isChecked() else "false")
        self.settings.setValue("dec_len_size", self.dec_len_size_combo.currentText())
        self.settings.setValue("dec_len_endian", self.dec_len_endian_combo.currentText())
        self.settings.setValue("dec_len_inc_hdr", "true" if self.dec_len_inc_hdr_cb.isChecked() else "false")
        self.settings.setValue("settings_visible", "true" if self.toggle_settings_btn.isChecked() else "false")

        self.settings.setValue("log_file", self.log_file_edit.text().strip())
        self.settings.setValue("extra_args", self.extra_args_edit.text().strip())

    def on_mode_changed(self, index: int):
        self.param_stack.setCurrentIndex(index)
        
        # Auto-update default log file name based on mode
        mode = self.mode_combo.currentText()
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
            
        self.update_generated_args()

    def update_generated_args(self):
        mode = self.mode_combo.currentText()
        args = []

        if mode == "UDP":
            args.append("udp")
            if self.udp_bind_host.text().strip():
                args.extend(["--bind-host", self.udp_bind_host.text().strip()])
            if self.udp_bind_port.text().strip():
                args.extend(["--bind-port", self.udp_bind_port.text().strip()])
            if self.udp_target_host.text().strip():
                args.extend(["--target-host", self.udp_target_host.text().strip()])
            if self.udp_target_port.text().strip():
                args.extend(["--target-port", self.udp_target_port.text().strip()])

        elif mode == "TCP Client":
            args.append("tcp-client")
            if self.tcp_cli_host.text().strip():
                args.extend(["--host", self.tcp_cli_host.text().strip()])
            if self.tcp_cli_port.text().strip():
                args.extend(["--port", self.tcp_cli_port.text().strip()])

        elif mode == "TCP Server":
            args.append("tcp-server")
            if self.tcp_srv_host.text().strip():
                args.extend(["--listen-host", self.tcp_srv_host.text().strip()])
            if self.tcp_srv_port.text().strip():
                args.extend(["--listen-port", self.tcp_srv_port.text().strip()])

        elif mode == "TCP Proxy":
            args.append("tcp-proxy")
            if self.tcp_prx_listen_host.text().strip():
                args.extend(["--listen-host", self.tcp_prx_listen_host.text().strip()])
            if self.tcp_prx_listen_port.text().strip():
                args.extend(["--listen-port", self.tcp_prx_listen_port.text().strip()])
            if self.tcp_prx_target_host.text().strip():
                args.extend(["--target-host", self.tcp_prx_target_host.text().strip()])
            if self.tcp_prx_target_port.text().strip():
                args.extend(["--target-port", self.tcp_prx_target_port.text().strip()])

        elif mode == "Serial":
            args.append("serial")
            if self.ser_port.text().strip():
                args.extend(["--port", self.ser_port.text().strip()])
            if self.ser_baud.currentText().strip():
                args.extend(["--baudrate", self.ser_baud.currentText().strip()])

        # Frame Decoder options
        decoder = self.decoder_combo.currentText()
        if decoder != "raw":
            args.extend(["--decoder", decoder])
            if decoder == "fixed":
                args.extend(["--frame-size", str(self.dec_fixed_size.value())])
            elif decoder == "delimiter":
                delim = self.dec_delim_edit.text().strip()
                if delim:
                    args.extend(["--delimiter", delim])
                if self.dec_delim_inc_cb.isChecked():
                    args.append("--include-delimiter")
            elif decoder == "length-prefix":
                args.extend(["--length-size", self.dec_len_size_combo.currentText()])
                args.extend(["--length-endian", self.dec_len_endian_combo.currentText()])
                if self.dec_len_inc_hdr_cb.isChecked():
                    args.append("--length-includes-header")

        # Common option: log file
        log_file = self.log_file_edit.text().strip()
        if log_file:
            args.extend(["--log", log_file])

        # Common option: extra args
        extra = self.extra_args_edit.text().strip()
        if extra:
            args.append(extra)

        generated_str = " ".join(args)
        self.cli_args_edit.setText(generated_str)

    def on_decoder_changed(self, index: int):
        self.decoder_param_stack.setCurrentIndex(index)
        self.update_generated_args()

    def toggle_settings_visibility(self, checked: bool):
        self.conn_group.setVisible(checked)

    def closeEvent(self, event):
        self.save_settings()
        self.stop_capture()
        self.disconnect_socket()
        event.accept()
