import unittest
from pathlib import Path
import tempfile
import json
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)

from src.application.handlers.state_handler import StateHandler, CONFIG_DIR, STATE_FILE


class TestStateHandler(unittest.TestCase):
    def setUp(self):
        self._orig_config = CONFIG_DIR
        self._orig_state = STATE_FILE
        self._tmpdir = tempfile.mkdtemp()

        import src.application.handlers.state_handler as sh
        sh.CONFIG_DIR = Path(self._tmpdir)
        sh.STATE_FILE = sh.CONFIG_DIR / "state.json"

        StateHandler._instance = None
        self.handler = StateHandler()

    def tearDown(self):
        import src.application.handlers.state_handler as sh
        sh.CONFIG_DIR = self._orig_config
        sh.STATE_FILE = self._orig_state
        StateHandler._instance = None

    def test_singleton(self):
        h2 = StateHandler()
        self.assertIs(self.handler, h2)

    def test_set_and_get(self):
        self.handler.set("test.key", "value")
        self.assertEqual(self.handler.get("test.key"), "value")

    def test_get_default(self):
        self.assertIsNone(self.handler.get("nonexistent"))
        self.assertEqual(self.handler.get("nonexistent", 42), 42)

    def test_nested_key(self):
        self.handler.set("a.b.c", 123)
        self.assertEqual(self.handler.get("a.b.c"), 123)
        self.assertIsNone(self.handler.get("a.x"))

    def test_recent_files(self):
        self.handler.add_recent_file("/path/to/project.jbproj")
        recent = self.handler.get_recent_files()
        self.assertIn("project.jbproj", recent[0])

        self.handler.add_recent_file("/path/to/other.jbproj")
        recent = self.handler.get_recent_files()
        self.assertEqual(len(recent), 2)
        self.assertIn("other.jbproj", recent[0])

    def test_recent_files_dedup(self):
        self.handler.add_recent_file("/path/to/project.jbproj")
        self.handler.add_recent_file("/path/to/project.jbproj")
        recent = self.handler.get_recent_files()
        self.assertEqual(len(recent), 1)

    def test_remove_recent_file(self):
        self.handler.add_recent_file("/path/to/project.jbproj")
        self.handler.remove_recent_file("/path/to/project.jbproj")
        recent = self.handler.get_recent_files()
        self.assertEqual(len(recent), 0)

    def test_persistence(self):
        self.handler.set("theme.variant", "midnight")
        self.handler.set("audio.sample_rate", 48000)

        StateHandler._instance = None
        h2 = StateHandler()

        self.assertEqual(h2.get("theme.variant"), "midnight")
        self.assertEqual(h2.get("audio.sample_rate"), 48000)

    def test_listeners(self):
        calls = []
        def listener(key, value):
            calls.append((key, value))

        self.handler.listen("theme", listener)
        self.handler.set("theme.variant", "slate")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], ("theme.variant", "slate"))

    def test_reset(self):
        self.handler.set("some.key", "value")
        self.handler.reset()
        self.assertIsNone(self.handler.get("some.key"))


class TestToast(unittest.TestCase):
    def test_toast_types(self):
        from src.presentation.widgets.toast import ToastType
        self.assertIn(ToastType.SUCCESS, [ToastType.SUCCESS, ToastType.ERROR, ToastType.INFO, ToastType.WARNING])

    def test_type_config(self):
        from src.presentation.widgets.toast import _get_type_config, ToastType
        for t in ToastType:
            config = _get_type_config(t)
            self.assertIn("bg", config)
            self.assertIn("border", config)
            self.assertIn("icon_color", config)
            self.assertIn("icon", config)

    def test_toast_manager_singleton(self):
        from src.presentation.widgets.toast import ToastManager
        t1 = ToastManager()
        t2 = ToastManager()
        self.assertIs(t1, t2)

    def test_toast_manager_not_ready(self):
        from src.presentation.widgets.toast import ToastManager
        try:
            ToastManager.show_info("test")
        except Exception:
            self.fail("ToastManager.show_info raised exception when not initialized")

    def test_icon_fallback(self):
        from src.presentation.styles.icons import Icons
        self.assertTrue(hasattr(Icons, 'CHECK'))
        self.assertTrue(hasattr(Icons, 'CROSS'))
        self.assertTrue(hasattr(Icons, 'INFO'))
        self.assertTrue(hasattr(Icons, 'STAR'))


class TestShortcutsManagerConfigurable(unittest.TestCase):
    def setUp(self):
        from src.presentation.controllers.keyboard_shortcuts import ShortcutsManager, DEFAULT_SHORTCUTS, CONFIG_DIR, SHORTCUTS_FILE
        self._orig_config = CONFIG_DIR
        self._orig_file = SHORTCUTS_FILE
        self._tmpdir = tempfile.mkdtemp()

        import src.presentation.controllers.keyboard_shortcuts as ks
        ks.CONFIG_DIR = Path(self._tmpdir)
        ks.SHORTCUTS_FILE = ks.CONFIG_DIR / "shortcuts.json"

        ShortcutsManager._instance = None
        self.manager = ShortcutsManager()

    def tearDown(self):
        from src.presentation.controllers.keyboard_shortcuts import ShortcutsManager, CONFIG_DIR, SHORTCUTS_FILE
        import src.presentation.controllers.keyboard_shortcuts as ks
        ks.CONFIG_DIR = self._orig_config
        ks.SHORTCUTS_FILE = self._orig_file

    def test_default_shortcuts_loaded(self):
        self.assertIsNotNone(self.manager.get_shortcut("Play/Pause"))
        self.assertEqual(self.manager.get_shortcut("Play/Pause"), "Space")

    def test_get_all_shortcuts(self):
        all_sc = self.manager.get_all_shortcuts()
        self.assertGreater(len(all_sc), 30)

    def test_categories(self):
        cats = self.manager.get_categories()
        self.assertIn("Transport", cats)
        self.assertIn("Edit", cats)
        self.assertIn("View", cats)
        self.assertIn("File", cats)

    def test_get_by_category(self):
        transport = self.manager.get_by_category("Transport")
        names = [e.name for e in transport]
        self.assertIn("Play/Pause", names)
        self.assertIn("Stop", names)

    def test_find_conflict(self):
        conflict = self.manager.find_conflict("Play/Pause", "Ctrl+Z")
        self.assertEqual(conflict, "Undo")

    def test_no_conflict_with_self(self):
        conflict = self.manager.find_conflict("Play/Pause", "Space")
        self.assertIsNone(conflict)

    def test_set_shortcut(self):
        result = self.manager.set_shortcut("Play/Pause", "Ctrl+Space")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_shortcut("Play/Pause"), "Ctrl+Space")

    def test_set_shortcut_rejects_conflict(self):
        result = self.manager.set_shortcut("Play/Pause", "Ctrl+Z")
        self.assertFalse(result)

    def test_reset_defaults(self):
        self.manager.set_shortcut("Play/Pause", "Ctrl+Space")
        self.manager.reset_defaults()
        self.assertEqual(self.manager.get_shortcut("Play/Pause"), "Space")

    def test_invalid_name(self):
        self.assertIsNone(self.manager.get_shortcut("NonexistentAction"))

    def test_persistence(self):
        self.manager.set_shortcut("Loop", "Ctrl+L")
        from src.presentation.controllers.keyboard_shortcuts import ShortcutsManager
        ShortcutsManager._instance = None
        m2 = ShortcutsManager()
        self.assertEqual(m2.get_shortcut("Loop"), "Ctrl+L")


if __name__ == "__main__":
    unittest.main()
