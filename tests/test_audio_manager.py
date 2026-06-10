import unittest
from unittest.mock import MagicMock, patch
from src.infrastructure.audio.audio_manager import AudioManager


class TestAudioManager(unittest.TestCase):
    def setUp(self):
        self.manager = AudioManager(sample_rate=44100, buffer_size=512)

    def test_initial_state(self):
        self.assertFalse(self.manager.is_playing)
        self.assertFalse(self.manager.metronome_enabled)
        self.assertFalse(self.manager.loop_enabled)
        self.assertFalse(self.manager.count_in_enabled)
        self.assertEqual(self.manager.current_step, 0)

    def test_toggle_metronome(self):
        self.assertFalse(self.manager.metronome_enabled)
        result = self.manager.toggle_metronome()
        self.assertTrue(result)
        self.assertTrue(self.manager.metronome_enabled)
        result = self.manager.toggle_metronome()
        self.assertFalse(result)

    def test_toggle_loop(self):
        self.assertFalse(self.manager.loop_enabled)
        self.manager.toggle_loop()
        self.assertTrue(self.manager.loop_enabled)

    def test_toggle_count_in(self):
        self.assertFalse(self.manager.count_in_enabled)
        self.manager.toggle_count_in()
        self.assertTrue(self.manager.count_in_enabled)

    def test_register_track(self):
        self.manager.register_track("track_0", note=60, volume=0.8)
        data = self.manager.get_track_synth("track_0")
        self.assertEqual(data.get("note"), 60)
        self.assertEqual(data.get("volume"), 0.8)

    def test_unregister_track(self):
        self.manager.register_track("track_0")
        self.manager.unregister_track("track_0")
        data = self.manager.get_track_synth("track_0")
        self.assertEqual(data, {})

    def test_set_track_volume(self):
        self.manager.register_track("track_0", volume=0.8)
        self.manager.set_track_volume("track_0", 0.5)
        self.assertEqual(
            self.manager.get_track_synth("track_0").get("volume"), 0.5
        )

    def test_set_track_mute(self):
        self.manager.register_track("track_0", muted=False)
        self.manager.set_track_mute("track_0", True)
        self.assertTrue(self.manager.get_track_synth("track_0").get("muted"))

    def test_set_track_pan(self):
        self.manager.register_track("track_0")
        self.manager.set_track_pan("track_0", -0.5)
        self.assertEqual(
            self.manager.get_track_synth("track_0").get("pan"), -0.5
        )

    def test_set_track_note(self):
        self.manager.register_track("track_0", note=60)
        self.manager.set_track_note("track_0", 72)
        self.assertEqual(
            self.manager.get_track_synth("track_0").get("note"), 72
        )

    def test_set_num_steps(self):
        self.manager.set_num_steps(32)
        self.assertEqual(self.manager._num_steps, 32)

    def test_set_step_active(self):
        self.manager.set_step_active(0, 4, True)
        states = self.manager.get_step_states()
        self.assertIn(0, states)
        self.assertTrue(states[0][4])

    def test_get_step_states_empty(self):
        states = self.manager.get_step_states()
        self.assertEqual(states, {})

    def test_init_track_steps(self):
        self.manager.init_track_steps(0)
        states = self.manager.get_step_states()
        self.assertIn(0, states)

    def test_get_all_track_synths(self):
        self.manager.register_track("track_0", note=60)
        self.manager.register_track("track_1", note=72)
        all_synths = self.manager.get_all_track_synths()
        self.assertEqual(len(all_synths), 2)

    def test_set_bpm(self):
        self.manager.set_bpm(140)
        self.assertEqual(self.manager._bpm, 140)

    def test_set_bpm_clamped(self):
        self.manager.set_bpm(10)
        self.assertEqual(self.manager._bpm, 20)
        self.manager.set_bpm(500)
        self.assertEqual(self.manager._bpm, 300)

    def test_get_audio_levels_no_router(self):
        levels = self.manager.get_audio_levels()
        self.assertEqual(levels, (0.0, 0.0))

    def test_get_waveform_data_no_router(self):
        data = self.manager.get_waveform_data(256)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0], [0.0] * 256)
        self.assertEqual(data[1], [0.0] * 256)

    def test_shutdown(self):
        self.manager.register_track("track_0")
        self.manager.shutdown()
        self.assertFalse(self.manager.is_playing)

    def test_callbacks(self):
        tick_cb = MagicMock()
        step_cb = MagicMock()
        state_cb = MagicMock()
        self.manager.set_on_tick(tick_cb)
        self.manager.set_on_step(step_cb)
        self.manager.set_on_state_change(state_cb)
        self.assertIsNotNone(self.manager._on_tick_callback)
        self.assertIsNotNone(self.manager._on_step_callback)
        self.assertIsNotNone(self.manager._on_state_change)


if __name__ == '__main__':
    unittest.main()
