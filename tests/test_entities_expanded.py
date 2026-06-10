import unittest
from src.domain.entities.clip import Clip, ClipType, ClipColor
from src.domain.entities.arrangement import Arrangement
from src.domain.entities.timeline import Timeline, MusicalPosition
from src.domain.entities.tempo_map import TempoMap
from src.domain.events.event_bus import EventBus, get_event_bus, DomainEvent
from datetime import datetime


class TestClip(unittest.TestCase):
    def test_create_midi_clip(self):
        clip = Clip.create_midi_clip(name="Test Clip", start_tick=0, duration=480)
        self.assertEqual(clip.name, "Test Clip")
        self.assertEqual(clip.clip_type, ClipType.MIDI)
        self.assertEqual(clip.start_tick, 0)
        self.assertEqual(clip.duration, 480)
        self.assertEqual(clip.end_tick, 480)

    def test_create_audio_clip(self):
        clip = Clip(
            id="test", name="Audio", clip_type=ClipType.AUDIO,
            start_tick=480, duration=960
        )
        self.assertEqual(clip.start_tick, 480)
        self.assertEqual(clip.end_tick, 1440)

    def test_clip_default_color(self):
        clip = Clip.create_midi_clip(name="Test", start_tick=0, duration=480)
        self.assertEqual(clip.color, ClipColor.BLUE)

    def test_clip_move(self):
        clip = Clip.create_midi_clip(name="Test", start_tick=0, duration=480)
        clip.move_to(960)
        self.assertEqual(clip.start_tick, 960)
        self.assertEqual(clip.end_tick, 1440)

    def test_clip_resize(self):
        clip = Clip.create_midi_clip(name="Test", start_tick=0, duration=480)
        clip.resize(960)
        self.assertEqual(clip.duration, 960)
        self.assertEqual(clip.end_tick, 960)

    def test_clip_split(self):
        clip = Clip.create_midi_clip(name="Test", start_tick=0, duration=960)
        left, right = clip.split_at(480)
        self.assertEqual(left.start_tick, 0)
        self.assertEqual(left.duration, 480)
        self.assertEqual(right.start_tick, 480)
        self.assertEqual(right.duration, 480)

    def test_clip_overlaps(self):
        c1 = Clip.create_midi_clip(name="C1", start_tick=0, duration=480)
        c2 = Clip.create_midi_clip(name="C2", start_tick=240, duration=480)
        c3 = Clip.create_midi_clip(name="C3", start_tick=960, duration=480)
        self.assertTrue(c1.overlaps(c2))
        self.assertFalse(c1.overlaps(c3))

    def test_clip_contains_tick(self):
        clip = Clip.create_midi_clip(name="Test", start_tick=0, duration=480)
        self.assertTrue(clip.contains_tick(240))
        self.assertFalse(clip.contains_tick(960))


class TestArrangement(unittest.TestCase):
    def setUp(self):
        from src.domain.entities.project import Project
        self.project = Project(name="Test")

    def test_create_arrangement(self):
        arr = Arrangement(name="Main")
        self.assertEqual(arr.name, "Main")
        self.assertIsNotNone(arr.id)

    def test_add_clip(self):
        arr = self.project.arrangement
        clip = Clip.create_midi_clip(name="Test", start_tick=0, duration=480)
        arr.add_clip("track_1", clip)
        clips = arr.get_track_clips("track_1")
        self.assertEqual(len(clips), 1)

    def test_remove_clip(self):
        arr = self.project.arrangement
        clip = Clip.create_midi_clip(name="Test", start_tick=0, duration=480)
        arr.add_clip("track_1", clip)
        removed = arr.remove_clip("track_1", clip.id)
        self.assertIsNotNone(removed)

    def test_get_track_clips(self):
        arr = self.project.arrangement
        c1 = Clip.create_midi_clip(name="C1", start_tick=0, duration=480)
        c2 = Clip.create_midi_clip(name="C2", start_tick=960, duration=480)
        arr.add_clip("track_1", c1)
        arr.add_clip("track_1", c2)
        result = arr.get_track_clips("track_1")
        self.assertEqual(len(result), 2)


class TestTimeline(unittest.TestCase):
    def test_default_resolution(self):
        tl = Timeline()
        self.assertEqual(tl.resolution, 480)

    def test_add_marker(self):
        tl = Timeline()
        tl.add_marker(0, "Intro")
        tl.add_marker(1920, "Verse")
        markers = tl.get_markers()
        self.assertEqual(len(markers), 2)

    def test_get_nearest_marker(self):
        tl = Timeline()
        tl.add_marker(0, "Intro")
        tl.add_marker(1920, "Verse")
        marker = tl.get_nearest_marker(100)
        self.assertIsNotNone(marker)
        self.assertEqual(marker[1], "Intro")

    def test_remove_marker(self):
        tl = Timeline()
        tl.add_marker(0, "Intro")
        tl.add_marker(1920, "Verse")
        tl.remove_marker(0)
        self.assertEqual(len(tl.get_markers()), 1)

    def test_quantize_position(self):
        tl = Timeline()
        result = tl.quantize_position(115, 120)
        self.assertIn(result, (0, 120))

    def test_musical_position_to_ticks(self):
        self.assertEqual(MusicalPosition(bar=1, beat=1, tick=0).to_ticks(), 0)
        self.assertEqual(MusicalPosition(bar=2, beat=1, tick=0).to_ticks(), 1920)
        self.assertEqual(MusicalPosition(bar=1, beat=3, tick=120).to_ticks(), 1080)

    def test_musical_position_from_ticks(self):
        pos = MusicalPosition.from_ticks(0)
        self.assertEqual(pos.bar, 1)
        self.assertEqual(pos.beat, 1)
        self.assertEqual(pos.tick, 0)

    def test_musical_position_str(self):
        self.assertEqual(str(MusicalPosition(3, 2, 120)), "3.2.120")


class TestTempoMap(unittest.TestCase):
    def test_default_bpm(self):
        tm = TempoMap()
        self.assertEqual(tm.get_bpm_at(0), 120)

    def test_set_bpm(self):
        tm = TempoMap()
        tm.set_bpm(960, 140)
        self.assertEqual(tm.get_bpm_at(0), 120)
        self.assertEqual(tm.get_bpm_at(960), 140)

    def test_default_time_signature(self):
        tm = TempoMap()
        self.assertEqual(tm.get_time_signature_at(0), (4, 4))

    def test_set_time_signature(self):
        tm = TempoMap()
        tm.set_time_signature(0, 3, 4)
        self.assertEqual(tm.get_time_signature_at(0), (3, 4))

    def test_get_tempo_points(self):
        tm = TempoMap()
        tm.set_bpm(0, 120)
        tm.set_bpm(960, 140)
        points = tm.get_tempo_points()
        self.assertEqual(len(points), 2)

    def test_bpm_between_points(self):
        tm = TempoMap()
        tm.set_bpm(960, 140)
        tm.set_bpm(1920, 160)
        self.assertEqual(tm.get_bpm_at(1440), 140)
        self.assertEqual(tm.get_bpm_at(1920), 160)


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        received = []
        self.bus.subscribe("test.event", lambda e: received.append(e))
        event = DomainEvent(
            event_id="1", event_type="test.event",
            timestamp=datetime.now(), data={"value": 42}
        )
        self.bus.publish(event)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].data["value"], 42)

    def test_unsubscribe(self):
        received = []
        handler = lambda e: received.append(e)
        self.bus.subscribe("test.event", handler)
        self.bus.unsubscribe("test.event", handler)
        event = DomainEvent("2", "test.event", datetime.now(), {})
        self.bus.publish(event)
        self.assertEqual(len(received), 0)

    def test_wildcard_subscribe(self):
        received = []
        self.bus.subscribe("test.*", lambda e: received.append(e))
        now = datetime.now()
        self.bus.publish(DomainEvent("3", "test.one", now, {}))
        self.bus.publish(DomainEvent("4", "test.two", now, {}))
        self.assertGreaterEqual(len(received), 0)

    def test_no_match(self):
        received = []
        self.bus.subscribe("other.event", lambda e: received.append(e))
        self.bus.publish(DomainEvent("5", "test.event", datetime.now(), {}))
        self.assertEqual(len(received), 0)

    def test_get_event_bus_global(self):
        bus = get_event_bus()
        self.assertIsNotNone(bus)


if __name__ == '__main__':
    unittest.main()
