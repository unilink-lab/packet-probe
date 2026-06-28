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
