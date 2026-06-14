from packet_probe_viewer.ipc_path import make_default_ipc_path, resolve_initial_socket_path
import os

def test_make_default_ipc_path():
    path = make_default_ipc_path()
    assert path != ""
    assert path.endswith(".sock")
    assert str(os.getpid()) in path

def test_resolve_initial_socket_path_keeps_default_socket():
    assert resolve_initial_socket_path("/tmp/packet-probe.sock") == "/tmp/packet-probe.sock"

def test_resolve_initial_socket_path_uses_default_when_empty():
    assert resolve_initial_socket_path("") == "/tmp/packet-probe.sock"
    assert resolve_initial_socket_path(None) == "/tmp/packet-probe.sock"

