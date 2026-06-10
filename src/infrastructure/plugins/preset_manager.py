"""Preset Manager - Save and load synthesizer and effect presets.

This module provides:
- Preset: Individual preset data
- PresetBank: Collection of presets
- PresetManager: Load/save/manage presets
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PresetCategory(Enum):
    """Categories for presets."""
    SYNTH = "synth"
    EFFECT = "effect"
    DRUM = "drum"
    LEAD = "lead"
    BASS = "bass"
    PAD = "pad"
    PLUCK = "pluck"
    FX = "fx"
    USER = "user"


@dataclass
class Preset:
    """A single preset.
    
    Attributes:
        id: Unique identifier
        name: Preset name
        category: Preset category
        author: Preset author
        description: Description of the preset
        parameters: Dictionary of parameter name -> value
        tags: List of tags for search
    """
    
    id: str = ""
    name: str = ""
    category: PresetCategory = PresetCategory.USER
    author: str = "User"
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert preset to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "author": self.author,
            "description": self.description,
            "parameters": self.parameters,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Preset":
        """Create preset from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            category=PresetCategory(data.get("category", "user")),
            author=data.get("author", "User"),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            tags=data.get("tags", []),
        )


@dataclass
class PresetBank:
    """A bank containing multiple presets.
    
    Attributes:
        id: Bank identifier
        name: Bank name
        description: Bank description
        presets: List of presets in the bank
    """
    
    id: str = ""
    name: str = ""
    description: str = ""
    presets: List[Preset] = field(default_factory=list)
    
    def add_preset(self, preset: Preset) -> None:
        """Add a preset to the bank."""
        self.presets.append(preset)
    
    def remove_preset(self, preset_id: str) -> bool:
        """Remove a preset by ID."""
        for i, p in enumerate(self.presets):
            if p.id == preset_id:
                self.presets.pop(i)
                return True
        return False
    
    def get_preset(self, preset_id: str) -> Optional[Preset]:
        """Get a preset by ID."""
        for p in self.presets:
            if p.id == preset_id:
                return p
        return None
    
    def get_presets_by_category(self, category: PresetCategory) -> List[Preset]:
        """Get all presets in a category."""
        return [p for p in self.presets if p.category == category]
    
    def to_dict(self) -> dict:
        """Convert bank to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "presets": [p.to_dict() for p in self.presets],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PresetBank":
        """Create bank from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            presets=[Preset.from_dict(p) for p in data.get("presets", [])],
        )


class PresetManager:
    """Manager for loading, saving, and organizing presets."""
    
    def __init__(self, presets_dir: Optional[Path] = None):
        """Initialize the preset manager.
        
        Args:
            presets_dir: Directory for storing presets
        """
        self._presets_dir = presets_dir
        self._banks: Dict[str, PresetBank] = {}
        self._current_bank: Optional[PresetBank] = None
        
        if presets_dir:
            presets_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PresetManager initialized with dir: {presets_dir}")
    
    def set_presets_directory(self, directory: Path) -> None:
        """Set the presets directory."""
        self._presets_dir = directory
        directory.mkdir(parents=True, exist_ok=True)
    
    def create_bank(
        self, bank_id: str, name: str, description: str = ""
    ) -> PresetBank:
        """Create a new preset bank.
        
        Args:
            bank_id: Unique bank identifier
            name: Bank name
            description: Bank description
            
        Returns:
            The created bank
        """
        bank = PresetBank(id=bank_id, name=name, description=description)
        self._banks[bank_id] = bank
        return bank
    
    def get_bank(self, bank_id: str) -> Optional[PresetBank]:
        """Get a bank by ID."""
        return self._banks.get(bank_id)
    
    def get_all_banks(self) -> List[PresetBank]:
        """Get all banks."""
        return list(self._banks.values())
    
    def delete_bank(self, bank_id: str) -> bool:
        """Delete a bank."""
        if bank_id in self._banks:
            del self._banks[bank_id]
            return True
        return False
    
    def save_bank(self, bank: PresetBank, filepath: Optional[Path] = None) -> bool:
        """Save a bank to file.
        
        Args:
            bank: Bank to save
            filepath: Optional custom filepath
            
        Returns:
            True if successful
        """
        if filepath is None:
            if self._presets_dir is None:
                logger.error("No presets directory configured")
                return False
            filepath = self._presets_dir / f"{bank.id}.json"
        
        try:
            with open(filepath, "w") as f:
                json.dump(bank.to_dict(), f, indent=2)
            logger.info(f"Saved bank to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save bank: {e}")
            return False
    
    def load_bank(self, filepath: Path) -> Optional[PresetBank]:
        """Load a bank from file.
        
        Args:
            filepath: Path to bank file
            
        Returns:
            Loaded bank or None
        """
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            bank = PresetBank.from_dict(data)
            self._banks[bank.id] = bank
            
            logger.info(f"Loaded bank: {bank.name}")
            return bank
        except Exception as e:
            logger.error(f"Failed to load bank: {e}")
            return None
    
    def save_preset(
        self, preset: Preset, bank_id: str, filepath: Optional[Path] = None
    ) -> bool:
        """Save a single preset.
        
        Args:
            preset: Preset to save
            bank_id: Bank ID
            filepath: Optional custom filepath
            
        Returns:
            True if successful
        """
        # Get or create bank
        if bank_id not in self._banks:
            self.create_bank(bank_id, bank_id)
        
        bank = self._banks[bank_id]
        bank.add_preset(preset)
        
        return self.save_bank(bank, filepath)
    
    def delete_preset(self, bank_id: str, preset_id: str) -> bool:
        """Delete a preset from a bank.
        
        Args:
            bank_id: Bank ID
            preset_id: Preset ID
            
        Returns:
            True if successful
        """
        bank = self._banks.get(bank_id)
        if bank:
            return bank.remove_preset(preset_id)
        return False
    
    def search_presets(
        self, query: str, category: Optional[PresetCategory] = None
    ) -> List[Preset]:
        """Search presets by name, tags, or description.
        
        Args:
            query: Search query
            category: Optional category filter
            
        Returns:
            List of matching presets
        """
        query = query.lower()
        results = []
        
        for bank in self._banks.values():
            for preset in bank.presets:
                # Check category
                if category and preset.category != category:
                    continue
                
                # Check name, description, or tags
                if (query in preset.name.lower() or
                    query in preset.description.lower() or
                    any(query in tag.lower() for tag in preset.tags)):
                    results.append(preset)
        
        return results
    
    def get_default_presets(self) -> Dict[str, Preset]:
        """Get default built-in presets.
        
        Returns:
            Dictionary of preset_id -> Preset
        """
        return {
            "init_synth": Preset(
                id="init_synth",
                name="Init Synth",
                category=PresetCategory.SYNTH,
                description="Default synthesizer initialization",
                parameters={
                    "oscillator": "saw",
                    "attack": 0.01,
                    "decay": 0.2,
                    "sustain": 0.7,
                    "release": 0.3,
                    "filter_cutoff": 0.8,
                    "filter_resonance": 0.0,
                },
                tags=["init", "default", "basic"],
            ),
            "pluck": Preset(
                id="pluck",
                name="Pluck",
                category=PresetCategory.PLUCK,
                description="Short plucked sound",
                parameters={
                    "oscillator": "triangle",
                    "attack": 0.001,
                    "decay": 0.3,
                    "sustain": 0.0,
                    "release": 0.2,
                    "filter_cutoff": 0.9,
                    "filter_resonance": 0.3,
                },
                tags=["pluck", "short", "harp"],
            ),
            "bass": Preset(
                id="bass",
                name="Deep Bass",
                category=PresetCategory.BASS,
                description="Deep sub bass",
                parameters={
                    "oscillator": "sine",
                    "attack": 0.01,
                    "decay": 0.1,
                    "sustain": 0.8,
                    "release": 0.2,
                    "filter_cutoff": 0.3,
                    "filter_resonance": 0.0,
                },
                tags=["bass", "sub", "deep"],
            ),
            "pad": Preset(
                id="pad",
                name="Warm Pad",
                category=PresetCategory.PAD,
                description="Warm evolving pad",
                parameters={
                    "oscillator": "saw",
                    "attack": 0.5,
                    "decay": 0.3,
                    "sustain": 0.8,
                    "release": 1.0,
                    "filter_cutoff": 0.6,
                    "filter_resonance": 0.2,
                },
                tags=["pad", "warm", "ambient", "slow"],
            ),
            "lead": Preset(
                id="lead",
                name="Bright Lead",
                category=PresetCategory.LEAD,
                description="Bright synthesizer lead",
                parameters={
                    "oscillator": "square",
                    "attack": 0.01,
                    "decay": 0.1,
                    "sustain": 0.6,
                    "release": 0.3,
                    "filter_cutoff": 0.95,
                    "filter_resonance": 0.4,
                },
                tags=["lead", "bright", "synth"],
            ),
        }
