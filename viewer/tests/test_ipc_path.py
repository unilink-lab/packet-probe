from packet_probe_viewer.ipc_path import make_default_ipc_path
import os

def test_make_default_ipc_path():
    path = make_default_ipc_path()
    assert path != ""
    assert path.endswith(".sock")
    assert str(os.getpid()) in path
