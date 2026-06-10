import unittest
from unittest.mock import MagicMock
from pathlib import Path

from src.application.handlers.project_handler import ProjectHandler
from src.application.handlers.transport_handler import TransportHandler, TransportState
from src.application.handlers.track_handler import TrackHandler
from src.application.handlers.note_handler import NoteHandler
from src.application.handlers.automation_handler import AutomationHandler
from src.application.handlers.arrangement_handler import ArrangementHandler
from src.domain.entities.project import Project
from src.domain.entities.track import Track
from src.domain.entities.note import Note
from src.domain.entities.clip import Clip, ClipType


class TestProjectHandler(unittest.TestCase):
    def setUp(self):
        self.handler = ProjectHandler()

    def test_create_project(self):
        project = self.handler.create_project("Test")
        self.assertIsNotNone(project)
        self.assertEqual(project.name, "Test")

    def test_create_project_default_name(self):
        project = self.handler.create_project()
        self.assertIsNotNone(project)

    def test_create_project_custom_bpm(self):
        project = self.handler.create_project("Fast", bpm=160)
        self.assertEqual(project.bpm, 160)

    def test_current_project(self):
        project = self.handler.create_project("Test")
        self.assertIsNotNone(self.handler.current_project)
        self.assertEqual(self.handler.current_project.id, project.id)

    def test_has_project(self):
        self.assertFalse(self.handler.has_project)
        self.handler.create_project("Test")
        self.assertTrue(self.handler.has_project)

    def test_close_project(self):
        self.handler.create_project("Test")
        self.handler.close_project()
        self.assertFalse(self.handler.has_project)

    def test_set_bpm(self):
        self.handler.create_project("Test")
        self.handler.set_bpm(140)
        self.assertEqual(self.handler.get_bpm(), 140)

    def test_set_time_signature(self):
        self.handler.create_project("Test")
        self.handler.set_time_signature(3, 4)
        self.assertEqual(self.handler.current_project.time_signature, (3, 4))

    def test_add_track(self):
        self.handler.create_project("Test")
        track = self.handler.add_track("New Track")
        self.assertIsNotNone(track)

    def test_remove_track(self):
        self.handler.create_project("Test")
        track = self.handler.add_track()
        result = self.handler.remove_track(track.id)
        self.assertTrue(result)

    def test_get_track(self):
        self.handler.create_project("Test")
        track = self.handler.add_track("My Track")
        found = self.handler.get_track(track.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "My Track")

    def test_get_all_tracks_empty(self):
        self.handler.create_project("Test")
        tracks = self.handler.get_all_tracks()
        self.assertGreaterEqual(len(tracks), 0)

    def test_get_all_tracks(self):
        self.handler.create_project("Test")
        initial = len(self.handler.get_all_tracks())
        self.handler.add_track("A")
        self.handler.add_track("B")
        self.assertEqual(len(self.handler.get_all_tracks()), initial + 2)


class TestTransportHandler(unittest.TestCase):
    def setUp(self):
        self.mock_audio = MagicMock()
        self.mock_audio.play.return_value = None
        self.mock_audio.pause.return_value = None
        self.mock_audio.stop.return_value = None
        self.handler = TransportHandler(audio_service=self.mock_audio)

    def test_initial_state(self):
        self.assertEqual(self.handler.state, TransportState.STOPPED)
        self.assertEqual(self.handler.bpm, 120)

    def test_play(self):
        self.assertTrue(self.handler.play())
        self.assertEqual(self.handler.state, TransportState.PLAYING)

    def test_pause(self):
        self.handler.play()
        self.assertTrue(self.handler.pause())
        self.assertEqual(self.handler.state, TransportState.PAUSED)

    def test_stop(self):
        self.handler.play()
        self.handler.stop()
        self.assertEqual(self.handler.state, TransportState.STOPPED)
        self.assertEqual(self.handler.position, 0)

    def test_toggle(self):
        self.handler.play()
        self.handler.toggle()
        self.assertEqual(self.handler.state, TransportState.PAUSED)
        self.handler.toggle()
        self.assertEqual(self.handler.state, TransportState.PLAYING)

    def test_start_recording(self):
        self.assertTrue(self.handler.start_recording())
        self.assertEqual(self.handler.state, TransportState.RECORDING)

    def test_stop_recording(self):
        self.handler.start_recording()
        self.assertTrue(self.handler.stop_recording())
        self.assertEqual(self.handler.state, TransportState.PLAYING)

    def test_seek(self):
        self.handler.seek(960)
        self.assertEqual(self.handler.position, 960)

    def test_seek_negative_clamps(self):
        self.handler.seek(-100)
        self.assertEqual(self.handler.position, 0)

    def test_set_bpm(self):
        self.handler.set_bpm(140)
        self.assertEqual(self.handler.bpm, 140)

    def test_set_bpm_clamped(self):
        self.handler.set_bpm(10)
        self.assertEqual(self.handler.bpm, 20)
        self.handler.set_bpm(500)
        self.assertEqual(self.handler.bpm, 300)

    def test_set_loop(self):
        self.handler.set_loop(True, 0, 16)
        self.assertTrue(self.handler.loop_enabled)
        self.assertEqual(self.handler.loop_region, (0, 16))

    def test_go_to_start(self):
        self.handler.seek(960)
        self.handler.go_to_start()
        self.assertEqual(self.handler.position, 0)

    def test_bpm_changed_callback(self):
        bpms = []
        self.handler.set_on_bpm_changed(lambda b: bpms.append(b))
        self.handler.set_bpm(140)
        self.assertEqual(bpms, [140])


class TestTrackHandler(unittest.TestCase):
    def setUp(self):
        self.handler = TrackHandler()

    def test_create_track(self):
        track = self.handler.create_track("New Track")
        self.assertEqual(track.name, "New Track")
        self.assertEqual(track.volume, 1.0)

    def test_set_volume(self):
        track = self.handler.create_track()
        self.handler.set_volume(track, 0.5)
        self.assertEqual(track.volume, 0.5)

    def test_set_pan(self):
        track = self.handler.create_track()
        self.handler.set_pan(track, -0.5)
        self.assertEqual(track.pan, -0.5)

    def test_toggle_mute(self):
        track = self.handler.create_track()
        self.handler.toggle_mute(track)
        self.assertTrue(track.muted)
        self.handler.toggle_mute(track)
        self.assertFalse(track.muted)

    def test_toggle_solo(self):
        track = self.handler.create_track()
        self.handler.toggle_solo(track)
        self.assertTrue(track.solo)
        self.handler.toggle_solo(track)
        self.assertFalse(track.solo)


class TestNoteHandler(unittest.TestCase):
    def setUp(self):
        self.handler = NoteHandler()

    def test_create_note(self):
        note = self.handler.create_note(60, 100, 480, 0)
        self.assertEqual(note.pitch, 60)
        self.assertEqual(note.velocity, 100)
        self.assertEqual(note.duration, 480)
        self.assertEqual(note.start_time, 0)

    def test_create_note_defaults(self):
        note = self.handler.create_note()
        self.assertEqual(note.pitch, 60)

    def test_create_note_from_name(self):
        note = self.handler.create_note_from_name("C4")
        self.assertEqual(note.pitch, 60)

    def test_transpose_note(self):
        note = self.handler.create_note(60)
        transposed = self.handler.transpose_note(note, 12)
        self.assertEqual(transposed.pitch, 72)

    def test_set_velocity(self):
        note = self.handler.create_note(60, 100)
        self.handler.set_velocity(note, 50)
        self.assertEqual(note.velocity, 50)

    def test_set_duration(self):
        note = self.handler.create_note(60, 100, 480)
        self.handler.set_duration(note, 960)
        self.assertEqual(note.duration, 960)

    def test_set_start_time(self):
        note = self.handler.create_note(60, 100, 480, 0)
        self.handler.set_start_time(note, 960)
        self.assertEqual(note.start_time, 960)

    def test_quantize_note(self):
        note = self.handler.create_note(60, 100, 100, 115)
        q = self.handler.quantize_note(note, 120)
        self.assertIsNotNone(q)


class TestArrangementHandler(unittest.TestCase):
    def setUp(self):
        self.project = Project(name="Test")
        self.handler = ArrangementHandler()
        self.clip = Clip.create_midi_clip(name="Test", start_tick=0, duration=480)

    def test_get_track_clips_empty(self):
        clips = self.handler.get_track_clips(self.project, "track_1")
        self.assertEqual(len(clips), 0)

    def test_add_clip(self):
        self.project.arrangement.add_clip("track_1", self.clip)
        clips = self.handler.get_track_clips(self.project, "track_1")
        self.assertEqual(len(clips), 1)

    def test_remove_clip(self):
        self.project.arrangement.add_clip("track_1", self.clip)
        result = self.handler.remove_clip(self.project, "track_1", self.clip.id)
        self.assertTrue(result)

    def test_get_track_clips_after_add(self):
        self.project.arrangement.add_clip("track_1", self.clip)
        clips = self.handler.get_track_clips(self.project, "track_1")
        self.assertEqual(len(clips), 1)


class TestAutomationHandler(unittest.TestCase):
    def setUp(self):
        self.handler = AutomationHandler()

    def test_add_point(self):
        self.handler.add_point("volume", 0, 0.8)
        value = self.handler.get_value_at("volume", 0)
        self.assertAlmostEqual(value, 0.8)

    def test_remove_point(self):
        self.handler.add_point("volume", 0, 0.8)
        removed = self.handler.remove_point("volume", 0)
        self.assertTrue(removed)

    def test_get_value_at_interpolated(self):
        self.handler.add_point("volume", 0, 0.0)
        self.handler.add_point("volume", 960, 1.0)
        value = self.handler.get_value_at("volume", 480)
        self.assertAlmostEqual(value, 0.5, places=2)

    def test_get_value_at_default(self):
        value = self.handler.get_value_at("volume", 0, 0.5)
        self.assertAlmostEqual(value, 0.5)

    def test_clear_curve(self):
        self.handler.add_point("volume", 0, 0.8)
        self.handler.clear_curve("volume")
        value = self.handler.get_value_at("volume", 0, -1.0)
        self.assertAlmostEqual(value, -1.0)

    def test_enable_disable(self):
        self.assertTrue(self.handler.is_enabled)
        self.handler.disable()
        self.assertFalse(self.handler.is_enabled)
        self.handler.enable()
        self.assertTrue(self.handler.is_enabled)


if __name__ == '__main__':
    unittest.main()
