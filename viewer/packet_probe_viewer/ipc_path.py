from pathlib import Path
import os
import tempfile

def make_default_ipc_path() -> str:
    pid = os.getpid()
    if os.name == "nt":
        return str(Path(tempfile.gettempdir()) / f"ppv-{pid}.sock")
    else:
        return str(Path(tempfile.gettempdir()) / f"packet-probe-viewer-{pid}.sock")
