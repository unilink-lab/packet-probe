from pathlib import Path
import os
import tempfile

def make_default_ipc_path() -> str:
    pid = os.getpid()
    if os.name == "nt":
        return str(Path(tempfile.gettempdir()) / f"ppv-{pid}.sock")
    else:
        return str(Path(tempfile.gettempdir()) / f"packet-probe-viewer-{pid}.sock")

def resolve_initial_socket_path(initial_socket_path: str | None) -> str:
    return initial_socket_path or "/tmp/packet-probe.sock"
