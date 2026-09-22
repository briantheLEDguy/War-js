"""Recovery must keep all original modules and invalidate stale native assemblies."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("equipped_source", Path(__file__).resolve().parents[1] / "scripts/unreal/equipped_source.py")
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class EquippedSourceTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        models = self.root / "public/assets/models"
        models.mkdir(parents=True)
        self.registry = {"characterProfiles": {}, "equipment": {}}
        for slot in source.SLOTS:
            name = source.module_name(slot)
            path = models / name
            path.write_bytes(slot.encode())
            record = {"model": name, "modelSha256": source.digest(path), "bodyVariant": "m", "approvalState": "approved", "runtimeReady": True}
            if slot == "body":
                self.registry["characterProfiles"][source.PROFILE] = record
            else:
                self.registry["equipment"][slot] = {"variants": {"m": record}}
        directory = self.root / "artifacts/unreal/equipped" / source.PROFILE
        directory.mkdir(parents=True)
        self.model, self.receipt = directory / "equipped.glb", directory / "assembly.json"
        self.model.write_bytes(b"complete equipped character")
        self.document = {"schemaVersion": 1, "profileKey": source.PROFILE,
                         "modules": source.module_sources(self.root, self.registry), "sourceSha256": source.digest(self.model)}
        self.receipt.write_text(json.dumps(self.document))

    def resolve(self):
        return source.resolve_source(self.root, "characterProfiles", source.PROFILE,
                                     self.registry["characterProfiles"][source.PROFILE], self.registry)

    def test_complete_assembly_resolves_without_replacing_browser_body(self):
        result = self.resolve()
        self.assertEqual(result[:2], (self.model, self.receipt))
        self.assertEqual(len(self.document["modules"]), 11)
        self.assertEqual(self.registry["characterProfiles"][source.PROFILE]["model"], source.module_name("body"))

    def test_missing_armor_cannot_pass_as_complete_character(self):
        self.document["modules"].pop()
        self.receipt.write_text(json.dumps(self.document))
        with self.assertRaisesRegex(ValueError, "stale or incomplete"):
            self.resolve()

    def test_changed_assembly_and_changed_original_module_are_rejected(self):
        self.model.write_bytes(b"substituted NPC")
        with self.assertRaisesRegex(ValueError, "stale or incomplete"):
            self.resolve()
        self.model.write_bytes(b"complete equipped character")
        (self.root / "public/assets/models" / source.module_name("weapon")).write_bytes(b"different weapon")
        with self.assertRaisesRegex(ValueError, "Unverified Prelate module"):
            self.resolve()

    def test_wrong_body_or_unapproved_armor_is_rejected(self):
        original = copy.deepcopy(self.registry)
        self.registry["equipment"]["chest"]["variants"]["m"]["bodyVariant"] = "f"
        with self.assertRaisesRegex(ValueError, "one registered male"):
            self.resolve()
        self.registry = original
        self.registry["equipment"]["chest"]["variants"]["m"]["runtimeReady"] = False
        with self.assertRaisesRegex(ValueError, "Unverified Prelate module"):
            self.resolve()


if __name__ == "__main__":
    unittest.main()
