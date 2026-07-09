---
name: run-packet-probe-viewer
description: Build the packet-probe engine and run/drive the Packet Probe Viewer (PySide6 desktop GUI) - start a UDP capture, send a test datagram, verify the event table, and take screenshots. Use when asked to run, start, or screenshot the viewer, or to confirm a viewer change works in the real app end-to-end.
---

Packet Probe Viewer (`viewer/`) is a PySide6 desktop GUI that spawns the
`packet-probe engine` C++ process and talks to it over a Windows Unix Domain
Socket (IPC control protocol v2). It is driven in-process via
`.claude/skills/run-packet-probe-viewer/driver.py`, which instantiates the
real `MainWindow` in a real `QApplication` and calls its widgets/API directly
(the same technique `viewer/tests/test_main_window.py` uses with pytest-qt's
`qtbot`, just outside pytest so it can run as a one-shot script and take
screenshots) - no external UI automation (tmux/screen-scraping) needed since
Python has direct access to the live widget tree.

All paths below are relative to the repo root (`packet-probe/`). This has
only been run/verified on Windows (git-bash + MSVC); there is no Linux path
here.

## Prerequisites

- Python 3.10+ with PySide6 (`pip show PySide6`)
- Visual Studio 2022 Build Tools (MSVC) + CMake, for the C++ engine
- vcpkg with Boost installed for `x64-windows` (the repo's `build/CMakeCache.txt`
  already points `CMAKE_TOOLCHAIN_FILE` at `<vcpkg-root>/scripts/buildsystems/vcpkg.cmake`)
- The `unilink` Python bindings (native extension, package name `unilink`,
  **not** `unilink-python`) - required for live IPC capture. Check:

  ```bash
  python -c "import unilink; print(unilink.__version__, unilink._core.__file__)"
  ```

  If that fails, or `unilink` is older than the `unilink` core repo you're
  building `packet-probe` against, rebuild it from source (see Setup).

## Setup

```bash
cd viewer
python -m pip install -e .
```

If `unilink` needs building/rebuilding (native extension is stale or
missing), it comes from a sibling repo (`unilink-python`, built against
another sibling repo, the `unilink` C++ core - **not** the same as this
`packet-probe` repo's own `build/`). On this machine those live at
`D:/GitHub/unilink-python` and `D:/GitHub/unilink-lab/unilink`; adjust paths
if your layout differs:

```bash
python -m pip install scikit-build-core "pybind11>=2.11,<3" cmake ninja
cd /d/GitHub/unilink-python
rm -rf build/cp312-fresh
python -m pip install -e . \
  -Ccmake.define.UNILINK_CORE_SOURCE_DIR=/d/GitHub/unilink-lab/unilink \
  -Ccmake.define.CMAKE_TOOLCHAIN_FILE=C:/Users/jwsun/vcpkg/scripts/buildsystems/vcpkg.cmake \
  -Ccmake.define.VCPKG_MANIFEST_MODE=OFF \
  -Cbuild-dir=build/cp312-fresh \
  --no-build-isolation
```

This is a full native rebuild (compiles the `unilink` C++ core + pybind11
bindings) - takes several minutes.

## Build

The viewer spawns `packet-probe.exe`, so it must be built first:

```bash
cmake --build build --config Debug --target packet-probe
```

**Then copy the runtime DLL next to the exe** (see Gotchas - this is not done
automatically):

```bash
cp build/bin/unilink.dll build/Debug/unilink.dll
```

## Run (agent path)

```bash
python .claude/skills/run-packet-probe-viewer/driver.py screenshot
python .claude/skills/run-packet-probe-viewer/driver.py udp-capture
```

Run from the repo root. Screenshots land in
`.claude/skills/run-packet-probe-viewer/` by default (override with
`--out-dir`). Exit code 0 = pass, 1 = fail; failure output includes the
Process Log tab contents.

| scenario | what it does |
|---|---|
| `screenshot` | Launches `MainWindow`, waits for layout, saves `screenshot.png` of the idle window. |
| `udp-capture` | Launches `MainWindow`, sets UDP mode / `127.0.0.1` / `--port` (default `19126`), clicks **Start Capture**, waits for `engine_state == "capturing"`, sends one test UDP datagram, waits for a `raw_bytes` row in the event table, clicks **Stop Capture**. Saves `01_before_start.png` / `02_after_capturing.png` / `03_after_event.png`. Fails (exit 1) if capture never starts or no event arrives. |

Useful driver internals for writing new scenarios (see `driver.py`):
`make_window()` returns `(app, window)`; `pump(app, seconds)` runs the Qt
event loop long enough for cross-thread signals (IPC worker, QProcess) to be
delivered; `shutdown(app, window)` stops capture and force-exits cleanly.
Key widgets: `cli_path_edit`, `mode_combo`, `udp_bind_host`/`udp_bind_port`/
`udp_target_host`/`udp_target_port`, `start_capture_btn`/`stop_capture_btn`,
`table_model` (rows: col 4 is event `type`, e.g. `raw_bytes`/`frame`/`state_change`),
`_engine_state`/`_ipc_connected`, `process_output` (Process Log text).

## Run (human path)

```bash
cd viewer
python run_viewer.py
```

Opens the window normally; use the UI's Start Capture button. Useless in a
headless/no-display context - use the driver instead.

## Test

```bash
cd viewer
python -m pytest -q
```

44 passed as of this writing (no live IPC/process involved - pure widget/unit tests).

## Gotchas

- **CLI auto-detect misses MSVC builds** - `find_packet_probe_binary()` in
  `main_window.py` used to only check `build/packet-probe` (no `.exe`, no
  per-config subdir), which only matches single-config generators (Linux
  Makefiles/Ninja). MSVC is multi-config: the real binary is
  `build/Debug/packet-probe.exe`. Already fixed in this repo (commit
  `8004f5e`) to check `Debug/Release/RelWithDebInfo/MinSizeRel` with `.exe`.
- **`unilink.dll` is not copied next to `packet-probe.exe` automatically** -
  it's a FetchContent'd subproject target, not a vcpkg package, so
  `VCPKG_APPLOCAL_DEPS` (which is ON in this repo) doesn't apply-local-copy
  it. Without the manual `cp` in Build, the exe fails immediately with
  `error while loading shared libraries: unilink.dll`.
- **A stale `packet-probe.exe` silently lacks newer CLI modes** - an old
  Debug build ran fine but its `--help` had no `engine` mode at all (it
  predated that feature). If `packet-probe engine --ipc ...` says `unknown
  or missing mode: engine`, rebuild (see Build).
- **UDP "Target Host"/"Target Port" default to `127.0.0.1`/`19085`, not
  empty** - a non-empty target `connect()`s the UDP socket to that one peer,
  so datagrams from any other source (e.g. a throwaway ephemeral-port test
  socket) are silently dropped with no error anywhere. For a receive-any-source
  capture (matching `docs/validation/viewer-ipc.md`'s CLI-only flow), clear
  both fields - `driver.py`'s `udp-capture` scenario does this.
- **`unilink` (Python bindings) version drift is invisible** - `pip show
  unilink` can report a version/build that predates recent fixes in the
  sibling `unilink` C++ core, with no automatic check tying them together.
  If IPC connects but behaves oddly (or doesn't connect at all against a
  freshly-rebuilt `packet-probe.exe`), compare
  `python -c "import unilink,os;print(os.path.getmtime(unilink._core.__file__))"`
  against the core repo's `git log -1 --format=%cd`, and rebuild per Setup if
  the extension predates relevant core commits.
- **git-bash silently reinterprets POSIX paths only in argv, not in embedded
  strings** - if you hand-write a quick repro script that launches
  `packet-probe.exe` as a background job (its `/tmp/x.sock` argv gets
  MSYS-translated to a Windows path) and a separate Python `-c "..."` client
  using the same literal `/tmp/x.sock` string (which does *not* get
  translated inside a quoted script), the two processes silently target
  different files and the connection just times out - not a Windows AF_UNIX
  bug. `driver.py` never hits this because Python computes real paths, not
  POSIX literals passed through a shell.

## Troubleshooting

- **`error while loading shared libraries: unilink.dll`**: DLL not next to
  the exe. `cp build/bin/unilink.dll build/Debug/unilink.dll`.
- **`packet-probe: unknown or missing mode: engine`**: stale build.
  `cmake --build build --config Debug --target packet-probe`.
- **CMake: `Could NOT find Boost (missing: Boost_INCLUDE_DIR system)`** while
  building `unilink-python`: missing `-Ccmake.define.CMAKE_TOOLCHAIN_FILE=<vcpkg>/scripts/buildsystems/vcpkg.cmake`.
- **CMake/vcpkg: `<vcpkg-root>\ports\jwsung91-unilink: error: jwsung91-unilink does not exist`**:
  `unilink-python`'s `vcpkg.json` manifest references a private port/registry
  not configured locally; build in classic mode instead:
  `-Ccmake.define.VCPKG_MANIFEST_MODE=OFF`.
- **`driver.py udp-capture` reaches `capturing` but reports "no raw_bytes
  event"**: almost always the Target Host/Port gotcha above - confirm they're
  empty, not their form defaults.
