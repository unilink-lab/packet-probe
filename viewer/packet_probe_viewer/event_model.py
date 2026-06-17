from dataclasses import dataclass
from typing import Any
from datetime import datetime

@dataclass
class PacketEvent:
    raw: dict[str, Any]

    @property
    def seq(self) -> int:
        return self.raw.get("seq", 0)

    @property
    def parent_seq(self) -> int:
        return self.raw.get("parent_seq", 0)

    @property
    def parent_seqs(self) -> list[int]:
        val = self.raw.get("parent_seqs", [])
        if not val and self.parent_seq:
            return [self.parent_seq]
        return val

    @property
    def time_ns(self) -> int:
        return self.raw.get("time_ns", 0)

    @property
    def session(self) -> str:
        return self.raw.get("session", "")

    @property
    def transport(self) -> str:
        return self.raw.get("transport", "")

    @property
    def direction(self) -> str:
        return self.raw.get("direction", "")

    @property
    def type(self) -> str:
        return self.raw.get("type", "")

    @property
    def size(self) -> int:
        return self.raw.get("size", 0)

    @property
    def payload_hex(self) -> str:
        return self.raw.get("payload_hex", "")

    @property
    def summary(self) -> str:
        return self.raw.get("summary", "")

def format_time_ns(time_ns: int) -> str:
    if not time_ns:
        return "00:00:00.000000"
    dt = datetime.fromtimestamp(time_ns / 1e9)
    return dt.strftime("%H:%M:%S.%f")
