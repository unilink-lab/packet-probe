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


def test_main_window_settings_and_presets(qtbot):
    window = MainWindow(settings_org="UnilinkLabTest", settings_app="PacketProbeViewerTest")
    qtbot.addWidget(window)

    # 1. Verify default preset combo setup and auto-change behavior
    assert window.preset_combo.count() == 4
    assert window.preset_combo.itemText(1) == "UDP Loopback (19085)"

    # Change to UDP Loopback preset
    window.preset_combo.setCurrentIndex(1)
    assert "udp" in window.cli_args_edit.text()
    assert "--target-port 19085" in window.cli_args_edit.text()

    # Edit arguments manually -> preset combo should change back to "Custom" (index 0)
    window.cli_args_edit.setText("udp --custom-flag")
    assert window.preset_combo.currentIndex() == 0

    # 2. Verify QSettings persistence (save and load)
    # Modify settings values
    window.cli_path_edit.setText("/mock/path/packet-probe")
    window.cli_args_edit.setText("tcp-client --custom")
    window.preset_combo.setCurrentIndex(0)
    window.socket_path_edit.setText("/mock/path/socket")
    window.hex_radio.setChecked(True)
    window.eol_combo.setCurrentIndex(2) # CR (\r)

    # Save settings
    window.save_settings()

    # Create a new window instance to load from settings
    new_window = MainWindow(settings_org="UnilinkLabTest", settings_app="PacketProbeViewerTest")
    qtbot.addWidget(new_window)

    # Assert new window loaded saved settings
    assert new_window.cli_path_edit.text() == "/mock/path/packet-probe"
    assert new_window.cli_args_edit.text() == "tcp-client --custom"
    assert new_window.preset_combo.currentIndex() == 0
    assert new_window.socket_path_edit.text() == "/mock/path/socket"
    assert new_window.hex_radio.isChecked() is True
    assert new_window.eol_combo.currentIndex() == 2
