import unittest
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestVSTHost(unittest.TestCase):
    def setUp(self):
        from src.infrastructure.plugins.vst_host import VSTHost, VSTVersion, PluginCategory
        self.host = VSTHost()

    def test_scan_all_returns_list(self):
        result = self.host.scan_all()
        self.assertIsInstance(result, list)

    def test_validate_nonexistent_returns_invalid(self):
        from src.infrastructure.plugins.vst_host import VSTVersion
        info = self.host.validate_plugin(Path("/nonexistent/plugin.dll"))
        self.assertFalse(info.is_valid)
        self.assertEqual(info.version, VSTVersion.UNKNOWN)

    def test_validate_tiny_file_returns_invalid(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".dll", delete=False)
        tmp.write(b"MZ" + b"\x00" * 100)
        tmp.close()
        info = self.host.validate_plugin(Path(tmp.name))
        self.assertFalse(info.is_valid)
        Path(tmp.name).unlink()

    def test_validate_vst2_magic_detected(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".dll", delete=False)
        tmp.write(b"MZ" + b"\x00" * 60000 + b"VSTPluginMain")
        tmp.close()
        info = self.host.validate_plugin(Path(tmp.name))
        self.assertTrue(info.is_valid)
        self.assertEqual(info.version.value, "vst2")
        Path(tmp.name).unlink()

    def test_scanned_plugins_dict(self):
        from src.infrastructure.plugins.vst_host import VSTPluginInfo, VSTVersion
        self.host._scanned_plugins["TestPlugin"] = VSTPluginInfo(
            name="TestPlugin", file_path=Path("test.dll"),
            version=VSTVersion.VST2, is_valid=True
        )
        plugins = self.host.get_scanned_plugins()
        self.assertGreaterEqual(len(plugins), 1)

    def test_find_plugin(self):
        from src.infrastructure.plugins.vst_host import VSTPluginInfo, VSTVersion
        self.host._scanned_plugins["TestSynth"] = VSTPluginInfo(
            name="TestSynth", file_path=Path("synth.dll"),
            version=VSTVersion.VST2, is_valid=True
        )
        info = self.host.find_plugin("TestSynth")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "TestSynth")
        self.assertIsNone(self.host.find_plugin("Nonexistent"))

    def test_load_plugin_invalid_returns_none(self):
        from src.infrastructure.plugins.vst_host import VSTPluginInfo, VSTVersion
        info = VSTPluginInfo(
            name="BadPlugin", file_path=Path("bad.dll"),
            version=VSTVersion.VST2, is_valid=False
        )
        result = self.host.load_plugin(info)
        self.assertIsNone(result)

    def test_unload_nonexistent_returns_false(self):
        self.assertFalse(self.host.unload_plugin("Nonexistent"))

    def test_loaded_count(self):
        self.assertEqual(self.host.get_loaded_count(), 0)

    def test_validate_vst3_bundle(self):
        import platform as pf
        if pf.system() == "Windows":
            self.skipTest("VST3 bundle test requires POSIX-style fs")
        tmp = Path(tempfile.mkdtemp())
        bundle = tmp / "Test.vst3"
        bundle.mkdir(parents=True)
        (bundle / "Contents" / "Resources").mkdir(parents=True)
        info = self.host.validate_plugin(bundle)
        self.assertEqual(info.version.value, "vst3")
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    def test_vst_versions(self):
        from src.infrastructure.plugins.vst_host import VSTVersion
        self.assertEqual(VSTVersion.VST2.value, "vst2")
        self.assertEqual(VSTVersion.VST3.value, "vst3")
        self.assertEqual(VSTVersion.UNKNOWN.value, "unknown")

    def test_plugin_categories(self):
        from src.infrastructure.plugins.vst_host import PluginCategory
        self.assertEqual(PluginCategory.EFFECT.value, 1)
        self.assertEqual(PluginCategory.SYNTH.value, 2)


class TestVSTPluginInfo(unittest.TestCase):
    def test_default_values(self):
        from src.infrastructure.plugins.vst_host import VSTPluginInfo, VSTVersion
        info = VSTPluginInfo(name="Test", file_path=Path("test.dll"), version=VSTVersion.VST2)
        self.assertEqual(info.name, "Test")
        self.assertEqual(info.num_inputs, 2)
        self.assertEqual(info.num_outputs, 2)
        self.assertFalse(info.is_valid)
        self.assertFalse(info.has_editor)
        self.assertEqual(info.parameters, [])

    def test_with_parameters(self):
        from src.infrastructure.plugins.vst_host import VSTPluginInfo, VSTVersion
        info = VSTPluginInfo(
            name="Test", file_path=Path("test.dll"),
            version=VSTVersion.VST2, is_valid=True,
            num_inputs=0, num_outputs=2, has_editor=True,
            parameters=[("Volume", 0.8), ("Pan", 0.5)]
        )
        self.assertTrue(info.is_valid)
        self.assertEqual(info.num_inputs, 0)
        self.assertTrue(info.has_editor)
        self.assertEqual(len(info.parameters), 2)


class TestPluginManager(unittest.TestCase):
    def setUp(self):
        from src.infrastructure.plugins.plugin_manager import PluginManager
        self.manager = PluginManager(scan_at_start=False)

    def test_scan_all_counts_builtins(self):
        count = self.manager.scan_all()
        self.assertGreaterEqual(count, 0)

    def test_catalog_initial_empty(self):
        self.assertEqual(self.manager.count, 0)

    def test_get_instruments_returns_list(self):
        instruments = self.manager.get_instruments()
        self.assertIsInstance(instruments, list)

    def test_get_effects_returns_list(self):
        effects = self.manager.get_effects()
        self.assertIsInstance(effects, list)

    def test_get_builtin_returns_list(self):
        builtin = self.manager.get_builtin()
        self.assertIsInstance(builtin, list)

    def test_get_vst_initial_empty(self):
        vst = self.manager.get_vst()
        self.assertEqual(len(vst), 0)

    def test_load_nonexistent_returns_none(self):
        result = self.manager.load("NonexistentPlugin")
        self.assertIsNone(result)

    def test_unload_nonexistent_returns_false(self):
        self.assertFalse(self.manager.unload("NonexistentPlugin"))

    def test_get_plugin_nonexistent_returns_none(self):
        self.assertIsNone(self.manager.get_plugin("NonexistentPlugin"))

    def test_toggle_favorite(self):
        from src.infrastructure.plugins.plugin_manager import PluginEntry
        self.manager._catalog["Test"] = PluginEntry(
            name="Test", plugin_type="builtin", category="effect"
        )
        self.assertTrue(self.manager.toggle_favorite("Test"))
        self.assertTrue(self.manager._catalog["Test"].is_favorite)
        self.assertFalse(self.manager.toggle_favorite("Nonexistent"))

    def test_add_to_blacklist(self):
        from src.infrastructure.plugins.plugin_manager import PluginEntry
        self.manager._catalog["BadPlugin"] = PluginEntry(
            name="BadPlugin", plugin_type="vst2", category="effect"
        )
        self.manager.add_to_blacklist("BadPlugin")
        self.assertIn("BadPlugin", self.manager._blacklist)
        self.assertNotIn("BadPlugin", self.manager._catalog)

    def test_loaded_count_starts_zero(self):
        self.assertEqual(self.manager.loaded_count, 0)

    def test_scan_directory(self):
        import shutil
        tmp = Path(tempfile.mkdtemp())
        try:
            result = self.manager.scan_directory(tmp)
            self.assertIsInstance(result, list)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_plugin_entry_dataclass(self):
        from src.infrastructure.plugins.plugin_manager import PluginEntry
        entry = PluginEntry(
            name="Synth1", plugin_type="builtin",
            category="instrument", version="2.0",
            vendor="TestCorp", is_favorite=True,
            tags=["lead", "bass"]
        )
        self.assertEqual(entry.name, "Synth1")
        self.assertEqual(entry.vendor, "TestCorp")
        self.assertTrue(entry.is_favorite)
        self.assertEqual(entry.tags, ["lead", "bass"])


if __name__ == "__main__":
    unittest.main()
