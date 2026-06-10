"""MIDI Learn - System for mapping MIDI controls to DAW parameters."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Any
import logging
import json
import uuid

logger = logging.getLogger(__name__)


class MIDIEventType(Enum):
    """Types of MIDI events."""
    NOTE_ON = "note_on"
    NOTE_OFF = "note_off"
    CONTROL_CHANGE = "cc"
    PROGRAM_CHANGE = "program"
    PITCH_BEND = "pitch_bend"
    AFTERTOUCH = "aftertouch"


class MIDILearnMode(Enum):
    """MIDI Learn operation modes."""
    INACTIVE = "inactive"  # Normal operation
    LEARNING = "learning"  # Waiting for MIDI input
    MAPPING = "mapping"    # Mapping to a specific parameter


@dataclass
class MIDIMapping:
    """A single MIDI to parameter mapping.
    
    Attributes:
        id: Unique identifier
        channel: MIDI channel (0-15, or -1 for any)
        cc_number: CC number (0-127) or note number
        event_type: Type of MIDI event
        parameter_id: ID of the parameter to control
        parameter_path: Full path to parameter (e.g., "track.0.volume")
        min_value: Minimum output value
        max_value: Maximum output value
        invert: Whether to invert the value
        label: Human-readable label for UI
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel: int = -1  # -1 means any channel
    cc_number: int = 0
    event_type: MIDIEventType = MIDIEventType.CONTROL_CHANGE
    parameter_id: str = ""
    parameter_path: str = ""
    min_value: float = 0.0
    max_value: float = 1.0
    invert: bool = False
    label: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "channel": self.channel,
            "cc_number": self.cc_number,
            "event_type": self.event_type.value,
            "parameter_id": self.parameter_id,
            "parameter_path": self.parameter_path,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "invert": self.invert,
            "label": self.label,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MIDIMapping":
        """Create mapping from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            channel=data.get("channel", -1),
            cc_number=data.get("cc_number", 0),
            event_type=MIDIEventType(data.get("event_type", "cc")),
            parameter_id=data.get("parameter_id", ""),
            parameter_path=data.get("parameter_path", ""),
            min_value=data.get("min_value", 0.0),
            max_value=data.get("max_value", 1.0),
            invert=data.get("invert", False),
            label=data.get("label", ""),
        )
    
    def map_value(self, midi_value: float) -> float:
        """Map MIDI value (0-127) to parameter value.
        
        Args:
            midi_value: Raw MIDI value (0-127)
            
        Returns:
            Mapped value (min_value to max_value)
        """
        # Normalize to 0-1
        normalized = midi_value / 127.0
        
        # Invert if needed
        if self.invert:
            normalized = 1.0 - normalized
        
        # Scale to range
        return self.min_value + (normalized * (self.max_value - self.min_value))
    
    def matches(self, channel: int, cc: int, event_type: MIDIEventType) -> bool:
        """Check if this mapping matches the given MIDI message.
        
        Args:
            channel: MIDI channel
            cc: CC number or note number
            event_type: Type of MIDI event
            
        Returns:
            True if matches
        """
        # Check event type
        if event_type != self.event_type:
            return False
        
        # Check channel (any channel is -1)
        if self.channel != -1 and channel != self.channel:
            return False
        
        # Check CC/note number
        if cc != self.cc_number:
            return False
        
        return True


class MIDILearnManager:
    """Manages MIDI Learn functionality.
    
    This class handles:
    - Storing MIDI mappings
    - Entering/leaving learn mode
    - Processing incoming MIDI messages
    - Notifying registered callbacks of parameter changes
    """
    
    def __init__(self) -> None:
        """Initialize the MIDI Learn manager."""
        self._mappings: Dict[str, MIDIMapping] = {}
        self._mode = MIDILearnMode.INACTIVE
        self._learn_callback: Optional[Callable] = None
        self._parameter_callbacks: Dict[str, List[Callable]] = {}
        self._pending_parameter: Optional[str] = None
        self._last_midi_values: Dict[int, float] = {}  # For relative controls
        
        logger.info("MIDILearnManager initialized")
    
    @property
    def mode(self) -> MIDILearnMode:
        """Get current MIDI learn mode."""
        return self._mode
    
    @property
    def mappings(self) -> List[MIDIMapping]:
        """Get all MIDI mappings."""
        return list(self._mappings.values())
    
    def start_learn(self, parameter_id: str = "", parameter_path: str = "") -> None:
        """Start MIDI learn mode.
        
        Args:
            parameter_id: ID of parameter to map (optional)
            parameter_path: Full path to parameter (optional)
        """
        self._mode = MIDILearnMode.LEARNING
        self._pending_parameter = parameter_id or parameter_path
        logger.info(f"MIDI Learn started for: {self._pending_parameter or 'any'}")
    
    def cancel_learn(self) -> None:
        """Cancel MIDI learn mode."""
        self._mode = MIDILearnMode.INACTIVE
        self._pending_parameter = None
        logger.info("MIDI Learn cancelled")
    
    def stop_learn(self) -> None:
        """Stop MIDI learn mode (alias for cancel)."""
        self.cancel_learn()
    
    def add_mapping(self, mapping: MIDIMapping) -> None:
        """Add a MIDI mapping.
        
        Args:
            mapping: The mapping to add
        """
        self._mappings[mapping.id] = mapping
        logger.info(f"Added MIDI mapping: {mapping.label or mapping.cc_number}")
    
    def remove_mapping(self, mapping_id: str) -> bool:
        """Remove a MIDI mapping.
        
        Args:
            mapping_id: ID of the mapping to remove
            
        Returns:
            True if mapping was removed
        """
        if mapping_id in self._mappings:
            del self._mappings[mapping_id]
            logger.info(f"Removed MIDI mapping: {mapping_id}")
            return True
        return False
    
    def get_mapping_for_parameter(self, parameter_id: str) -> Optional[MIDIMapping]:
        """Get the mapping for a specific parameter.
        
        Args:
            parameter_id: ID of the parameter
            
        Returns:
            The mapping, or None if not found
        """
        for mapping in self._mappings.values():
            if mapping.parameter_id == parameter_id:
                return mapping
        return None
    
    def process_midi(
        self, channel: int, cc: int, value: int, event_type: MIDIEventType
    ) -> Optional[float]:
        """Process an incoming MIDI message.
        
        Args:
            channel: MIDI channel (0-15)
            cc: CC number or note number
            value: MIDI value (0-127)
            event_type: Type of MIDI event
            
        Returns:
            The mapped value if a mapping exists, None otherwise
        """
        # If in learn mode, create new mapping
        if self._mode == MIDILearnMode.LEARNING:
            mapping = MIDIMapping(
                channel=channel,
                cc_number=cc,
                event_type=event_type,
                parameter_id=self._pending_parameter or f"param_{cc}",
                parameter_path=self._pending_parameter or "",
            )
            self.add_mapping(mapping)
            self.cancel_learn()
            
            # Return the mapped value
            return mapping.map_value(float(value))
        
        # Check for existing mapping
        for mapping in self._mappings.values():
            if mapping.matches(channel, cc, event_type):
                mapped_value = mapping.map_value(float(value))
                
                # Notify callbacks
                self._notify_parameter_change(mapping.parameter_id, mapped_value)
                
                return mapped_value
        
        return None
    
    def register_parameter_callback(
        self, parameter_id: str, callback: Callable[[float], None]
    ) -> None:
        """Register a callback for a parameter.
        
        Args:
            parameter_id: ID of the parameter
            callback: Function to call with new value
        """
        if parameter_id not in self._parameter_callbacks:
            self._parameter_callbacks[parameter_id] = []
        self._parameter_callbacks[parameter_id].append(callback)
    
    def unregister_parameter_callback(
        self, parameter_id: str, callback: Callable[[float], None]
    ) -> bool:
        """Unregister a parameter callback.
        
        Args:
            parameter_id: ID of the parameter
            callback: The callback to remove
            
        Returns:
            True if callback was found and removed
        """
        if parameter_id in self._parameter_callbacks:
            try:
                self._parameter_callbacks[parameter_id].remove(callback)
                return True
            except ValueError:
                pass
        return False
    
    def _notify_parameter_change(self, parameter_id: str, value: float) -> None:
        """Notify all callbacks of a parameter change.
        
        Args:
            parameter_id: ID of the parameter
            value: New value
        """
        if parameter_id in self._parameter_callbacks:
            for callback in self._parameter_callbacks[parameter_id]:
                try:
                    callback(value)
                except Exception as e:
                    logger.error(f"Error in MIDI callback: {e}")
    
    def clear_all_mappings(self) -> None:
        """Clear all MIDI mappings."""
        self._mappings.clear()
        logger.info("Cleared all MIDI mappings")
    
    def save_mappings(self, filepath: str) -> bool:
        """Save mappings to a JSON file.
        
        Args:
            filepath: Path to save to
            
        Returns:
            True if successful
        """
        try:
            data = {
                "mappings": [m.to_dict() for m in self._mappings.values()]
            }
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved MIDI mappings to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save MIDI mappings: {e}")
            return False
    
    def load_mappings(self, filepath: str) -> bool:
        """Load mappings from a JSON file.
        
        Args:
            filepath: Path to load from
            
        Returns:
            True if successful
        """
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            self._mappings.clear()
            for mapping_data in data.get("mappings", []):
                mapping = MIDIMapping.from_dict(mapping_data)
                self._mappings[mapping.id] = mapping
            
            logger.info(f"Loaded MIDI mappings from: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load MIDI mappings: {e}")
            return False
    
    def get_mapping_summary(self) -> List[dict]:
        """Get a summary of all mappings for UI display.
        
        Returns:
            List of mapping dictionaries
        """
        return [
            {
                "id": m.id,
                "label": m.label or f"CC {m.cc_number}",
                "channel": m.channel if m.channel >= 0 else "Any",
                "cc": m.cc_number,
                "parameter": m.parameter_id,
                "range": f"{m.min_value:.2f} - {m.max_value:.2f}",
                "invert": m.invert,
            }
            for m in self._mappings.values()
        ]
