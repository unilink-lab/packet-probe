from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QFont

def format_hex_dump(hex_str: str) -> str:
    if not hex_str:
        return ""
    _HEX_CHARS = set("0123456789abcdefABCDEF")
    
    # Check for invalid characters (excluding common delimiters/whitespaces)
    allowed_delimiters = set(" \t\n\r:-")
    for c in hex_str:
        if c not in _HEX_CHARS and c not in allowed_delimiters:
            return f"Invalid hex payload: contains invalid character '{c}'"

    clean_hex = "".join(c for c in hex_str if c in _HEX_CHARS)
    if not clean_hex:
        if not hex_str.strip():
            return ""
        return "Invalid hex payload: no hex characters"

    if len(clean_hex) % 2 != 0:
        return f"Invalid hex payload length: {len(clean_hex)}"
    bytes_list = [clean_hex[i:i+2] for i in range(0, len(clean_hex), 2)]
    
    lines = []
    for offset in range(0, len(bytes_list), 16):
        chunk = bytes_list[offset:offset+16]
        hex_part = " ".join(chunk)
        line = f"{offset:04x}  {hex_part}"
        lines.append(line)
    return "\n".join(lines)

class HexView(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        font = QFont("Courier New", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setPlaceholderText("Hex View")

    def set_payload_hex(self, payload_hex: str) -> None:
        if not payload_hex:
            self.clear()
            return

        formatted = format_hex_dump(payload_hex)
        self.setPlainText(formatted)
