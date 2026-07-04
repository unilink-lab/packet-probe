import json

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

    # Select the row (table_view is backed by the filter proxy, so map into it)
    idx = window.filter_proxy.mapFromSource(window.table_model.index(0, 0))
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

    # Send only goes out over IPC (see docs/ipc-protocol.md, "Control Protocol v2");
    # simulate a connected, capturing engine by stubbing the worker.
    sent_commands = []

    class FakeWorker:
        def send_command(self, cmd):
            sent_commands.append(cmd)
            return cmd.get("id", "fake-id")

    window.worker = FakeWorker()
    window._ipc_connected = True
    window._engine_state = "capturing"

    # 1. Test Text Mode GUI sending
    window.text_radio.setChecked(True)
    window.eol_combo.setCurrentIndex(1)  # LF (\n)
    window.send_input.setText("Hello")

    window.send_data()
    # "Hello\n" -> hex "48656c6c6f0a"
    assert len(sent_commands) == 1
    assert sent_commands[0]["command"] == "send"
    assert sent_commands[0]["payload_hex"] == "48656c6c6f0a"

    # 2. Test Hex Mode GUI sending
    sent_commands.clear()
    window.hex_radio.setChecked(True)
    window.send_input.setText("AA BB CC")

    window.send_data()
    assert len(sent_commands) == 1
    assert sent_commands[0]["command"] == "send"
    assert sent_commands[0]["payload_hex"] == "aabbcc"


def test_main_window_send_result_feedback(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window._pending_commands["s1"] = "send"
    window.on_result_received({"type": "result", "id": "s1", "ok": True})
    assert "Sent" in window.send_feedback_label.text()

    window._pending_commands["s2"] = "send"
    window.on_result_received({"type": "result", "id": "s2", "ok": False, "error": "device gone"})
    assert "device gone" in window.send_feedback_label.text()


def test_main_window_send_requires_connected_capturing_engine(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    # Avoid a real (blocking) modal dialog in the test process.
    warnings = []
    monkeypatch.setattr(
        "packet_probe_viewer.main_window.QMessageBox.warning",
        lambda *args, **kwargs: warnings.append(args[1:]),
    )

    window.send_input.setText("Hello")

    # Not connected at all.
    window.send_data()
    assert len(warnings) == 1

    # Connected but idle (no capture running).
    class FakeWorker:
        def send_command(self, cmd):
            return cmd.get("id", "fake-id")

    window.worker = FakeWorker()
    window._ipc_connected = True
    window._engine_state = "idle"
    window.send_data()
    assert len(warnings) == 2


def test_main_window_settings_and_presets(qtbot):
    window = MainWindow(settings_org="UnilinkLabTest", settings_app="PacketProbeViewerTest")
    qtbot.addWidget(window)

    # 1. Verify default mode combo setup and auto-change behavior
    assert window.mode_combo.count() == 5
    assert window.mode_combo.itemText(0) == "UDP"
    assert window.mode_combo.itemText(1) == "TCP Client"

    # Select TCP Client mode
    window.mode_combo.setCurrentIndex(1)
    assert window.param_stack.currentIndex() == 1
    assert '"mode": "tcp-client"' in window.config_preview_edit.text()

    # Modify Remote Host in TCP Client mode
    window.tcp_cli_host.setText("192.168.1.100")
    window.tcp_cli_port.setText("8080")
    # Verify the read-only preview updates dynamically
    preview = json.loads(window.config_preview_edit.text())
    assert preview["host"] == "192.168.1.100"
    assert preview["port"] == 8080

    # 2. Verify QSettings persistence (save and load)
    # Modify settings values
    window.cli_path_edit.setText("/mock/path/packet-probe")
    window.socket_path_edit.setText("/mock/path/socket")
    window.hex_radio.setChecked(True)
    window.eol_combo.setCurrentIndex(2) # CR (\r)

    # Change to Serial mode and customize parameters
    window.mode_combo.setCurrentIndex(4) # Serial
    window.ser_port.setCurrentText("/dev/ttyACM0")
    window.ser_baud.setCurrentText("9600")
    window.log_file_edit.setText("serial_test.jsonl")
    window.log_file_cb.setChecked(True)

    # Save settings
    window.save_settings()

    # Create a new window instance to load from settings
    new_window = MainWindow(settings_org="UnilinkLabTest", settings_app="PacketProbeViewerTest")
    qtbot.addWidget(new_window)

    # Assert new window loaded saved settings
    assert new_window.cli_path_edit.text() == "/mock/path/packet-probe"
    assert new_window.socket_path_edit.text() == "/mock/path/socket"
    assert new_window.hex_radio.isChecked() is True
    assert new_window.eol_combo.currentIndex() == 2

    # Assert new window restored Serial mode and fields
    assert new_window.mode_combo.currentIndex() == 4
    assert new_window.ser_port.currentText() == "/dev/ttyACM0"
    assert new_window.ser_baud.currentText() == "9600"
    assert new_window.log_file_edit.text() == "serial_test.jsonl"
    assert new_window.log_file_cb.isChecked() is True
    # Verify generated config preview was loaded correctly
    preview = json.loads(new_window.config_preview_edit.text())
    assert preview["mode"] == "serial"
    assert preview["serial_port"] == "/dev/ttyACM0"
    assert preview["baudrate"] == 9600
    assert preview["log_path"] == "serial_test.jsonl"
