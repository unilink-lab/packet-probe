"""In-process driver for the Packet Probe Viewer (PySide6) GUI.

Rather than external UI automation (tmux/screen-scraping), this instantiates
the real `MainWindow` inside a real `QApplication` and drives it directly via
its Python API/widgets - the same approach the project's own
`viewer/tests/test_main_window.py` uses with pytest-qt's `qtbot`, just outside
pytest so it can run as a one-shot script and take real screenshots.

Usage (run from the `viewer/` directory so `packet_probe_viewer` importable,
or let this script add it to sys.path via --viewer-dir):

    python driver.py screenshot [--out-dir DIR]
    python driver.py udp-capture [--out-dir DIR] [--port PORT] [--cli-path PATH]

Exit code 0 on success, 1 on failure. Screenshots (PNG) are written to
--out-dir (default: alongside this script).
"""

import argparse
import os
import socket
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
REPO_ROOT = SKILL_DIR.parents[2]  # .claude/skills/run-packet-probe-viewer -> repo root
VIEWER_DIR = REPO_ROOT / "viewer"
DEFAULT_CLI_PATH = REPO_ROOT / "build" / "Debug" / "packet-probe.exe"


def pump(app, duration_s):
    end = time.time() + duration_s
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def make_window():
    sys.path.insert(0, str(VIEWER_DIR))
    os.chdir(VIEWER_DIR)
    from PySide6.QtWidgets import QApplication
    from packet_probe_viewer.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.resize(1400, 900)
    window.show()
    return app, window


def shutdown(app, window):
    try:
        if getattr(window, "capture_process", None) and window.capture_process.is_running():
            window.stop_capture_btn.click()
            pump(app, 1.0)
            window.capture_process.stop()
        window.close()
        pump(app, 0.3)
    except Exception as exc:
        print(f"[driver] non-fatal cleanup error: {exc}")
    app.quit()
    # Some Qt worker threads (IpcClientWorker) can outlive a clean app.quit()
    # on Windows; force-exit rather than hang the driver process.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


def cmd_screenshot(args):
    app, window = make_window()
    pump(app, 0.5)
    out = Path(args.out_dir) / "screenshot.png"
    window.grab().save(str(out))
    print(f"[driver] PASS: screenshot written to {out}")
    shutdown(app, window)


def cmd_udp_capture(args):
    app, window = make_window()
    pump(app, 0.5)
    out_dir = Path(args.out_dir)

    window.grab().save(str(out_dir / "01_before_start.png"))

    window.cli_path_edit.setText(args.cli_path)
    window.mode_combo.setCurrentIndex(0)  # UDP
    window.udp_bind_host.setText("127.0.0.1")
    window.udp_bind_port.setText(str(args.port))
    # Must be cleared: a non-empty Target Host/Port connect()s the UDP socket
    # to that one peer, silently dropping datagrams from any other source
    # (see Gotchas in SKILL.md) - the default form values are NOT receive-all.
    window.udp_target_host.setText("")
    window.udp_target_port.setText("")
    pump(app, 0.2)

    print(f"[driver] cli_path = {window.cli_path_edit.text()}")
    window.start_capture_btn.click()

    deadline = time.time() + 15
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.05)
        if window._engine_state == "capturing":
            break

    print(f"[driver] engine_state = {window._engine_state}, ipc_connected = {window._ipc_connected}")
    window.grab().save(str(out_dir / "02_after_capturing.png"))

    if window._engine_state != "capturing":
        print("[driver] FAIL: engine never reached capturing state")
        print("---process_output---")
        print(window.process_output.toPlainText())
        shutdown(app, window)
        sys.exit(1)

    pump(app, 0.5)  # let the udp socket finish binding before we send
    baseline_rows = window.table_model.rowCount()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(bytes.fromhex("02 10 01 00 03 A7"), ("127.0.0.1", args.port))
    s.close()

    deadline = time.time() + 8
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.05)
        if window.table_model.rowCount() > baseline_rows:
            break

    row_count = window.table_model.rowCount()
    window.grab().save(str(out_dir / "03_after_event.png"))

    got_raw_bytes = False
    for r in range(row_count):
        row_type = window.table_model.data(window.table_model.index(r, 4))
        if row_type == "raw_bytes":
            got_raw_bytes = True

    window.stop_capture_btn.click()
    pump(app, 1.0)

    if got_raw_bytes:
        print(f"[driver] PASS: {row_count} events captured (baseline {baseline_rows}), raw_bytes event seen")
        shutdown(app, window)
    else:
        print(f"[driver] FAIL: no raw_bytes event after sending test datagram ({row_count} rows total)")
        shutdown(app, window)
        sys.exit(1)


SCENARIOS = {
    "screenshot": cmd_screenshot,
    "udp-capture": cmd_udp_capture,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--out-dir", default=str(SKILL_DIR))
    parser.add_argument("--port", type=int, default=19126)
    parser.add_argument("--cli-path", default=str(DEFAULT_CLI_PATH))
    args = parser.parse_args()

    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    SCENARIOS[args.scenario](args)


if __name__ == "__main__":
    main()
