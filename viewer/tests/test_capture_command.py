import pytest
from packet_probe_viewer.capture_command import (
    build_capture_config,
    build_decoder_config,
    engine_mode_for_ui,
    supports_send,
)


def _common(**overrides):
    base = {"log_path": "", "hex_raw": False, "hex_frame": False, "latency": True}
    base.update(overrides)
    return base


def test_engine_mode_for_ui():
    assert engine_mode_for_ui("UDP") == "udp"
    assert engine_mode_for_ui("TCP Client") == "tcp-client"
    assert engine_mode_for_ui("TCP Server") == "tcp-server"
    assert engine_mode_for_ui("TCP Proxy") == "tcp-proxy"
    assert engine_mode_for_ui("Serial") == "serial"
    with pytest.raises(ValueError):
        engine_mode_for_ui("Not A Mode")


def test_supports_send():
    assert supports_send("udp") is True
    assert supports_send("tcp-client") is True
    assert supports_send("tcp-proxy") is False


def test_build_udp_config():
    decoder = build_decoder_config("raw")
    config = build_capture_config(
        "UDP",
        {"bind_host": "0.0.0.0", "bind_port": "19000", "target_host": "127.0.0.1", "target_port": "19085"},
        decoder,
        _common(log_path="udp.jsonl"),
    )
    assert config["mode"] == "udp"
    assert config["bind_host"] == "0.0.0.0"
    assert config["bind_port"] == 19000
    assert config["target_host"] == "127.0.0.1"
    assert config["target_port"] == 19085
    assert config["log_path"] == "udp.jsonl"
    assert config["decoder"]["decoder"] == "raw"


def test_build_tcp_client_config():
    decoder = build_decoder_config("raw")
    config = build_capture_config("TCP Client", {"host": "127.0.0.1", "port": "9000"}, decoder, _common())
    assert config["mode"] == "tcp-client"
    assert config["host"] == "127.0.0.1"
    assert config["port"] == 9000


def test_build_serial_config():
    decoder = build_decoder_config("raw")
    config = build_capture_config(
        "Serial", {"serial_port": "/dev/ttyUSB0", "baudrate": "115200"}, decoder, _common()
    )
    assert config["mode"] == "serial"
    assert config["serial_port"] == "/dev/ttyUSB0"
    assert config["baudrate"] == 115200


def test_build_tcp_proxy_config_with_latency():
    decoder = build_decoder_config("raw")
    config = build_capture_config(
        "TCP Proxy",
        {"listen_host": "127.0.0.1", "listen_port": "19000", "target_host": "127.0.0.1", "target_port": "19085"},
        decoder,
        _common(latency=True),
    )
    assert config["mode"] == "tcp-proxy"
    assert config["listen_port"] == 19000
    assert config["target_port"] == 19085
    assert config["latency"] is True


def test_build_config_rejects_invalid_port():
    decoder = build_decoder_config("raw")
    with pytest.raises(ValueError):
        build_capture_config("UDP", {"bind_host": "0.0.0.0", "bind_port": "not-a-port"}, decoder, _common())


def test_build_config_rejects_out_of_range_port():
    decoder = build_decoder_config("raw")
    with pytest.raises(ValueError):
        build_capture_config("UDP", {"bind_host": "0.0.0.0", "bind_port": "99999"}, decoder, _common())


def test_build_decoder_config_delimiter():
    decoder = build_decoder_config("delimiter", delimiter_hex="0A", include_delimiter=False)
    assert decoder["decoder"] == "delimiter"
    assert decoder["delimiter_hex"] == "0A"
    assert decoder["include_delimiter"] is False
