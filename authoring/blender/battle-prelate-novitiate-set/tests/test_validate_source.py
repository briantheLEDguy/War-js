"""Reject corrupt authored mesh records before Blender imports them."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate_source  # noqa: E402


def component_fixture() -> dict:
    """Small closed topology fixture with per-corner UVs and named landmarks."""
    vertices = [
        {"id": "a", "co": [0.0, 0.0, 0.0]},
        {"id": "b", "co": [1.0, 0.0, 0.0]},
        {"id": "c", "co": [0.0, 1.0, 0.0]},
        {"id": "d", "co": [0.0, 0.0, 1.0]},
    ]
    faces = [
        {"id": "base", "vertices": ["a", "c", "b"], "uv": [[0, 0], [0, 1], [1, 0]], "material": "steel"},
        {"id": "front", "vertices": ["a", "b", "d"], "uv": [[0, 0], [1, 0], [0, 1]], "material": "steel"},
        {"id": "outer", "vertices": ["b", "c", "d"], "uv": [[0, 0], [1, 0], [0, 1]], "material": "brass"},
        {"id": "side", "vertices": ["c", "a", "d"], "uv": [[0, 0], [1, 0], [0, 1]], "material": "steel"},
    ]
    return {
        "schema_version": 1,
        "component": "test_fixture",
        "reference_notes": [],
        "parts": [{
            "id": "shell", "vertices": vertices, "faces": faces, "closed": True,
            "landmarks": {"apex": "d"}, "seams": [["a", "b"]],
            "sharp_edges": [["a", "c"]], "creases": [{"edge": ["b", "c"], "value": 0.5}],
            "modifiers": [],
            "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0], "scale": [1, 1, 1]},
        }],
    }


class ValidateAuthoredSourceTests(unittest.TestCase):
    def setUp(self):
        self.data = component_fixture()
        self.part = self.data["parts"][0]

    def assert_rejected(self, message: str):
        with self.assertRaisesRegex(ValueError, message):
            validate_source.validate_component(self.data)

    def test_closed_reference_fixture_passes_with_counts(self):
        result = validate_source.validate_component(self.data)
        self.assertEqual(result, [{"part": "shell", "control_vertices": 4,
                                  "control_faces": 4, "control_triangles": 4,
                                  "control_boundary_edges": 0}])

    def test_component_name_must_be_nonempty_text(self):
        for name in ("", "  ", None, 42):
            with self.subTest(name=name):
                self.data["component"] = name
                self.assert_rejected("component name")

    def test_component_requires_nonempty_part_list(self):
        for parts in ([], None, {}):
            with self.subTest(parts=parts):
                self.data["parts"] = parts
                self.assert_rejected("at least one authored part")

    def test_part_name_must_be_nonempty_text(self):
        for name in ("", "  ", None, 42):
            with self.subTest(name=name):
                self.part["id"] = name
                self.assert_rejected("named part")

    def test_part_requires_vertices_and_faces(self):
        for field in ("vertices", "faces"):
            with self.subTest(field=field):
                original = self.part[field]
                self.part[field] = []
                self.assert_rejected("vertices and faces")
                self.part[field] = original

    def test_declared_open_control_surface_reports_boundary(self):
        self.part["faces"] = self.part["faces"][:1]
        self.part["closed"] = False
        result = validate_source.validate_component(self.data)
        self.assertEqual(result[0]["control_boundary_edges"], 3)

    def test_nonfinite_and_nonnumeric_vertex_coordinates_are_rejected(self):
        for coordinate in (float("nan"), float("inf"), -float("inf"), True, "1"):
            with self.subTest(coordinate=coordinate):
                self.part["vertices"][0]["co"] = [coordinate, 0, 0]
                self.assert_rejected("expected 3 finite coordinates")

    def test_vertex_coordinate_dimension_is_checked(self):
        for coordinates in ([0, 0], [0, 0, 0, 1], (0, 0, 0)):
            with self.subTest(coordinates=coordinates):
                self.part["vertices"][0]["co"] = coordinates
                self.assert_rejected("expected 3 finite coordinates")

    def test_duplicate_part_id_is_rejected(self):
        self.data["parts"].append(copy.deepcopy(self.part))
        self.assert_rejected("Duplicate part shell")

    def test_duplicate_vertex_id_is_rejected(self):
        self.part["vertices"].append(copy.deepcopy(self.part["vertices"][0]))
        self.assert_rejected("duplicate vertex a")

    def test_duplicate_face_id_is_rejected(self):
        self.part["faces"][1]["id"] = self.part["faces"][0]["id"]
        self.assert_rejected("duplicate face base")

    def test_missing_vertex_reference_is_rejected(self):
        self.part["faces"][0]["vertices"][0] = "missing"
        self.assert_rejected("invalid face indices")

    def test_repeated_vertex_inside_face_is_rejected(self):
        self.part["faces"][0]["vertices"] = ["a", "b", "a"]
        self.assert_rejected("invalid face indices")

    def test_face_requires_at_least_three_vertices(self):
        self.part["faces"][0]["vertices"] = ["a", "b"]
        self.assert_rejected("invalid face indices")

    def test_uv_count_must_match_face_corners(self):
        for uv in ([[0, 0], [1, 0]], [[0, 0], [1, 0], [0, 1], [1, 1]]):
            with self.subTest(uv=uv):
                self.part["faces"][0]["uv"] = uv
                self.assert_rejected("per-corner UV count mismatch")

    def test_uvs_require_two_finite_numeric_coordinates(self):
        for uv in ([float("nan"), 0], [0, float("inf")], [True, 0], [0], [0, 0, 0]):
            with self.subTest(uv=uv):
                self.part["faces"][0]["uv"][0] = uv
                self.assert_rejected("expected 2 finite coordinates")

    def test_collinear_face_is_rejected(self):
        self.part["vertices"][2]["co"] = [2, 0, 0]
        self.assert_rejected("degenerate face")

    def test_distinct_ids_with_coincident_positions_are_rejected(self):
        self.part["vertices"][1]["co"] = [0, 0, 0]
        self.assert_rejected("degenerate face")

    def test_unknown_material_is_rejected(self):
        self.part["faces"][0]["material"] = "procedural_noise_material"
        self.assert_rejected("unknown material")

    def test_landmark_must_reference_existing_vertex(self):
        self.part["landmarks"]["apex"] = "missing"
        self.assert_rejected("missing landmark apex")

    def test_false_closed_declaration_is_rejected(self):
        self.part["faces"].pop()
        self.assert_rejected("declared closed but has 3 boundary edges")

    def test_edge_with_three_incident_faces_is_rejected(self):
        extra = copy.deepcopy(self.part["faces"][0])
        extra["id"] = "extra_incident_face"
        self.part["faces"].append(extra)
        self.assert_rejected("nonmanifold control edge")

    def test_crease_requires_real_edge_and_bounded_finite_weight(self):
        for crease in (
            {"edge": ["a", "missing"], "value": 0.5},
            {"edge": ["a", "b"], "value": -0.01},
            {"edge": ["a", "b"], "value": 1.01},
            {"edge": ["a", "b"], "value": float("inf")},
            {"edge": ["a", "b"], "value": float("nan")},
        ):
            with self.subTest(crease=crease):
                self.part["creases"] = [crease]
                self.assert_rejected("invalid crease")

    def test_seams_and_sharp_edges_require_mesh_edges(self):
        for field in ("seams", "sharp_edges"):
            with self.subTest(field=field):
                original = self.part[field]
                self.part[field] = [["a", "missing"]]
                self.assert_rejected(f"{field} references nonexistent edge")
                self.part[field] = original

    def test_prohibited_modifiers_are_rejected(self):
        for modifier in ("NODES", "REMESH", "SCREW", "SKIN", "ARRAY", "DISPLACE"):
            with self.subTest(modifier=modifier):
                self.part["modifiers"] = [{"type": modifier}]
                self.assert_rejected(f"prohibited modifier {modifier}")

    def test_declared_finishing_modifiers_are_allowed(self):
        self.part["modifiers"] = [
            {"type": "MIRROR", "axis": "X"},
            {"type": "SUBSURF", "levels": 2},
            {"type": "BEVEL", "width": 0.001, "segments": 2},
            {"type": "SOLIDIFY", "thickness": 0.003, "offset": 0},
        ]
        self.assertEqual(validate_source.validate_component(self.data)[0]["control_faces"], 4)

    def test_subdivision_bounds_are_checked(self):
        for levels in (-1, 5):
            with self.subTest(levels=levels):
                self.part["modifiers"] = [{"type": "SUBSURF", "levels": levels}]
                self.assert_rejected("excessive subdivision")

    def test_mirror_axis_must_be_a_single_supported_axis(self):
        for axis in ("XY", "x", "", 1, None):
            with self.subTest(axis=axis):
                self.part["modifiers"] = [{"type": "MIRROR", "axis": axis}]
                self.assert_rejected("invalid mirror axis")

    def test_bevel_parameters_require_bounded_width_and_integer_segments(self):
        for settings in (
            {"type": "BEVEL"}, {"type": "BEVEL", "width": 0},
            {"type": "BEVEL", "width": 0.06}, {"type": "BEVEL", "width": "0.001"},
            {"type": "BEVEL", "width": float("nan")},
            {"type": "BEVEL", "width": 0.001, "segments": 0},
            {"type": "BEVEL", "width": 0.001, "segments": 9},
            {"type": "BEVEL", "width": 0.001, "segments": 2.5},
        ):
            with self.subTest(settings=settings):
                self.part["modifiers"] = [settings]
                self.assert_rejected("invalid bevel settings")

    def test_solidify_parameters_require_bounded_finite_thickness_and_offset(self):
        for settings in (
            {"type": "SOLIDIFY"}, {"type": "SOLIDIFY", "thickness": 0},
            {"type": "SOLIDIFY", "thickness": -0.003},
            {"type": "SOLIDIFY", "thickness": 0.06},
            {"type": "SOLIDIFY", "thickness": float("inf")},
            {"type": "SOLIDIFY", "thickness": 0.003, "offset": 2},
            {"type": "SOLIDIFY", "thickness": 0.003, "offset": float("nan")},
            {"type": "SOLIDIFY", "thickness": 0.003, "offset": "0"},
        ):
            with self.subTest(settings=settings):
                self.part["modifiers"] = [settings]
                self.assert_rejected("invalid solidify settings")

    def test_nonfinite_transform_is_rejected(self):
        self.part["transform"]["rotation_degrees"] = [0, float("nan"), 0]
        self.assert_rejected("expected 3 finite coordinates")

    def test_singular_transform_is_rejected(self):
        self.part["transform"]["scale"] = [1, 0, 1]
        self.assert_rejected("singular scale")

    def test_explicit_instance_transform_is_validated(self):
        self.part["instances"] = [{"location": [0, float("inf"), 0]}]
        self.assert_rejected("expected 3 finite coordinates")

    def test_repository_component_records_pass_when_present(self):
        paths = sorted(path for path in (ROOT / "source").glob("*.json") if path.name != "scene.json")
        if not paths:
            self.skipTest("No authored component JSON files exist yet")
        for path in paths:
            with self.subTest(component=path.name):
                rows = validate_source.validate_component(json.loads(path.read_text(encoding="utf-8")))
                self.assertGreater(len(rows), 0, "Component has no parts")
                self.assertTrue(all(row["control_faces"] > 0 for row in rows), "A part has no faces")


if __name__ == "__main__":
    unittest.main()
