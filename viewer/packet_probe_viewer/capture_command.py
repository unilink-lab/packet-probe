from dataclasses import dataclass
import shlex
import os

@dataclass
class CaptureCommand:
    executable: str
    args: list[str]
    ipc_path: str

def parse_capture_args(args_text: str) -> list[str]:
    return shlex.split(args_text, posix=(os.name != "nt"))

def build_capture_command(executable: str, args_text: str, ipc_path: str) -> CaptureCommand:
    args = parse_capture_args(args_text)
    if "--ipc" in args:
        raise ValueError("Do not pass --ipc manually in launcher mode; viewer manages IPC automatically.")
    
    args.extend(["--ipc", ipc_path])
    return CaptureCommand(executable=executable, args=args, ipc_path=ipc_path)
