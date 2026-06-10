from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ChannelState(Enum):
    PLAYING = "playing"
    MUTED = "muted"
    SOLO = "solo"
    BYPASSED = "bypassed"


@dataclass
class Send:
    id: str
    name: str
    target_bus: str
    amount: float = 0.0
    pre_fader: bool = False


@dataclass
class ChannelStrip:
    id: str
    name: str
    volume: float = 0.8
    pan: float = 0.0
    mute: bool = False
    solo: bool = False
    peak_left: float = 0.0
    peak_right: float = 0.0
    effects: List[object] = field(default_factory=list)
    sends: List[Send] = field(default_factory=list)
    solo_safe: bool = False
    mute_group: Optional[str] = None
    link_group: Optional[str] = None
    sidechain_source: Optional[str] = None

    def is_active(self) -> bool:
        return not self.mute and self.volume > 0
