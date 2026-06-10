"""Unit tests for domain entities."""

import unittest
from src.domain.entities.project import Project
from src.domain.entities.track import Track
from src.domain.entities.pattern import Pattern
from src.domain.entities.note import Note


class TestProject(unittest.TestCase):
    """Tests for the Project entity."""
    
    def test_create_project(self):
        """Test creating a new project."""
        project = Project(name="Test Project")
        
        self.assertEqual(project.name, "Test Project")
        self.assertEqual(project.bpm, 120)
        self.assertEqual(project.time_signature, (4, 4))
    
    def test_set_bpm(self):
        """Test setting BPM."""
        project = Project()
        project.set_bpm(140)
        
        self.assertEqual(project.bpm, 140)
    
    def test_time_signature(self):
        """Test setting time signature."""
        project = Project()
        project.set_time_signature(3, 8)
        
        self.assertEqual(project.time_signature, (3, 8))
    
    def test_is_saved(self):
        """Test is_saved property."""
        project = Project()
        
        self.assertFalse(project.is_saved)
        
        # After setting file_path, should be saved
        from pathlib import Path
        project.file_path = Path("/test/path.jbp")
        
        self.assertTrue(project.is_saved)
    
    def test_display_name(self):
        """Test display_name property."""
        project = Project(name="Test Project")
        
        self.assertEqual(project.display_name, "Test Project *")
        
        from pathlib import Path
        project.file_path = Path("/test/path.jbp")
        
        self.assertEqual(project.display_name, "Test Project")


class TestTrack(unittest.TestCase):
    """Tests for the Track entity."""
    
    def test_create_track(self):
        """Test creating a new track."""
        track = Track(name="Test Track")
        
        self.assertEqual(track.name, "Test Track")
        self.assertEqual(track.volume, 1.0)
        self.assertEqual(track.pan, 0.0)
        self.assertFalse(track.muted)
        self.assertFalse(track.solo)
    
    def test_set_volume(self):
        """Test setting track volume."""
        track = Track()
        track.volume = 0.5
        
        self.assertEqual(track.volume, 0.5)
    
    def test_set_pan(self):
        """Test setting track pan."""
        track = Track()
        track.pan = -0.5
        
        self.assertEqual(track.pan, -0.5)
    
    def test_toggle_mute(self):
        """Test toggling mute."""
        track = Track()
        
        self.assertFalse(track.muted)
        track.muted = True
        self.assertTrue(track.muted)
        track.muted = False
        self.assertFalse(track.muted)
    
    def test_toggle_solo(self):
        """Test toggling solo."""
        track = Track()
        
        self.assertFalse(track.solo)
        track.solo = True
        self.assertTrue(track.solo)
        track.solo = False
        self.assertFalse(track.solo)


class TestPattern(unittest.TestCase):
    """Tests for the Pattern entity."""
    
    def test_create_pattern(self):
        """Test creating a new pattern."""
        pattern = Pattern(name="Test Pattern", length=16)
        
        self.assertEqual(pattern.name, "Test Pattern")
        self.assertEqual(pattern.length, 16)
    
    def test_toggle_step(self):
        """Test toggling a step."""
        pattern = Pattern(length=16)
        
        self.assertFalse(pattern.steps[0])
        pattern.toggle_step(0)
        self.assertTrue(pattern.steps[0])
        pattern.toggle_step(0)
        self.assertFalse(pattern.steps[0])
    
    def test_get_step(self):
        """Test getting a step."""
        pattern = Pattern(length=16)
        
        self.assertFalse(pattern.get_step(5))
    
    def test_set_step(self):
        """Test setting a step."""
        pattern = Pattern(length=16)
        
        pattern.set_step(5, True)
        self.assertTrue(pattern.get_step(5))
    
    def test_clear_all_steps(self):
        """Test clearing all steps."""
        pattern = Pattern(length=16)
        
        pattern.steps[0] = True
        pattern.steps[5] = True
        
        pattern.clear_all_steps()
        
        self.assertFalse(any(pattern.steps))
    
    def test_set_length(self):
        """Test changing pattern length."""
        pattern = Pattern(length=16)
        
        pattern.set_length(32)
        
        self.assertEqual(pattern.length, 32)
        self.assertEqual(len(pattern.steps), 32)


class TestNote(unittest.TestCase):
    """Tests for the Note entity."""
    
    def test_create_note(self):
        """Test creating a new note."""
        note = Note(pitch=60, velocity=100, duration=250)
        
        self.assertEqual(note.pitch, 60)
        self.assertEqual(note.velocity, 100)
        self.assertEqual(note.duration, 250)
    
    def test_note_name(self):
        """Test note name property."""
        # Middle C (MIDI 60)
        note = Note(pitch=60)
        
        self.assertEqual(note.note_name, "C4")
    
    def test_set_pitch(self):
        """Test setting note pitch."""
        note = Note(pitch=60)
        note.pitch = 72  # C5
        
        self.assertEqual(note.pitch, 72)
    
    def test_set_velocity(self):
        """Test setting note velocity."""
        note = Note(pitch=60, velocity=100)
        note.velocity = 50
        
        self.assertEqual(note.velocity, 50)
    
    def test_default_values(self):
        """Test note default values."""
        note = Note()
        
        self.assertEqual(note.pitch, 60)
        self.assertEqual(note.velocity, 100)
        self.assertEqual(note.duration, 100)
    
    def test_end_time(self):
        """Test end_time property."""
        note = Note(start_time=100, duration=50)
        
        self.assertEqual(note.end_time, 150)
    
    def test_transpose(self):
        """Test transposing a note."""
        note = Note(pitch=60)  # C4
        transposed = note.transpose(12)  # Up one octave
        
        self.assertEqual(transposed.pitch, 72)  # C5
    
    def test_from_note_name(self):
        """Test creating note from name."""
        note = Note.from_note_name("C4")
        
        self.assertEqual(note.pitch, 60)


if __name__ == '__main__':
    unittest.main()
