# Third-Party Notices

The Packet Probe Viewer uses third-party runtime dependencies.

## PySide6 / Qt for Python

The optional viewer depends on PySide6 / Qt for Python.

PySide6 and Qt are not vendored in this repository. They are installed as external
runtime dependencies through Python packaging tools such as `pip`.

PySide6 and Qt are distributed under their respective license terms. Users and
redistributors are responsible for complying with those terms when packaging or
redistributing the viewer.

For source distributions from this repository, Packet Probe only includes viewer
source code and dependency declarations.

## wirestead-python

The viewer uses wirestead-python as its IPC transport dependency. wirestead-python
binds the wirestead C++ communication library and may include native extension
modules and runtime libraries in packaged distributions.

## Packaging note

If you build a standalone viewer binary or installer that bundles PySide6 or Qt
libraries, review and include the required third-party license notices for that
distribution format.
