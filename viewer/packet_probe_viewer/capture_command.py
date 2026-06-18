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

def _contains_ipc_arg(args: list[str]) -> bool:
    return any(arg == "--ipc" or arg.startswith("--ipc=") for arg in args)

def build_capture_command(executable: str, args_text: str, ipc_path: str) -> CaptureCommand:
    args = parse_capture_args(args_text)
    if _contains_ipc_arg(args):
        raise ValueError("Do not pass --ipc manually in launcher mode; viewer manages IPC automatically.")
    
    # Auto-append --send-hex to support dynamic Text/Hex format sending from GUI
    has_send_option = any(arg in ["--send-text", "--send-hex", "--send-file"] for arg in args)
    if not has_send_option:
        args.append("--send-hex")
        
    args.extend(["--ipc", ipc_path])
    return CaptureCommand(executable=executable, args=args, ipc_path=ipc_path)

