import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/unreal"))
from capital_materials import SOURCE, TARGET, cloth_material, package_file


class MaterialProtectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = package_file(self.root, SOURCE)
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b"purchased-original")
        self.target = package_file(self.root, TARGET)
        self.receipt = self.root / "artifacts/unreal/licensed-kits/cloth-material-adaptation.json"
        self.compiles = 0

        class Material:
            pass

        self.material = Material()

        def duplicate(source, target):
            self.assertEqual((source, target), (SOURCE, TARGET))
            self.target.parent.mkdir(parents=True)
            self.target.write_bytes(b"adapted-native-copy")
            return self.material

        def compile_material(material):
            self.assertIs(material, self.material)
            self.compiles += 1

        self.unreal = SimpleNamespace(Material=Material,
            Paths=SimpleNamespace(project_dir=lambda: str(self.root / "unreal/AegisWar")),
            SystemLibrary=SimpleNamespace(get_engine_version=lambda: "5.8.2-test"),
            EditorAssetLibrary=SimpleNamespace(duplicate_asset=duplicate, save_loaded_asset=lambda *a, **kw: True),
            MaterialEditingLibrary=SimpleNamespace(recompile_material=compile_material),
            load_asset=lambda _: self.material)

    def test_repeat_preserves_source_and_native_copy(self):
        self.assertIs(cloth_material(self.root, self.unreal), self.material)
        before = self.target.read_bytes()
        self.assertIs(cloth_material(self.root, self.unreal), self.material)
        self.assertEqual(self.compiles, 1)
        self.assertEqual(self.source.read_bytes(), b"purchased-original")
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(json.loads(self.receipt.read_text())["visualApproved"])

    def test_owner_edits_are_not_overwritten(self):
        cloth_material(self.root, self.unreal)
        self.target.write_bytes(b"owner-material-edit")
        with self.assertRaises(RuntimeError):
            cloth_material(self.root, self.unreal)
        self.assertEqual(self.target.read_bytes(), b"owner-material-edit")
        self.assertEqual(self.compiles, 1)

    def test_changed_purchase_requires_reconciliation(self):
        cloth_material(self.root, self.unreal)
        self.source.write_bytes(b"updated-purchased-pack")
        with self.assertRaises(RuntimeError):
            cloth_material(self.root, self.unreal)
        self.assertEqual(self.compiles, 1)

    def test_unrecorded_existing_asset_is_preserved(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b"owner-existing-material")
        with self.assertRaises(RuntimeError):
            cloth_material(self.root, self.unreal)
        self.assertEqual(self.target.read_bytes(), b"owner-existing-material")
        self.assertEqual(self.compiles, 0)

    def test_staging_project_cannot_write_game_assets(self):
        self.unreal.Paths.project_dir = lambda: str(self.root / "CityKitStaging")
        with self.assertRaises(RuntimeError):
            cloth_material(self.root, self.unreal)
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
