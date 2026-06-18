from PySide6.QtCore import Qt
from packet_probe_viewer.main_window import MainWindow
from packet_probe_viewer.event_model import PacketEvent

def test_main_window_tabs(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    # Check that tabs are instantiated and present
    assert window.text_view is not None
    assert window.hex_view is not None
    assert window.detail_tabs.tabText(1) == "Text"

    # Test clearing all resets the tab contents
    window.text_view.setPlainText("dummy")
    window.hex_view.setPlainText("dummy")
    window.clear_all()
    assert window.text_view.toPlainText() == ""
    assert window.hex_view.toPlainText() == ""

    # Append mock event with binary payload
    event = PacketEvent({
        "seq": 1,
        "payload_hex": "48656c6c6f0a",  # "Hello\n"
        "type": "raw_bytes",
        "summary": "hello"
    })
    window.table_model.append_event(event)

    # Select the row
    idx = window.table_model.index(0, 0)
    selection_model = window.table_view.selectionModel()
    selection_model.select(
        idx,
        selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows
    )
    
    # Trigger selection changed handler manually to populate widgets
    window.on_selection_changed(selection_model.selection(), None)

    # Verify Text tab has decoded readable characters
    assert window.text_view.toPlainText() == "Hello\n"

    # Verify Hex tab has premium formatted hex dump with ASCII sidebar
    hex_content = window.hex_view.toPlainText()
    assert "48 65 6c 6c 6f 0a" in hex_content
    assert "|Hello.|" in hex_content


def test_main_window_send_payload_conversion(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    # Setup active command arguments showing hex send is active (default)
    window.active_cmd_args = ["--send-hex"]
    
    # 1. Test Text Mode GUI sending to Hex Mode CLI
    window.text_radio.setChecked(True)
    window.eol_combo.setCurrentIndex(1)  # LF (\n)
    window.send_input.setText("Hello")
    
    # We stub capture_process.write_stdin to verify what is sent
    written_data = []
    window.capture_process.write_stdin = lambda d: written_data.append(d)
    window.capture_process.is_running = lambda: True

    window.send_data()
    # "Hello\n" -> "48656c6c6f0a\n"
    assert len(written_data) == 1
    assert written_data[0] == b"48656c6c6f0a\n"

    # 2. Test Hex Mode GUI sending to Hex Mode CLI
    written_data.clear()
    window.hex_radio.setChecked(True)
    window.send_input.setText("AA BB CC")
    
    window.send_data()
    # "AA BB CC" clean -> "aabbcc\n"
    assert len(written_data) == 1
    assert written_data[0] == b"aabbcc\n"
