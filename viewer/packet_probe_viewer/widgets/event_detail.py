import json
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QFont
from ..event_model import PacketEvent

class EventDetailView(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        font = QFont("Courier New", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setPlaceholderText("Event Detail JSON")

    def set_event(self, event: PacketEvent | None) -> None:
        if not event:
            self.clear()
            return

        try:
            formatted = json.dumps(event.raw, indent=2, ensure_ascii=False)
            self.setPlainText(formatted)
        except Exception as e:
            self.setPlainText(f"Error formatting JSON: {e}")
