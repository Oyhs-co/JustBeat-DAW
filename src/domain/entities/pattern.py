"""Pattern entity - Represents a pattern in the step sequencer."""

from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class Pattern:
    """Pattern entity - represents a step sequencer pattern.
    
    Attributes:
        id: Unique identifier for the pattern
        name: Pattern name
        length: Number of steps in the pattern
        steps: List of step states (True = active, False = inactive)
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Pattern"
    length: int = 16
    steps: list[bool] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize steps if not provided."""
        if not self.steps:
            self.steps = [False] * self.length
    
    def __post_init__post_init__(self):
        """Validate pattern after initialization."""
        if self.length < 1 or self.length > 64:
            raise ValueError("Pattern length must be between 1 and 64")
        if len(self.steps) != self.length:
            # Adjust steps list to match length
            if len(self.steps) < self.length:
                self.steps.extend([False] * (self.length - len(self.steps)))
            else:
                self.steps = self.steps[:self.length]
    
    def toggle_step(self, index: int) -> None:
        """Toggle a step's active state.
        
        Args:
            index: Step index to toggle
            
        Raises:
            IndexError: If index is out of range
        """
        if 0 <= index < self.length:
            self.steps[index] = not self.steps[index]
        else:
            raise IndexError(f"Step index {index} out of range")
    
    def set_step(self, index: int, active: bool) -> None:
        """Set a step's active state.
        
        Args:
            index: Step index to set
            active: Whether the step should be active
            
        Raises:
            IndexError: If index is out of range
        """
        if 0 <= index < self.length:
            self.steps[index] = active
        else:
            raise IndexError(f"Step index {index} out of range")
    
    def set_note(self, index: int, note: "Note") -> None:
        """Set a note at a step position.
        
        For step sequencer patterns, this stores the MIDI note
        associated with a step.
        
        Args:
            index: Step index
            note: Note to store at this step
        """
        if not hasattr(self, 'notes'):
            self.notes = [None] * self.length
        
        if 0 <= index < self.length:
            if len(self.notes) < self.length:
                self.notes.extend([None] * (self.length - len(self.notes)))
            self.notes[index] = note
        else:
            raise IndexError(f"Step index {index} out of range")
    
    def get_note(self, index: int) -> "Note":
        """Get the note at a step position.
        
        Args:
            index: Step index
            
        Returns:
            Note at this step, or None
        """
        if not hasattr(self, 'notes') or self.notes is None:
            return None
        if 0 <= index < len(self.notes):
            return self.notes[index]
        return None
    
    def get_step(self, index: int) -> bool:
        """Get a step's active state.
        
        Args:
            index: Step index to get
            
        Returns:
            True if the step is active, False otherwise
            
        Raises:
            IndexError: If index is out of range
        """
        if 0 <= index < self.length:
            return self.steps[index]
        else:
            raise IndexError(f"Step index {index} out of range")
    
    def clear_all_steps(self) -> None:
        """Deactivate all steps in the pattern."""
        self.steps = [False] * self.length
    
    def set_length(self, length: int) -> None:
        """Change the pattern length.
        
        Args:
            length: New pattern length (1-64)
            
        Raises:
            ValueError: If length is out of valid range
        """
        if length < 1 or length > 64:
            raise ValueError("Pattern length must be between 1 and 64")
        self.length = length
        # Adjust steps list
        if len(self.steps) < length:
            self.steps.extend([False] * (length - len(self.steps)))
        else:
            self.steps = self.steps[:length]
    
    def to_dict(self) -> dict:
        """Convert pattern to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "length": self.length,
            "steps": self.steps,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        """Create pattern from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Pattern"),
            length=data.get("length", 16),
            steps=data.get("steps", []),
        )
