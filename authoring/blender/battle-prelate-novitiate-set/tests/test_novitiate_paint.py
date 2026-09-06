"""Source paint traceability, deterministic replay and channel safety."""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import paint_materials
import refine_novitiate_paint as refine


class NovitiatePaintTests(unittest.TestCase):
    def test_expanded_records_are_exact_finite_authored_copies(self):
        record = json.loads(refine.RECORD.read_text(encoding="utf-8"))
        paint_materials.validate_records(record)
        expected = {
            "novitiate_warp_yarn": refine.stamp(refine.WARP, refine.CLOTH_PLACEMENTS),
            "novitiate_weft_yarn": refine.stamp(refine.WEFT, refine.CLOTH_PLACEMENTS),
            "novitiate_leather_grain": refine.stamp(refine.LEATHER_GRAIN, refine.LEATHER_PLACEMENTS),
            "novitiate_linen_hem": refine.stamp(refine.HEM_DASH, refine.HEM_PLACEMENTS),
            "novitiate_linen_side": refine.stamp(refine.SIDE_DASH, refine.SIDE_PLACEMENTS),
        }
        for name, shapes in expected.items():
            self.assertEqual(record["brushes"][name]["shapes"], shapes)
        for path in expected["novitiate_linen_hem"]:
            self.assertTrue(all(950 <= y <= 953 for _, y in path))
        self.assertEqual(record["materials"]["crimson"]["base"]["basecolor"], [98,56,41])
        self.assertEqual(record["materials"]["crimson"]["base"]["metallic"], 0)
        self.assertEqual(record["materials"]["leather"]["base"]["metallic"], 0)

    def test_replay_is_idempotent_and_preserves_unrelated_material(self):
        original = json.loads(refine.RECORD.read_text(encoding="utf-8"))
        original["materials"]["independent_test_material"] = {"sentinel": [7,8,9], "layers": []}
        with tempfile.TemporaryDirectory() as folder:
            record = Path(folder) / "paint_strokes.json"
            record.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(refine, "RECORD", record), contextlib.redirect_stdout(io.StringIO()):
                refine.main()
                first = record.read_bytes()
                refine.main()
            self.assertEqual(first, record.read_bytes())
            self.assertEqual(json.loads(first)["materials"]["independent_test_material"], original["materials"]["independent_test_material"])
            self.assertEqual(json.loads(first)["materials"]["parchment"], original["materials"]["parchment"])

    def test_manifest_binds_actual_maps_and_expected_color_spaces(self):
        manifest = json.loads((ROOT / "textures/paint_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["paint_source_sha256"], hashlib.sha256(refine.RECORD.read_bytes()).hexdigest())
        for material in manifest["materials"].values():
            self.assertEqual(set(material["maps"]), set(paint_materials.CHANNELS))
            for channel, data in material["maps"].items():
                path = ROOT / "textures" / data["path"]
                self.assertEqual(data["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                with Image.open(path) as image:
                    self.assertEqual(image.size, (1024,1024))
                    self.assertEqual(image.mode, "RGB" if channel == "basecolor" else "L")
                self.assertEqual(data["color_space"], "sRGB" if channel == "basecolor" else "Non-Color")


if __name__ == "__main__":
    unittest.main()
