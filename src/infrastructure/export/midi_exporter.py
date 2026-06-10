"""MIDI exporter - Export MIDI data to standard MIDI files."""

import mido
from pathlib import Path
from typing import List, Dict, Any


class MIDIExporter:
    """Export MIDI data to standard MIDI files."""
    
    def __init__(self):
        """Initialize the MIDI exporter."""
        self._ticks_per_beat = 480
    
    def set_ticks_per_beat(self, ticks: int) -> None:
        """Set ticks per beat.
        
        Args:
            ticks: Ticks per beat
        """
        self._ticks_per_beat = ticks
    
    def export_notes(self, notes: List[Dict[str, Any]], 
                    output_path: Path,
                    track_name: str = "JustBeat-DAW") -> bool:
        """Export notes to MIDI file.
        
        Args:
            notes: List of note dictionaries with 'pitch', 'velocity', 
                   'start_time', 'duration'
            output_path: Output file path
            track_name: Track name
            
        Returns:
            True if export successful
        """
        try:
            mid = mido.MidiFile()
            track = mido.MidiTrack()
            
            # Set track name
            track.append(mido.MetaMessage(
                'track_name', 
                name=track_name, 
                time=0
            ))
            
            # Set tempo (default 120 BPM)
            tempo = mido.bpm2tempo(120)
            track.append(mido.MetaMessage('set_tempo', tempo=tempo, time=0))
            
            # Convert notes to MIDI events
            # Sort notes by start time
            sorted_notes = sorted(notes, key=lambda n: n.get('start_time', 0))
            
            last_time = 0
            
            for note_data in sorted_notes:
                pitch = note_data.get('pitch', 60)
                velocity = note_data.get('velocity', 100)
                start_time = note_data.get('start_time', 0)
                duration = note_data.get('duration', 100)
                
                # Calculate delta time in ticks
                delta_time = int(start_time - last_time)
                last_time = start_time
                
                # Note On
                track.append(mido.Message(
                    'note_on',
                    note=pitch,
                    velocity=velocity,
                    time=delta_time
                ))
                
                # Note Off (after duration)
                end_time = start_time + duration
                delta_off = int(end_time - last_time)
                last_time = end_time
                
                track.append(mido.Message(
                    'note_off',
                    note=pitch,
                    velocity=0,
                    time=delta_off
                ))
            
            # End of track
            track.append(mido.MetaMessage('end_of_track', time=0))
            
            mid.tracks.append(track)
            
            # Save to file
            mid.save(str(output_path))
            
            return True
        
        except Exception as e:
            print(f"Error exporting MIDI: {e}")
            return False
    
    def export_pattern(self, pattern_data: Dict[str, Any],
                      output_path: Path) -> bool:
        """Export pattern data to MIDI file.
        
        Args:
            pattern_data: Pattern data with 'notes' list
            output_path: Output file path
            
        Returns:
            True if export successful
        """
        notes = pattern_data.get('notes', [])
        track_name = pattern_data.get('name', 'Pattern')
        
        return self.export_notes(notes, output_path, track_name)
