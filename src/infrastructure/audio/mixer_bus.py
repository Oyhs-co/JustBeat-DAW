from typing import List
from dataclasses import dataclass, field


@dataclass
class Bus:
    id: str
    name: str
    channels: List[str] = field(default_factory=list)
    volume: float = 1.0
    effects: List[object] = field(default_factory=list)
