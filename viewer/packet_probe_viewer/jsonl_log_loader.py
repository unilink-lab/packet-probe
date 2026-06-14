import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class JsonlLoadResult:
    metadata: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    malformed_lines: list[tuple[int, str]] = field(default_factory=list)

def load_packet_probe_jsonl(path: str | Path) -> JsonlLoadResult:
    result = JsonlLoadResult()
    
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            
            try:
                obj = json.loads(line_str)
                if not isinstance(obj, dict):
                    result.malformed_lines.append((line_num, line_str))
                    continue
                
                if obj.get("type") == "metadata":
                    if result.metadata is None:
                        result.metadata = obj
                else:
                    result.events.append(obj)
            except json.JSONDecodeError:
                result.malformed_lines.append((line_num, line_str))
                
    return result
