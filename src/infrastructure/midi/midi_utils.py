"""MIDI utilities for note and event conversions."""

# MIDI note to frequency
NOTE_TO_FREQ = {}
for note in range(128):
    NOTE_TO_FREQ[note] = 440.0 * (2.0 ** ((note - 69) / 12.0))


def midi_note_to_frequency(note: int) -> float:
    """Convert MIDI note number to frequency.
    
    Args:
        note: MIDI note number (0-127)
    
    Returns:
        Frequency in Hz
    """
    return NOTE_TO_FREQ.get(note, 440.0)


def frequency_to_midi_note(frequency: float) -> int:
    """Convert frequency to MIDI note number.
    
    Args:
        frequency: Frequency in Hz
    
    Returns:
        MIDI note number (0-127)
    """
    if frequency <= 0:
        return 60  # Default to middle C
    
    note = 69 + 12 * (frequency / 440.0)
    return max(0, min(127, round(note)))


# Note names
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_note_to_name(note: int) -> str:
    """Convert MIDI note number to note name.
    
    Args:
        note: MIDI note number (0-127)
    
    Returns:
        Note name (e.g., "C4", "F#3")
    """
    if note < 0 or note > 127:
        return "??"
    
    octave = (note // 12) - 1
    note_name = NOTE_NAMES[note % 12]
    return f"{note_name}{octave}"


def name_to_midi_note(name: str) -> int:
    """Convert note name to MIDI note number.
    
    Args:
        name: Note name (e.g., "C4", "F#3")
    
    Returns:
        MIDI note number (0-127)
    """
    # Parse note name
    name = name.strip().upper()
    
    # Handle flats
    name = name.replace('DB', 'C#').replace('EB', 'D#').replace('GB', 'F#')
    name = name.replace('AB', 'G#').replace('BB', 'A#')
    
    # Find note name
    note_num = -1
    for i, n in enumerate(NOTE_NAMES):
        if name.startswith(n):
            note_num = i
            name = name[len(n):]
            break
    
    if note_num < 0:
        return 60  # Default to middle C
    
    # Get octave
    try:
        octave = int(name)
    except ValueError:
        octave = 4  # Default to octave 4
    
    return (octave + 1) * 12 + note_num


# MIDI CC names
CC_NAMES = {
    0: "Bank Select",
    1: "Mod Wheel",
    2: "Breath",
    3: "Undefined",
    4: "Foot Controller",
    5: "Portamento Time",
    6: "Data Entry",
    7: "Volume",
    8: "Balance",
    9: "Undefined",
    10: "Pan",
    11: "Expression",
    12: "Effect 1",
    13: "Effect 2",
    14: "Undefined",
    15: "Undefined",
    16: "General Purpose 1",
    17: "General Purpose 2",
    18: "General Purpose 3",
    19: "General Purpose 4",
    20: "Undefined",
    21: "Undefined",
    22: "Undefined",
    23: "Undefined",
    24: "Undefined",
    25: "Undefined",
    26: "Undefined",
    27: "Undefined",
    28: "Undefined",
    29: "Undefined",
    30: "Undefined",
    31: "Undefined",
    64: "Sustain",
    65: "Portamento",
    66: "Sostenuto",
    67: "Soft Pedal",
    68: "Legato",
    69: "Hold 2",
    70: "Sound Controller 1",
    71: "Sound Controller 2",
    72: "Sound Controller 3",
    73: "Sound Controller 4",
    74: "Sound Controller 5",
    75: "Sound Controller 6",
    76: "Sound Controller 7",
    77: "Sound Controller 8",
    78: "Sound Controller 9",
    79: "Sound Controller 10",
    80: "General Purpose 5",
    81: "General Purpose 6",
    82: "General Purpose 7",
    83: "General Purpose 8",
    84: "Portamento Control",
    91: "Effect 1 Depth",
    92: "Effect 2 Depth",
    93: "Effect 3 Depth",
    94: "Effect 4 Depth",
    95: "Effect 5 Depth",
    96: "Data Increment",
    97: "Data Decrement",
    98: "NRPN LSB",
    99: "NRPN MSB",
    100: "RPN LSB",
    101: "RPN MSB",
}


def cc_number_to_name(cc: int) -> str:
    """Get MIDI CC name.
    
    Args:
        cc: CC number (0-127)
    
    Returns:
        CC name
    """
    return CC_NAMES.get(cc, f"CC{cc}")


# Scale definitions
SCALES = {
    'major': [0, 2, 4, 5, 7, 9, 11],
    'minor': [0, 2, 3, 5, 7, 8, 10],
    'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
    'melodic_minor': [0, 2, 3, 5, 7, 9, 11],
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'pentatonic_major': [0, 2, 4, 7, 9],
    'pentatonic_minor': [0, 3, 5, 7, 10],
    'blues': [0, 3, 5, 6, 7, 10],
    'chromatic': list(range(12)),
}


def get_scale_notes(root: int, scale_name: str) -> list[int]:
    """Get notes in a scale.
    
    Args:
        root: Root MIDI note
        scale_name: Scale name (e.g., "major", "minor")
    
    Returns:
        List of MIDI notes in the scale
    """
    if scale_name not in SCALES:
        scale_name = 'major'
    
    intervals = SCALES[scale_name]
    root_octave = root // 12
    root_note = root % 12
    
    notes = []
    for octave in range(8):
        for interval in intervals:
            note = root_note + interval + octave * 12
            if note <= 127:
                notes.append(note)
    
    return notes


def is_note_in_scale(note: int, root: int, scale_name: str) -> bool:
    """Check if a note is in a scale.
    
    Args:
        note: MIDI note to check
        root: Root MIDI note
        scale_name: Scale name
    
    Returns:
        True if note is in scale
    """
    scale_notes = get_scale_notes(root, scale_name)
    return note in scale_notes
