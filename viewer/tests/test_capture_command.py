import pytest
from packet_probe_viewer.capture_command import build_capture_command, parse_capture_args

def test_parse_capture_args():
    args = parse_capture_args("udp --bind-host 127.0.0.1 --bind-port 19000")
    assert args == ["udp", "--bind-host", "127.0.0.1", "--bind-port", "19000"]

def test_build_capture_command_adds_ipc():
    cmd = build_capture_command(
        "packet-probe",
        "udp --bind-host 127.0.0.1 --bind-port 19000",
        "/tmp/pp.sock"
    )
    assert cmd.executable == "packet-probe"
    assert cmd.args[0] == "udp"
    assert cmd.args[-2:] == ["--ipc", "/tmp/pp.sock"]
    assert cmd.ipc_path == "/tmp/pp.sock"

def test_build_capture_command_rejects_manual_ipc():
    with pytest.raises(ValueError):
        build_capture_command(
            "packet-probe",
            "udp --bind-port 19000 --ipc /tmp/custom.sock",
            "/tmp/pp.sock"
        )

def test_parse_capture_args_with_quoted_value():
    args = parse_capture_args('udp --log "my capture.jsonl"')
    assert args == ["udp", "--log", "my capture.jsonl"]

def test_build_capture_command_rejects_manual_ipc_equals_form():
    with pytest.raises(ValueError):
        build_capture_command(
            "packet-probe",
            "udp --bind-port 19000 --ipc=/tmp/custom.sock",
            "/tmp/pp.sock"
        )

