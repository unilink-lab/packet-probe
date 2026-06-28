from dataclasses import dataclass
import shlex
import os

@dataclass
class CaptureCommand:
    executable: str
    args: list[str]
    ipc_path: str
    send_mode: str  # "hex", "text", or "file"

def parse_capture_args(args_text: str) -> list[str]:
    return shlex.split(args_text, posix=(os.name != "nt"))

def _contains_ipc_arg(args: list[str]) -> bool:
    return any(arg == "--ipc" or arg.startswith("--ipc=") for arg in args)

def build_capture_command(executable: str, args_text: str, ipc_path: str) -> CaptureCommand:
    args = parse_capture_args(args_text)
    if _contains_ipc_arg(args):
        raise ValueError("Do not pass --ipc manually in launcher mode; viewer manages IPC automatically.")

    if "--send-text" in args:
        send_mode = "text"
    elif "--send-file" in args:
        send_mode = "file"
    else:
        send_mode = "hex"
        if "--send-hex" not in args:
            args.append("--send-hex")

    args.extend(["--ipc", ipc_path])
    return CaptureCommand(executable=executable, args=args, ipc_path=ipc_path, send_mode=send_mode)
