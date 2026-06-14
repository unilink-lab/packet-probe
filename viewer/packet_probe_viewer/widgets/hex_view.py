from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QFont

def format_hex_dump(hex_str: str) -> str:
    if not hex_str:
        return ""
    clean_hex = "".join(c for c in hex_str if c.isalnum())
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
