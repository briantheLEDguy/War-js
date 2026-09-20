"""Pure-Python preflight tests; actual import receipts require the Unreal commandlet."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch


source = Path(__file__).resolve().parents[1] / "scripts/unreal/import-models.py"
spec = importlib.util.spec_from_file_location("unreal_import_models", source)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class ModelImportPreflightTest(unittest.TestCase):
    def test_all_three_actual_examples_pass_preflight(self):
        for profile in importer.PROFILES:
            with self.subTest(profile=profile):
                context = importer.validate_inputs(profile)
                self.assertEqual(len(context["images"]), len(importer.texture_roles(context["gltf"])))

    def test_path_escape_and_unknown_profile_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Path escapes"):
            importer.relative_path("../not-a-repo-asset.fbx")
        with self.assertRaisesRegex(RuntimeError, "reviewed conversion"):
            importer.validate_inputs("unknown")

    def test_changed_bytes_cannot_reuse_old_receipt_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "asset.fbx"
            path.write_bytes(b"old")
            digest = importer.sha256(path)
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(RuntimeError, "Byte hash mismatch"):
                importer.verified_file(path, digest)

    def test_old_conversion_with_generated_bone_display_is_rejected(self):
        load = importer.load_json
        def old_conversion(path):
            document = load(path)
            if path.name == "conversion.json":
                document = copy.deepcopy(document)
                document["before"]["meshes"] += 1
                document["after"]["meshes"] += 1
            return document
        with patch.object(importer, "load_json", old_conversion):
            with self.assertRaisesRegex(RuntimeError, "generated helper geometry is forbidden"):
                importer.validate_inputs(importer.PROFILES[0])

    def test_embedded_image_extraction_keeps_exact_source_bytes(self):
        binary = b"exact original image bytes"
        document = {"bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(binary)}],
                    "images": [{"name": "original", "bufferView": 0, "mimeType": "image/png"}]}
        encoded = json.dumps(document).encode()
        encoded += b" " * (-len(encoded) % 4)
        padded_binary = binary + b"\0" * (-len(binary) % 4)
        total = 12 + 8 + len(encoded) + 8 + len(padded_binary)
        data = struct.pack("<4sII", b"glTF", 2, total)
        data += struct.pack("<II", len(encoded), 0x4E4F534A) + encoded
        data += struct.pack("<II", len(padded_binary), 0x004E4942) + padded_binary
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.glb"
            path.write_bytes(data)
            _, images = importer.read_glb(path)
            self.assertEqual(images[0]["bytes"], binary)
            self.assertEqual(hashlib.sha256(images[0]["bytes"]).digest(), hashlib.sha256(binary).digest())

    def test_unsupported_material_features_fail_instead_of_disappearing(self):
        with self.assertRaisesRegex(RuntimeError, "Unsupported material"):
            importer.texture_roles({"materials": [{"name": "custom", "extensions": {"unsupported": {}}}]})

    def test_visual_registry_invalidates_only_selected_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            registry = project / "Content/Migration/visual-imports.json"
            registry.parent.mkdir(parents=True)
            registry.write_text(json.dumps({"schemaVersion": 1, "entries": [
                {"profileKey": "retain", "skeletalMeshPath": "/Game/Retain.Retain"},
                {"profileKey": "retry", "skeletalMeshPath": "/Game/Old.Old"}]}))
            with patch.object(importer, "PROJECT", project), patch.object(importer, "VISUAL_REGISTRY", registry):
                importer.update_visual_registry(["retry"])
                self.assertEqual([entry["profileKey"] for entry in importer.load_json(registry)["entries"]], ["retain"])
                importer.update_visual_registry(["retry"], [{"profileKey": "retry", "skeletalMeshPath": "/Game/New.New"}])
                document = importer.load_json(registry)
                self.assertEqual(document["entries"][0]["skeletalMeshPath"], "/Game/Retain.Retain")
                self.assertEqual(document["entries"][1]["skeletalMeshPath"], "/Game/New.New")
                self.assertFalse(registry.with_suffix(".tmp").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
