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
    def test_material_slots_follow_unreal_fbx_names_without_losing_hyphens(self):
        self.assertEqual(importer.material_slot_mapping(["body.high-poly", "ns:cloth.body"]),
                         {"body_high-poly": "body.high-poly", "cloth_body": "ns:cloth.body"})
        with self.assertRaisesRegex(RuntimeError, "collide"):
            importer.material_slot_mapping(["body.high-poly", "body_high-poly"])

    def test_all_actual_examples_pass_preflight(self):
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

    def test_repository_textures_are_contained_and_fingerprinted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "public/assets/models/house.glb"
            texture = root / "public/assets/textures/wall.png"
            model.parent.mkdir(parents=True); texture.parent.mkdir(parents=True)
            original = b"\x89PNG\r\n\x1a\noriginal"
            texture.write_bytes(original)
            def write_model(uri, **extra):
                payload = json.dumps({"images": [{"uri": uri, "mimeType": "image/png", **extra}]}).encode()
                payload += b" " * (-len(payload) % 4)
                model.write_bytes(struct.pack("<4sII", b"glTF", 2, 20 + len(payload))
                                 + struct.pack("<II", len(payload), 0x4E4F534A) + payload)
            with patch.object(importer, "ROOT", root):
                write_model("../textures/wall.png")
                _, images = importer.read_glb(model)
                self.assertEqual(images[0]["bytes"], original)
                before = importer.image_dependencies(images)
                self.assertEqual(before[0]["sourcePath"], "public/assets/textures/wall.png")
                texture.write_bytes(original + b"changed")
                self.assertNotEqual(importer.image_dependencies(importer.read_glb(model)[1]), before)
                for uri in ("https://example.com/wall.png", "//server/share.png", "C:/private.png",
                            "../../../secret.png", "%2e%2e/%2e%2e/%2e%2e/secret.png", "../textures/wall.png?token=x"):
                    with self.subTest(uri=uri):
                        write_model(uri)
                        with self.assertRaises(RuntimeError): importer.read_glb(model)
                write_model("../textures/wall.png", bufferView=0)
                with self.assertRaisesRegex(RuntimeError, "Ambiguous"): importer.read_glb(model)
                write_model("../textures/missing.png")
                with self.assertRaisesRegex(RuntimeError, "missing"): importer.read_glb(model)

    def test_unsupported_material_features_fail_instead_of_disappearing(self):
        with self.assertRaisesRegex(RuntimeError, "Unsupported material"):
            importer.texture_roles({"materials": [{"name": "custom", "extensions": {"unsupported": {}}}]})

    def test_emissive_factor_strength_and_color_texture(self):
        material = {"name": "window", "emissiveFactor": [1, 0.35, 0.055],
                    "extensions": {"KHR_materials_emissive_strength": {"emissiveStrength": 1.5}},
                    "emissiveTexture": {"index": 0}}
        self.assertEqual(importer.emissive_color(material), [1.5, 0.35 * 1.5, 0.055 * 1.5])
        self.assertEqual(importer.texture_roles({"materials": [material], "textures": [{"source": 0}]}), {0: "color"})
        for factor in ([1, 2, 0], [1, 0], [True, 0, 0], [float("nan"), 0, 0]):
            with self.assertRaisesRegex(RuntimeError, "emissive factor"):
                importer.emissive_color({"emissiveFactor": factor})
        for strength in (-1, float("inf"), True, "1"):
            with self.assertRaisesRegex(RuntimeError, "emissive strength"):
                importer.emissive_color({"extensions": {"KHR_materials_emissive_strength": {"emissiveStrength": strength}}})

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
