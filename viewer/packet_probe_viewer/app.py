import sys
import argparse
from PySide6.QtWidgets import QApplication
from .main_window import MainWindow

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Optional read-only viewer for Packet Probe event streams"
    )
    parser.add_argument(
        "--socket",
        default="/tmp/packet-probe.sock",
        help="Path to the UDS IPC socket (default: /tmp/packet-probe.sock)",
    )
    return parser

def run(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    app = QApplication([sys.argv[0]])
    window = MainWindow(initial_socket_path=args.socket)
    window.show()

    return app.exec()
