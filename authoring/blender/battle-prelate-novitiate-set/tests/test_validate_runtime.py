"""Binary corruption and contract tests using tiny synthetic audit fixtures.

The fixture triangles are test input only, never character geometry or exports.
"""
import base64
import copy
import gzip
import io
import json
import math
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from validate_runtime import AuditError, CLIPS, Glb, SLOTS, compare_skins, model_name, sha256, validate_bundle, validate_glb


def fixture():
    binary = bytearray()
    document = {"asset": {"version": "2.0"}, "buffers": [], "bufferViews": [], "accessors": []}
    def view(payload):
        binary.extend(b"\0" * (-len(binary) % 4))
        index = len(document["bufferViews"])
        document["bufferViews"].append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(payload)})
        binary.extend(payload)
        return index
    def accessor(rows, kind, component=5126, normalized=False):
        fmt = {5121: "B", 5123: "H", 5126: "f"}[component]
        payload = b"".join(struct.pack("<" + fmt * len(row), *row) for row in rows)
        index = len(document["accessors"])
        document["accessors"].append({"bufferView": view(payload), "componentType": component, "type": kind,
                                      "count": len(rows), "normalized": normalized})
        return index
    attributes = {
        "POSITION": accessor([(0, 0, 0), (1, 0, 0), (0, 1, 0)], "VEC3"),
        "NORMAL": accessor([(0, 0, 1)] * 3, "VEC3"),
        "TEXCOORD_0": accessor([(0, 0), (1, 0), (0, 1)], "VEC2"),
        "JOINTS_0": accessor([(0, 1, 0, 0)] * 3, "VEC4", 5121),
        "WEIGHTS_0": accessor([(1, 0, 0, 0)] * 3, "VEC4"),
    }
    indices = accessor([(0,), (1,), (2,)], "SCALAR", 5123)
    identity = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    inverse = accessor([identity, identity], "MAT4")
    times = accessor([(0,), (1,)], "SCALAR")
    motion = accessor([(0, 0, 0), (0, .1, 0)], "VEC3")
    # A fixed valid 1x1 PNG used for all required channels in structural fixtures.
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    document.update({
        "scene": 0, "scenes": [{"nodes": [0, 3]}],
        "nodes": [{"name": "humanoid_game_v2", "children": [1]}, {"name": "hips", "children": [2]},
                  {"name": "upper_chest"}, {"name": "body", "mesh": 0, "skin": 0}],
        "skins": [{"joints": [1, 2], "inverseBindMatrices": inverse}],
        "meshes": [{"primitives": [{"attributes": attributes, "indices": indices, "material": 0}]}],
        "images": [{"bufferView": view(png), "mimeType": "image/png"}], "textures": [{"source": 0}],
        "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicRoughnessTexture": {"index": 0}},
                       "normalTexture": {"index": 0}, "occlusionTexture": {"index": 0}}],
        "animations": [{"name": name, "samplers": [{"input": times, "output": motion}],
                        "channels": [{"sampler": 0, "target": {"node": 1, "path": "translation"}}]} for name in sorted(CLIPS)],
    })
    document["buffers"] = [{"byteLength": len(binary)}]
    return document, binary


def pack(document, binary):
    json_payload = json.dumps(document).encode()
    json_payload += b" " * (-len(json_payload) % 4)
    binary = bytes(binary) + b"\0" * (-len(binary) % 4)
    length = 12 + 8 + len(json_payload) + 8 + len(binary)
    return struct.pack("<4sII", b"glTF", 2, length) + struct.pack("<II", len(json_payload), 0x4E4F534A) + json_payload + struct.pack("<II", len(binary), 0x004E4942) + binary


def replace_value(document, binary, index, values, fmt="f"):
    acc = document["accessors"][index]
    view = document["bufferViews"][acc["bufferView"]]
    struct.pack_into("<" + fmt * len(values), binary, view.get("byteOffset", 0) + acc.get("byteOffset", 0), *values)


class RuntimeAuditTests(unittest.TestCase):
    def setUp(self):
        self.doc, self.binary = fixture()
        self.primitive = self.doc["meshes"][0]["primitives"][0]

    def audit(self, slot="body"):
        return validate_glb(Glb(pack(self.doc, self.binary)), slot)

    def rejected(self, message, slot="body"):
        with self.assertRaisesRegex(AuditError, message):
            self.audit(slot)

    def test_valid_binary_counts_and_animation_samples(self):
        report = self.audit()
        self.assertEqual((report["triangles"], report["vertices"], report["draw_calls"], report["max_influences"]), (1, 3, 1, 1))
        self.assertEqual(len(report["animations"]), 9)
        self.assertTrue(all(a["changing_joint_channels"] == 1 for a in report["animations"]))

    def test_declared_glb_length_is_checked(self):
        payload = bytearray(pack(self.doc, self.binary))
        struct.pack_into("<I", payload, 8, len(payload) - 4)
        with self.assertRaisesRegex(AuditError, "declared length"):
            Glb(payload)

    def test_nonfinite_position_is_rejected(self):
        replace_value(self.doc, self.binary, self.primitive["attributes"]["POSITION"], [math.nan])
        self.rejected("POSITION contains nonfinite")

    def test_accessor_cannot_read_next_buffer_view(self):
        acc = self.doc["accessors"][self.primitive["attributes"]["POSITION"]]
        acc["count"] = 4
        self.rejected("exceeds bufferView")

    def test_stride_cannot_be_shorter_than_element(self):
        acc = self.doc["accessors"][self.primitive["attributes"]["POSITION"]]
        self.doc["bufferViews"][acc["bufferView"]]["byteStride"] = 8
        self.rejected("stride is shorter")

    def test_non_triangle_mode_is_rejected(self):
        self.primitive["mode"] = 1
        self.rejected("must use TRIANGLES")

    def test_triangle_index_out_of_range_is_rejected(self):
        replace_value(self.doc, self.binary, self.primitive["indices"], [0, 1, 3], "H")
        self.rejected("index exceeds POSITION")

    def test_degenerate_triangle_is_rejected(self):
        replace_value(self.doc, self.binary, self.primitive["indices"], [0, 1, 1], "H")
        self.rejected("degenerate triangle")

    def test_joint_indices_are_checked_even_for_zero_weight(self):
        replace_value(self.doc, self.binary, self.primitive["attributes"]["JOINTS_0"], [0, 1, 0, 2], "B")
        self.rejected("JOINTS index exceeds")

    def test_zero_weight_vertex_is_rejected(self):
        replace_value(self.doc, self.binary, self.primitive["attributes"]["WEIGHTS_0"], [0, 0, 0, 0])
        self.rejected("zero or more than four")

    def test_non_normalized_weight_sum_is_rejected(self):
        replace_value(self.doc, self.binary, self.primitive["attributes"]["WEIGHTS_0"], [.5, 0, 0, 0])
        self.rejected("do not sum to one")

    def test_negative_weight_is_rejected(self):
        replace_value(self.doc, self.binary, self.primitive["attributes"]["WEIGHTS_0"], [1, -.1, .1, 0])
        self.rejected("WEIGHTS must lie")

    def test_nonfinite_weight_is_rejected(self):
        replace_value(self.doc, self.binary, self.primitive["attributes"]["WEIGHTS_0"], [math.inf, 0, 0, 0])
        self.rejected("nonfinite")

    def test_more_than_four_influences_across_sets_is_rejected(self):
        attributes = self.primitive["attributes"]
        attributes["JOINTS_1"] = attributes["JOINTS_0"]
        attributes["WEIGHTS_1"] = attributes["WEIGHTS_0"]
        replace_value(self.doc, self.binary, attributes["WEIGHTS_0"], [.2, .2, .1, 0])
        self.rejected("zero or more than four")

    def test_unpaired_joint_weight_set_is_rejected(self):
        self.primitive["attributes"]["JOINTS_1"] = self.primitive["attributes"]["JOINTS_0"]
        self.rejected("Unpaired JOINTS")

    def test_normalized_integer_accessors_decode_actual_weights(self):
        index = self.primitive["attributes"]["WEIGHTS_0"]
        acc = self.doc["accessors"][index]
        acc["componentType"] = 5121
        acc["normalized"] = True
        replace_value(self.doc, self.binary, index, [255, 0, 0, 0] * 3, "B")
        self.assertEqual(self.audit()["max_influences"], 1)

    def test_body_requires_all_nine_animation_names(self):
        self.doc["animations"].pop()
        self.rejected("Missing body animations")

    def test_named_but_static_animation_is_rejected(self):
        index = self.doc["animations"][0]["samplers"][0]["output"]
        replace_value(self.doc, self.binary, index, [0, 0, 0, 0, 0, 0])
        self.rejected("no changing joint samples")

    def test_inverse_bind_matrix_count_must_match_joints(self):
        acc = self.doc["accessors"][self.doc["skins"][0]["inverseBindMatrices"]]
        acc["count"] = 1
        self.rejected("count differs from joint count")

    def test_skin_comparison_uses_joint_names_not_export_order(self):
        body = self.audit()["skins"]
        other = copy.deepcopy(body)
        other[0]["joints"] = dict(reversed(list(other[0]["joints"].items())))
        compare_skins(body, other)
        other[0]["joints"]["hips"]["inverse_bind"][12] = .25
        with self.assertRaisesRegex(AuditError, "inverseBindMatrices differ"):
            compare_skins(body, other)

    def test_missing_required_material_map_is_rejected(self):
        del self.doc["materials"][0]["normalTexture"]
        self.rejected("missing required normal texture")

    def test_texture_cannot_request_absent_uv_set(self):
        self.doc["materials"][0]["normalTexture"]["texCoord"] = 1
        self.rejected("missing TEXCOORD_1")

    def test_texture_above_2048_is_rejected(self):
        from PIL import Image
        stream = io.BytesIO()
        Image.new("RGB", (2049, 1)).save(stream, format="PNG")
        payload = stream.getvalue()
        self.binary.extend(b"\0" * (-len(self.binary) % 4))
        image_view = self.doc["bufferViews"][self.doc["images"][0]["bufferView"]]
        image_view.update(byteOffset=len(self.binary), byteLength=len(payload))
        self.binary.extend(payload)
        self.doc["buffers"][0]["byteLength"] = len(self.binary)
        self.rejected("exceeds 2048")

    def test_texture_cannot_escape_runtime_directory(self):
        self.doc["images"][0] = {"uri": "../outside.png"}
        with tempfile.TemporaryDirectory() as directory:
            glb = Glb(pack(self.doc, self.binary), Path(directory) / "fixture.glb", directory)
            with self.assertRaisesRegex(AuditError, "escapes runtime"):
                validate_glb(glb, "body")

    def test_armor_draw_call_budget_is_checked(self):
        self.doc["meshes"][0]["primitives"] = [copy.deepcopy(self.primitive) for _ in range(3)]
        self.rejected("exceeds two draw calls", "chest")

    def test_body_draw_call_budget_is_checked(self):
        self.doc["meshes"][0]["primitives"] = [copy.deepcopy(self.primitive) for _ in range(5)]
        self.rejected("exceeds four draw calls")

    def test_armor_triangle_budget_uses_binary_index_count(self):
        indices = self.doc["accessors"][self.primitive["indices"]]
        view = self.doc["bufferViews"][indices["bufferView"]]
        self.binary.extend(b"\0" * (-len(self.binary) % 4))
        payload = struct.pack("<HHH", 0, 1, 2) * 14001
        view.update(byteOffset=len(self.binary), byteLength=len(payload))
        self.binary.extend(payload)
        indices["count"] = 14001 * 3
        self.doc["buffers"][0]["byteLength"] = len(self.binary)
        self.rejected("exceeds 14,000 triangles", "chest")

    def test_reachable_mesh_instances_count_as_draw_calls(self):
        self.doc["nodes"].append({"name": "second", "mesh": 0, "skin": 0})
        self.doc["scenes"][0]["nodes"].append(4)
        report = self.audit()
        self.assertEqual((report["triangles"], report["draw_calls"]), (2, 2))

    def test_empty_runtime_never_reports_success(self):
        with tempfile.TemporaryDirectory() as directory:
            result = validate_bundle(directory)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["errors"]), 34)
        self.assertEqual(result["assets"], {})


class EvaluatedArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.runtime = root / "runtime"
        self.runtime.mkdir()
        source = root / "source/head.json"
        source.parent.mkdir()
        source.write_bytes(b'{"fixture":true}')
        records = [{"file": "source/head.json", "part": "fixture", "sha256": sha256(source.read_bytes())}]
        self.archive = self.runtime / "evaluated_lods.json.gz"
        self.archive.write_bytes(gzip.compress(b'{"meshes":[]}'))
        self.stage = {"evaluated_mesh_archive_sha256": sha256(self.archive.read_bytes()), "lods": {}}
        for lod in (0, 1, 2):
            modules = {}
            for slot in SLOTS:
                document, binary = fixture()
                document["nodes"][3]["extras"] = {"source_records": json.dumps(records)}
                if slot == "weapon":
                    del document["nodes"][3]["skin"]
                payload = pack(document, binary)
                (self.runtime / model_name(slot, lod)).write_bytes(payload)
                modules[slot] = {"sha256": sha256(payload), "bytes": len(payload), "triangles": 1, "source_records": records}
            self.stage["lods"][str(lod)] = {"modules": modules}
        self.write_stage()

    def tearDown(self):
        self.temp.cleanup()

    def write_stage(self):
        (self.runtime / "runtime_report.json").write_text(json.dumps(self.stage))

    def test_valid_archive_is_recorded_outside_runtime_asset_budget(self):
        report = validate_bundle(self.runtime)
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertEqual(report["evaluated_mesh_archive"], {"file": self.archive.name,
                         "sha256": self.stage["evaluated_mesh_archive_sha256"], "bytes": self.archive.stat().st_size})
        self.assertEqual(len(report["assets"]), 33)
        self.assertNotIn(str(self.archive), report["assets"])

    def test_missing_declared_archive_rejects_full_bundle(self):
        self.archive.unlink()
        report = validate_bundle(self.runtime)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("Evaluated mesh archive is missing" in error for error in report["errors"]))

    def test_changed_declared_archive_rejects_even_partial_audit(self):
        self.archive.write_bytes(gzip.compress(b'{"meshes":["changed"]}'))
        report = validate_bundle(self.runtime, (0,))
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("archive hash changed" in error for error in report["errors"]))

    def test_full_bundle_requires_archive_declaration(self):
        del self.stage["evaluated_mesh_archive_sha256"]
        self.write_stage()
        report = validate_bundle(self.runtime)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("evaluated_mesh_archive_sha256" in error for error in report["errors"]))

    def test_partial_legacy_stage_without_archive_has_explicit_warning(self):
        del self.stage["evaluated_mesh_archive_sha256"]
        self.write_stage()
        report = validate_bundle(self.runtime, (0,))
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertFalse(report["full_bundle_requested"])
        self.assertNotIn("evaluated_mesh_archive", report)
        self.assertTrue(any("Partial audit: no declared evaluated mesh archive" in warning for warning in report["warnings"]))

    def test_binary_only_partial_audit_is_explicitly_not_full_validation(self):
        (self.runtime / "runtime_report.json").unlink()
        report = validate_bundle(self.runtime, (0,))
        self.assertEqual(report["status"], "passed", report["errors"])
        self.assertFalse(report["full_bundle_requested"])
        self.assertTrue(any("Partial audit: no runtime_report.json" in warning for warning in report["warnings"]))
        full = validate_bundle(self.runtime)
        self.assertEqual(full["status"], "failed")
        self.assertTrue(any("Full-bundle validation requires runtime_report.json" in error for error in full["errors"]))


if __name__ == "__main__":
    unittest.main()
