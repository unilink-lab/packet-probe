# Dark theme translated from the "Packet Probe Viewer" design mock
# (claude.ai/design). The mock is authored in oklch; the values below are the
# sRGB/hex equivalents so Qt's stylesheet engine (which has no oklch support)
# renders the same palette. Accent is the UDP cyan from the design, which is
# also the default capture mode.
DARK_THEME_QSS = """
/* General background and text */
QMainWindow {
    background-color: #05070d;
}
QWidget {
    font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    color: #e5e8ed;
}
QLabel {
    color: #aaaeb4;
    font-weight: 500;
}

/* Group Boxes (Configuration / Send panels) - "card" surfaces */
QGroupBox {
    border: 1px solid #1e242e;
    border-radius: 10px;
    margin-top: 12px;
    font-weight: bold;
    color: #6b727e; /* muted uppercase-style section header */
    padding-top: 15px;
    background-color: #0b1016;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
    letter-spacing: 1px;
}

/* Text LineEdits & SpinBoxes */
QLineEdit, QComboBox, QSpinBox {
    background-color: #05070d;
    border: 1px solid #232933;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e5e8ed;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #2cb3b3;
    background-color: #030509;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background-color: #10141b;
    color: #5d646f;
    border: 1px solid #10141b;
}

/* Combo Box Dropdown items */
QComboBox QAbstractItemView {
    background-color: #0b1016;
    border: 1px solid #232933;
    selection-background-color: #2cb3b3;
    selection-color: #090b0f;
    color: #aaaeb4;
}

/* Buttons */
QPushButton {
    background-color: #131921;
    border: 1px solid #282e38;
    border-radius: 7px;
    padding: 6px 14px;
    color: #d4d8de;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1a2029;
    border: 1px solid #3a424e;
}
QPushButton:pressed {
    background-color: #030509;
}
QPushButton:disabled {
    background-color: #0b1016;
    color: #5d646f;
    border: 1px solid #10141b;
}

/* Accent Buttons (primary actions: Start Capture, Send) - filled accent
   with dark text, matching the design's solid mode-colored buttons */
QPushButton#start_capture_btn, QPushButton#send_btn {
    background-color: #2cb3b3;
    border: 1px solid #2cb3b3;
    color: #090b0f;
    font-weight: 700;
}
QPushButton#start_capture_btn:hover, QPushButton#send_btn:hover {
    background-color: #43c4c4;
}
QPushButton#start_capture_btn:pressed, QPushButton#send_btn:pressed {
    background-color: #1f9a9a;
}

/* Stop button - solid danger red */
QPushButton#stop_capture_btn {
    background-color: #c92f33;
    border: 1px solid #c92f33;
    color: #fcf3f2;
    font-weight: 700;
}
QPushButton#stop_capture_btn:hover {
    background-color: #dc4145;
}
QPushButton#stop_capture_btn:pressed {
    background-color: #a5262a;
}

/* Tables */
QTableView {
    background-color: #030509;
    border: 1px solid #1e242e;
    gridline-color: #10141b;
    border-radius: 8px;
    color: #e5e8ed;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
}
QTableView::item:selected {
    background-color: #171f2e;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #090d14;
    color: #6b727e;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #1e242e;
    font-weight: bold;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}

/* Tab Widgets (detail pane) - pill-style tabs */
QTabWidget::pane {
    border: 1px solid #1e242e;
    background-color: #10141b;
    border-radius: 8px;
    position: absolute;
    top: -1px;
}
QTabBar::tab {
    background-color: transparent;
    color: #6b727e;
    border: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    padding: 8px 16px;
    margin-right: 2px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #10141b;
    color: #2cb3b3;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background-color: #131921;
    color: #d4d8de;
}

/* PlainTextEdit for Logs / Text / Hex views */
QPlainTextEdit {
    background-color: #030509;
    border: 1px solid #1e242e;
    border-radius: 8px;
    color: #e5e8ed;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 9px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #2b323d;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #3a424e;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 9px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #2b323d;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #3a424e;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Radio Buttons (Send format) */
QRadioButton {
    color: #aaaeb4;
    font-weight: 500;
    spacing: 6px;
}
QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 8px;
    border: 1px solid #282e38;
    background-color: #05070d;
}
QRadioButton::indicator:checked {
    background-color: #2cb3b3;
    border: 1px solid #2cb3b3;
}
QRadioButton::indicator:hover {
    border: 1px solid #2cb3b3;
}

/* Splitters */
QSplitter::handle {
    background-color: #1e242e;
}
QSplitter::handle:horizontal {
    width: 4px;
}
QSplitter::handle:vertical {
    height: 4px;
}

/* Menu Bar and Menus */
QMenuBar {
    background-color: #090d14;
    border-bottom: 1px solid #1e242e;
}
QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
    color: #aaaeb4;
}
QMenuBar::item:selected {
    background-color: #131921;
    border-radius: 4px;
    color: #ffffff;
}
QMenu {
    background-color: #0b1016;
    border: 1px solid #1e242e;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
    color: #aaaeb4;
}
QMenu::item:selected {
    background-color: #2cb3b3;
    color: #090b0f;
}

/* Checkboxes */
QCheckBox {
    color: #aaaeb4;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #282e38;
    background-color: #05070d;
}
QCheckBox::indicator:checked {
    background-color: #2cb3b3;
    border: 1px solid #2cb3b3;
}
QCheckBox::indicator:hover {
    border: 1px solid #2cb3b3;
}

/* Checked PushButtons (e.g. settings toggle active) */
QPushButton:checked {
    background-color: #2cb3b3;
    color: #090b0f;
    border: 1px solid #2cb3b3;
}

/* Status bar */
QStatusBar {
    background-color: #090d14;
    border-top: 1px solid #1e242e;
    color: #6b727e;
}
QStatusBar::item {
    border: none;
}
"""
