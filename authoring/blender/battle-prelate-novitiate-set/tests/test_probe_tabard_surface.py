"""Probe output isolation and protected-input hash guards."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_tabard_surface as probe


class ProbeIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_output_cannot_target_staged_runtime(self):
        with self.assertRaisesRegex(ValueError, "fresh subdirectory"):
            probe.output_directory(self.root, self.root / "runtime/probe", False)
        self.assertFalse((self.root / "runtime").exists())

    def test_existing_probe_directory_is_not_overwritten(self):
        destination = self.root / "review/tabard_surface_probe/old"
        destination.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            probe.output_directory(self.root, destination, False)

    def test_snapshot_detects_staged_change_and_new_asset(self):
        (self.root / "runtime").mkdir()
        model = self.root / "runtime/character.glb"
        model.write_bytes(b"existing asset")
        master = self.root / "game.blend"
        master.write_bytes(b"existing master")
        before = probe.protected_snapshot(self.root, master)
        model.write_bytes(b"changed asset")
        extra = self.root / "runtime/extra.glb"
        extra.write_bytes(b"new asset")
        after = probe.protected_snapshot(self.root, master)
        self.assertNotEqual(before[str(model.resolve())], after[str(model.resolve())])
        self.assertNotIn(str(extra.resolve()), before)
        self.assertIn(str(extra.resolve()), after)
        self.assertEqual(before[str(master.resolve())], after[str(master.resolve())])


if __name__ == "__main__":
    unittest.main()
