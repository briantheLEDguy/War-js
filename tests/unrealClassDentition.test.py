import importlib.util
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dentition", ROOT / "scripts/unreal/class_character_dentition.py")
dentition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dentition)


class DentitionTests(unittest.TestCase):
    def test_curved_crowns_are_symmetric_and_start_behind_the_lip(self):
        root = (.021, -.143, 1.734)
        height, front = .037, -.177
        for t in (0, .25, .5, .75, 1):
            for segment in range(16):
                angle = segment*math.pi/8
                left = dentition.enamel_point(1, root, height, front, t, angle)
                right = dentition.enamel_point(-1, (-root[0], *root[1:]), height, front, t, math.pi-angle)
                self.assertAlmostEqual(left[0], -right[0])
                self.assertAlmostEqual(left[1], right[1])
                self.assertAlmostEqual(left[2], right[2])
                if t == 0:
                    self.assertGreater(left[1], -.160)
        tip = dentition.enamel_point(1, root, height, front, 1, 0)
        self.assertAlmostEqual(tip[1], front)
        self.assertAlmostEqual(tip[2], root[2]+height)
        for height, t in ((0, .5), (.037, -1), (.037, 2), (float("nan"), .5)):
            with self.assertRaises(ValueError): dentition.enamel_point(1, root, height, front, t, 0)

    def test_face_weight_collapse_preserves_normalization_and_four_influences(self):
        split = dentition.jaw_weights(dict(head=1), .9)
        self.assertAlmostEqual(split["jaw"], .9)
        self.assertAlmostEqual(split["head"], .1)
        self.assertEqual(dentition.jaw_weights(dict(head=1), 0), dict(head=1))
        self.assertEqual(dentition.jaw_weights(dict(head=1), 1), dict(jaw=1))
        weights = dentition.jaw_weights(dict(head=.6, neck=.2, chest=.15, upper_chest=.05), .2)
        self.assertEqual(len(weights), 4)
        self.assertAlmostEqual(sum(weights.values()), 1)
        for amount in (-1, 2, float("nan")):
            with self.assertRaises(ValueError): dentition.jaw_weights(dict(head=1), amount)

    def test_arches_follow_source_uvs_after_reordering_without_height_guessing(self):
        contract = json.loads((ROOT / "scripts/unreal/class-character-jaw-weights.json").read_text())["dentalCrownUvContract"]
        reordered = contract[::2]+contract[1::2]
        bounds = [row["bounds"] for row in reordered]
        self.assertEqual(dentition.split_crowns(bounds, contract), [row["lower"] for row in reordered])
        for values in (bounds[:-1], [bounds[0]]*32, [[float("nan")]*4, *bounds[1:]], [[0]*4, *bounds[1:]]):
            with self.assertRaises(ValueError): dentition.split_crowns(values, contract)

    def test_surface_contract_allows_reordering_but_rejects_changed_geometry(self):
        points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        signature = dentition.surface_signature(points, [(0, 1, 2)])
        self.assertEqual(signature, dentition.surface_signature([points[2], points[0], points[1], points[0]], [(3, 2, 0)]))
        self.assertNotEqual(signature, dentition.surface_signature(points, [(0, 2, 1)]))
        self.assertNotEqual(signature, dentition.surface_signature([(0, 0, .01), *points[1:]], [(0, 1, 2)]))

    def test_retained_weight_mask_is_cc0_unique_and_bounded(self):
        data = json.loads((ROOT / "scripts/unreal/class-character-jaw-weights.json").read_text())
        self.assertEqual(data["license"], "CC0")
        self.assertEqual(data["sourceFittingVertices"], 19158)
        self.assertEqual(len(data["weights"]), 1032)
        self.assertEqual(len({index for index, _ in data["weights"]}), 1032)
        self.assertTrue(all(0 <= index < 13380 and math.isfinite(weight) and 0 < weight <= 1 for index, weight in data["weights"]))


if __name__ == "__main__":
    unittest.main()
