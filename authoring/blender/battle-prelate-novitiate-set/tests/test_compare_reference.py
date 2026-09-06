"""Semantic landmark tests; no Blender changes or reference fitting."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import compare_reference as compare


class BeltLandmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "source").mkdir()
        self.source = self.root / "source/waist.json"
        self.source.write_text(json.dumps({"parts": [
            {"id": "heavy_relic_belt", "vertices": [{"id": "v000", "co": [0, -.16, 1.203]}], "landmarks": {}},
            {"id": "breastplate_shell", "vertices": [{"id": "old", "co": [0, -.16, 1.26]}], "landmarks": {"waist_center": "old"}},
        ]}))
        identity = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        self.evaluated = {"parts": [{"name": name, "matrix_world": identity, "source_sha256": compare.digest(self.source)}
                                    for name in ("heavy_relic_belt", "breastplate_shell")]}
        self.scene = {"acceptance": {"major_landmark_tolerance_m": .0372}}
        self.measurements = {"landmarks": {"front": [{"id": "F11", "name": "waist_belt_upper_center",
                              "raw_pixel": [254.282, 319.27], "uncertainty_radius_px": 4}]}}

    def tearDown(self):
        self.temp.cleanup()

    def row(self):
        return next(row for row in compare.landmarks(self.root, self.scene, self.measurements, self.evaluated)
                    if row["reference_id"] == "F11")

    def test_f11_measures_actual_belt_instead_of_breastplate_surrogate(self):
        row = self.row()
        self.assertEqual(row["part"], "heavy_relic_belt")
        self.assertEqual(row["source_vertex_id"], "v000")
        self.assertEqual(row["source_point_kind"], "explicit_diagnostic_vertex")
        self.assertEqual(row["world_position_m"], [0, -.16, 1.203])
        self.assertFalse(row["automatic_visual_acceptance"])

    def test_explicit_diagnostic_vertex_still_requires_matching_source_hash(self):
        self.source.write_text(self.source.read_text() + "\n")
        row = self.row()
        self.assertEqual(row["status"], "source_changed_since_render_no_measurement")
        self.assertNotIn("world_position_m", row)


if __name__ == "__main__":
    unittest.main()
