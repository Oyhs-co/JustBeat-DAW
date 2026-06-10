import unittest
from src.application.services.transport_service import TransportService, TransportState


class TestTransportService(unittest.TestCase):
    def setUp(self):
        self.service = TransportService(sample_rate=44100, ticks_per_beat=480)

    def test_initial_state(self):
        self.assertEqual(self.service.state, TransportState.STOPPED)
        self.assertEqual(self.service.bpm, 120)
        self.assertEqual(self.service.position, 0)
        self.assertFalse(self.service.is_playing)
        self.assertFalse(self.service.is_recording)

    def test_play(self):
        self.service.play()
        self.assertTrue(self.service.is_playing)
        self.assertEqual(self.service.state, TransportState.PLAYING)

    def test_pause(self):
        self.service.play()
        self.service.pause()
        self.assertEqual(self.service.state, TransportState.PAUSED)

    def test_stop(self):
        self.service.play()
        self.service.stop()
        self.assertEqual(self.service.state, TransportState.STOPPED)
        self.assertEqual(self.service.position, 0)

    def test_record(self):
        self.service.record()
        self.assertTrue(self.service.is_recording)
        self.assertEqual(self.service.state, TransportState.RECORDING)

    def test_set_bpm(self):
        self.service.set_bpm(140)
        self.assertEqual(self.service.bpm, 140)

    def test_seek(self):
        self.service.seek(960)
        self.assertEqual(self.service.position, 960)

    def test_position_callback(self):
        positions = []
        self.service.set_position_callback(lambda p: positions.append(p))
        self.service.seek(480)
        self.assertIn(480, positions)

    def test_state_callback(self):
        states = []
        self.service.set_state_callback(lambda s: states.append(s))
        self.service.play()
        self.assertIn(TransportState.PLAYING, states)

    def test_bpm_callback(self):
        bpms = []
        self.service.set_bpm_callback(lambda b: bpms.append(b))
        self.service.set_bpm(160)
        self.assertIn(160, bpms)
