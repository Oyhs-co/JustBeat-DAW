"""MIDI event - Represents a MIDI event in the domain."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MIDIEventType(Enum):
    """Types of MIDI events."""
    NOTE_ON = "note_on"
    NOTE_OFF = "note_off"
    CONTROL_CHANGE = "control_change"
    PITCH_BEND = "pitch_bend"
    PROGRAM_CHANGE = "program_change"


@dataclass
class MIDIEvent:
    """MIDI event - represents a MIDI message.
    
    Attributes:
        event_type: Type of MIDI event
        channel: MIDI channel (0-15)
        data1: First data byte (note number, control number, etc.)
        data2: Second data byte (velocity, value, etc.)
        timestamp: Event timestamp
    """
    
    event_type: MIDIEventType
    channel: int
    data1: int
    data2: int
    timestamp: datetime = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # Validate channel
        if not 0 <= self.channel <= 15:
            raise ValueError("MIDI channel must be between 0 and 15")
        
        # Validate data bytes based on event type
        if self.event_type in (MIDIEventType.NOTE_ON, MIDIEventType.NOTE_OFF):
            if not 0 <= self.data1 <= 127:
                raise ValueError("Note number must be between 0 and 127")
            if not 0 <= self.data2 <= 127:
                raise ValueError("Velocity must be between 0 and 127")
        elif self.event_type == MIDIEventType.CONTROL_CHANGE:
            if not 0 <= self.data1 <= 127:
                raise ValueError("Control number must be between 0 and 127")
            if not 0 <= self.data2 <= 127:
                raise ValueError("Control value must be between 0 and 127")
        elif self.event_type == MIDIEventType.PITCH_BEND:
            if not 0 <= self.data1 <= 127:
                raise ValueError("Pitch bend LSB must be between 0 and 127")
            if not 0 <= self.data2 <= 127:
                raise ValueError("Pitch bend MSB must be between 0 and 127")
    
    @classmethod
    def note_on(cls, channel: int, note: int, velocity: int) -> "MIDIEvent":
        """Create a Note On event.
        
        Args:
            channel: MIDI channel (0-15)
            note: Note number (0-127)
            velocity: Velocity (0-127)
            
        Returns:
            New MIDIEvent instance
        """
        return cls(
            event_type=MIDIEventType.NOTE_ON,
            channel=channel,
            data1=note,
            data2=velocity,
        )
    
    @classmethod
    def note_off(cls, channel: int, note: int) -> "MIDIEvent":
        """Create a Note Off event.
        
        Args:
            channel: MIDI channel (0-15)
            note: Note number (0-127)
            
        Returns:
            New MIDIEvent instance
        """
        return cls(
            event_type=MIDIEventType.NOTE_OFF,
            channel=channel,
            data1=note,
            data2=0,
        )
    
    @classmethod
    def control_change(cls, channel: int, control: int, value: int) -> "MIDIEvent":
        """Create a Control Change event.
        
        Args:
            channel: MIDI channel (0-15)
            control: Control number (0-127)
            value: Control value (0-127)
            
        Returns:
            New MIDIEvent instance
        """
        return cls(
            event_type=MIDIEventType.CONTROL_CHANGE,
            channel=channel,
            data1=control,
            data2=value,
        )
    
    @classmethod
    def pitch_bend(cls, channel: int, value: int) -> "MIDIEvent":
        """Create a Pitch Bend event.
        
        Args:
            channel: MIDI channel (0-15)
            value: Pitch bend value (0-16383, center = 8192)
            
        Returns:
            New MIDIEvent instance
        """
        lsb = value & 0x7F
        msb = (value >> 7) & 0x7F
        return cls(
            event_type=MIDIEventType.PITCH_BEND,
            channel=channel,
            data1=lsb,
            data2=msb,
        )
    
    def to_bytes(self) -> bytes:
        """Convert event to MIDI bytes.
        
        Returns:
            MIDI message as bytes
        """
        status_byte = (self.event_type.value.index * 16) | self.channel
        
        if self.event_type == MIDIEventType.NOTE_ON:
            return bytes([status_byte, self.data1, self.data2])
        elif self.event_type == MIDIEventType.NOTE_OFF:
            return bytes([status_byte, self.data1, self.data2])
        elif self.event_type == MIDIEventType.CONTROL_CHANGE:
            return bytes([status_byte, self.data1, self.data2])
        elif self.event_type == MIDIEventType.PITCH_BEND:
            return bytes([status_byte, self.data1, self.data2])
        elif self.event_type == MIDIEventType.PROGRAM_CHANGE:
            return bytes([status_byte, self.data1])
        
        return bytes()
