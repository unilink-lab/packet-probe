from collections import deque
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRect, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyle, QStyledItemDelegate
from .event_model import PacketEvent, format_time_ns

# Per-type text colors and TX/RX direction colors from the "Packet Probe
# Viewer" design mock (sRGB of its oklch values).
TYPE_COLORS = {
    "raw_bytes": "#88909c",
    "frame": "#1ad1d1",
    "latency": "#e3ae28",
    "error": "#f75d59",
    "state_change": "#b386e4",
}
TX_COLOR = "#52a9fe"  # app_to_device
RX_COLOR = "#4acaad"  # device_to_app


class DirectionChipDelegate(QStyledItemDelegate):
    """Renders the Direction column as a filled, rounded chip badge (App → Dev /
    Dev → App), matching the design mock."""

    def paint(self, painter, option, index):
        text = index.data() or ""
        if "APP -> DEVICE" in text:
            color, label = QColor(TX_COLOR), "App → Dev"
        elif "DEVICE -> APP" in text:
            color, label = QColor(RX_COLOR), "Dev → App"
        else:
            super().paint(painter, option, index)
            return

        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        painter.setFont(option.font)
        fm = painter.fontMetrics()
        chip_w = min(fm.horizontalAdvance(label) + 16, option.rect.width() - 12)
        chip = QRect(option.rect.left() + 8, option.rect.center().y() - 9, chip_w, 18)

        bg = QColor(color)
        bg.setAlpha(48)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)
        painter.drawRoundedRect(chip, 4, 4)

        painter.setPen(color)
        painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()

class PacketTableModel(QAbstractTableModel):
    MAX_EVENTS = 100_000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.events: deque[PacketEvent] = deque()
        self.parent_child_counts: dict[int, int] = {}
        self.headers = ["Seq", "Parent Seq(s)", "Time", "Direction", "Type", "Transport", "Size", "Summary"]

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.events)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.ForegroundRole:
            # The Direction column (3) is painted as a chip by
            # DirectionChipDelegate; the Type column (4) is colored per event
            # type. Other columns keep the default foreground.
            if index.column() == 4:
                event = self.events[index.row()]
                return QColor(TYPE_COLORS.get(event.type, "#88909c"))
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            event = self.events[index.row()]
            col = index.column()
            if col == 0:
                return getattr(event, "_display_seq", str(event.seq))
            elif col == 1:
                return ", ".join(map(str, event.parent_seqs)) if event.parent_seqs else "-"
            elif col == 2:
                return format_time_ns(event.time_ns)
            elif col == 3:
                direction = event.direction
                if direction == "device_to_app":
                    return "DEVICE -> APP"
                elif direction == "app_to_device":
                    return "APP -> DEVICE"
                return direction
            elif col == 4:
                return event.type
            elif col == 5:
                return event.transport
            elif col == 6:
                return event.size
            elif col == 7:
                return event.summary

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def append_event(self, event: PacketEvent):
        if len(self.events) >= self.MAX_EVENTS:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            self.events.popleft()
            self.endRemoveRows()

        # Option 2: Format derived events as virtual sequences in GUI (e.g. 66.1)
        # by tracking child event indices per parent raw packet sequence.
        p = event.parent_seqs[0] if event.parent_seqs else event.parent_seq
        if p:
            self.parent_child_counts[p] = self.parent_child_counts.get(p, 0) + 1
            event._display_seq = f"{p}.{self.parent_child_counts[p]}"
        else:
            event._display_seq = str(event.seq)

        row = len(self.events)
        self.beginInsertRows(QModelIndex(), row, row)
        self.events.append(event)
        self.endInsertRows()

    def set_events(self, events: list[PacketEvent]) -> None:
        self.beginResetModel()
        if len(events) > self.MAX_EVENTS:
            events = events[-self.MAX_EVENTS:]

        self.parent_child_counts.clear()
        for event in events:
            p = event.parent_seqs[0] if event.parent_seqs else event.parent_seq
            if p:
                self.parent_child_counts[p] = self.parent_child_counts.get(p, 0) + 1
                event._display_seq = f"{p}.{self.parent_child_counts[p]}"
            else:
                event._display_seq = str(event.seq)

        self.events = deque(events)
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self.events = deque()
        self.parent_child_counts.clear()
        self.endResetModel()

    def event_at(self, row: int) -> PacketEvent | None:
        if 0 <= row < len(self.events):
            return self.events[row]
        return None


class PacketFilterProxyModel(QSortFilterProxyModel):
    """Filters a PacketTableModel by direction, event type, and free-text search
    over the summary/hex payload. Values of "all"/"" disable that filter axis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._direction = "all"
        self._event_type = "all"
        self._text = ""
        self.setDynamicSortFilter(True)

    def set_direction_filter(self, direction: str) -> None:
        self._direction = direction
        self.invalidate()

    def set_type_filter(self, event_type: str) -> None:
        self._event_type = event_type
        self.invalidate()

    def set_text_filter(self, text: str) -> None:
        self._text = text.strip().lower()
        self.invalidate()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        event = model.event_at(source_row) if model else None
        if event is None:
            return False
        if self._direction != "all" and event.direction != self._direction:
            return False
        if self._event_type != "all" and event.type != self._event_type:
            return False
        if self._text and self._text not in f"{event.summary} {event.payload_hex}".lower():
            return False
        return True
