from packet_probe_viewer.app import build_arg_parser

def test_default_socket_path():
    parser = build_arg_parser()
    args = parser.parse_args([])
    assert args.socket == "/tmp/packet-probe.sock"

def test_custom_socket_path():
    parser = build_arg_parser()
    args = parser.parse_args(["--socket", "/tmp/custom.sock"])
    assert args.socket == "/tmp/custom.sock"
