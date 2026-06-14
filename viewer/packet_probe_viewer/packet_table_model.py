from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from .event_model import PacketEvent, format_time_ns

class PacketTableModel(QAbstractTableModel):
    MAX_EVENTS = 100_000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.events: list[PacketEvent] = []
        self.headers = ["Seq", "Time", "Direction", "Type", "Transport", "Size", "Summary"]

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.events)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            event = self.events[index.row()]
            col = index.column()
            if col == 0:
                return event.seq
            elif col == 1:
                return format_time_ns(event.time_ns)
            elif col == 2:
                direction = event.direction
                if direction == "device_to_app":
                    return "DEVICE -> APP"
                elif direction == "app_to_device":
                    return "APP -> DEVICE"
                return direction
            elif col == 3:
                return event.type
            elif col == 4:
                return event.transport
            elif col == 5:
                return event.size
            elif col == 6:
                return event.summary

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def append_event(self, event: PacketEvent):
        if len(self.events) >= self.MAX_EVENTS:
            self.beginRemoveRows(QModelIndex(), 0, 0)
            self.events.pop(0)
            self.endRemoveRows()

        row = len(self.events)
        self.beginInsertRows(QModelIndex(), row, row)
        self.events.append(event)
        self.endInsertRows()

    def set_events(self, events: list[PacketEvent]) -> None:
        self.beginResetModel()
        if len(events) > self.MAX_EVENTS:
            events = events[-self.MAX_EVENTS:]
        self.events = list(events)
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self.events.clear()
        self.endResetModel()

    def event_at(self, row: int) -> PacketEvent | None:
        if 0 <= row < len(self.events):
            return self.events[row]
        return None
