import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("class_character_audit", Path(__file__).resolve().parents[1] / "scripts/unreal/class_character_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ClassCharacterAuditTests(unittest.TestCase):
    def test_correction_requires_exact_source_and_normalized_canonical_weights(self):
        spec = importlib.util.spec_from_file_location("skin_contract", Path(__file__).resolve().parents[1] / "scripts/unreal/class_character_skin.py")
        skin = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"numpy": SimpleNamespace(), "mathutils.kdtree": SimpleNamespace(KDTree=None)}):
            spec.loader.exec_module(skin)
        baseline = dict(hipIterations=96, shoulderIterations=192, trunkAnchorWidth=.45)
        data = dict(schemaVersion=1, identity="stoneguard_m", sourceBodySha256="source", positionSha256="positions",
                    sourceVertexCount=2, baseline=baseline, nativeAccepted=False, runtimeEligible=False,
                    rows=[dict(vertex=0, weights=dict(hips=.6, spine=.4))])
        def validate(value):
            return skin.validate_correction(value, "stoneguard_m", "source", "positions", 2, ["hips", "spine"], baseline)
        self.assertEqual(validate(data), data["rows"])
        for change in (dict(sourceBodySha256="stale"), dict(positionSha256="other"), dict(nativeAccepted=True),
                       dict(identity="stoneguard_f"), dict(baseline={**baseline, "shoulderIterations": 128}),
                       dict(rows=data["rows"]*2), dict(rows=[dict(vertex=2, weights=dict(hips=1))]),
                       dict(rows=[dict(vertex=True, weights=dict(hips=1))]),
                       dict(rows=[dict(vertex=0, weights=dict(hips=.6))]),
                       dict(rows=[dict(vertex=0, weights=dict(foreign=1))]),
                       dict(rows=[dict(vertex=0, weights=dict(hips=float("nan")))])):
            with self.assertRaises(ValueError): validate({**data, **change})

    def test_weight_transfer_preserves_uv_seams_and_rejects_foreign_surfaces(self):
        # Export duplicates UV seam vertices. They must receive the same welded
        # source row, even when four-influence pruning discards a fifth weight.
        class Tree:
            def __init__(self, count): self.points = []
            def insert(self, point, index): self.points.append((point, index))
            def balance(self): pass
            def find(self, point):
                position, index = min(self.points, key=lambda entry: sum((a-b)**2 for a, b in zip(entry[0], point)))
                return position, index, sum((a-b)**2 for a, b in zip(position, point))**.5
        class Identity:
            def __matmul__(self, point): return point
        class Group:
            def __init__(self, name): self.name, self.weights = name, {}
            def remove(self, indices):
                for index in indices: self.weights.pop(index, None)
            def add(self, indices, value, mode):
                for index in indices: self.weights[index] = value
        class Groups(list):
            def get(self, name): return next((group for group in self if group.name == name), None)
            def new(self, name):
                group = Group(name)
                self.append(group)
                return group
        dependencies = {"numpy": SimpleNamespace(argsort=lambda row: sorted(range(len(row)), key=lambda index: row[index])),
                        "mathutils.kdtree": SimpleNamespace(KDTree=Tree)}
        spec = importlib.util.spec_from_file_location("skin_transfer", Path(__file__).resolve().parents[1] / "scripts/unreal/class_character_skin.py")
        skin = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", dependencies): spec.loader.exec_module(skin)
        names = ["a", "b", "c", "d", "e"]
        rig = SimpleNamespace(data=SimpleNamespace(bones=dict.fromkeys(names)))
        groups = Groups()
        body = SimpleNamespace(data=SimpleNamespace(vertices=[SimpleNamespace(index=index, co=(0, 0, 0)) for index in range(2)]),
                               matrix_world=Identity(), vertex_groups=groups)
        source = dict(names=names, positions=[(0, 0, 0)], weights=[[.8, .1, .05, .03, .02]], evidence={})
        skin.transfer(body, rig, source)
        self.assertEqual(len(groups), 4)
        self.assertAlmostEqual(sum(group.weights[0] for group in groups), 1)
        self.assertTrue(all(group.weights[0] == group.weights[1] for group in groups))
        body.data.vertices[1].co = (.001, 0, 0)
        with self.assertRaisesRegex(RuntimeError, "authoring surface"):
            skin.transfer(body, rig, source)
        with self.assertRaisesRegex(RuntimeError, "different skeleton"):
            skin.transfer(body, rig, {**source, "names": ["foreign"]})
        for iterations in (0, 257, 2.5, True):
            with self.assertRaises(ValueError):
                skin.refine_source(None, None, iterations)
            with self.assertRaises(ValueError):
                skin.refine_source(None, None, 96, iterations)
        for width in (0, 1, float("nan"), True):
            with self.assertRaises(ValueError):
                skin.refine_source(None, None, 96, 96, width)

    def test_lower_canines_are_curved_symmetric_and_closed(self):
        left, faces = audit.canine_surface(1, (.028, -.1, 1.7), .036)
        right, _ = audit.canine_surface(-1, (-.028, -.1, 1.7), .036)
        for index, point in enumerate(left[:-1]):
            ring, segment = divmod(index, 16)
            mirror = right[ring * 16 + (8 - segment) % 16]
            self.assertAlmostEqual(point[0], -mirror[0])
            self.assertAlmostEqual(point[1], mirror[1])
            self.assertAlmostEqual(point[2], mirror[2])
        self.assertAlmostEqual(left[-1][0], -right[-1][0])
        self.assertLess(left[-1][1], -.1)
        self.assertAlmostEqual(left[-1][2] - 1.7, .036)
        edges = {}
        for face in faces:
            for a, b in zip(face, face[1:] + face[:1]):
                edge = tuple(sorted((a, b)))
                edges[edge] = edges.get(edge, 0) + 1
        self.assertTrue(all(count == 2 for count in edges.values()))

    def test_packed_colour_samples_are_not_gamma_converted_twice(self):
        self.assertEqual(audit.texture_srgb("#804020"), (128 / 255, 64 / 255, 32 / 255))
        with self.assertRaises(ValueError):
            audit.texture_srgb("#fff")

    def test_weights_require_real_normalized_finite_influences(self):
        self.assertTrue(all(audit.weight_checks([[1], [.4, .3, .2, .1]]).values()))
        for weights in ([], [[]], [[.5]], [[float("nan")]], [[-1, 2]], [[.2] * 5]):
            self.assertFalse(all(audit.weight_checks(weights).values()))

    def test_anatomy_rejects_asymmetry_and_the_original_long_calf(self):
        lengths = {f"{name}_{side}": value for side in ("L", "R") for name, value in
                   (("upper_arm", .22), ("forearm", .23), ("thigh", .36), ("shin", .34))}
        self.assertTrue(all(audit.limb_checks(lengths).values()))
        self.assertFalse(audit.limb_checks({**lengths, "thigh_L": .20})["thighSymmetry"])
        self.assertFalse(audit.limb_checks({**lengths, "thigh_L": .297, "shin_L": .402})["legRatioL"])
        self.assertFalse(audit.limb_checks({**lengths, "thigh_L": float("nan")})["finitePositiveLengths"])

    def test_edge_density_does_not_conceal_visible_joint_spikes(self):
        dense = dict(finite=True, p01EdgeRatio=.8, p99EdgeRatio=1.3, maxEdgeExtensionM=.012)
        self.assertTrue(audit.deformation_checks(dense, 1.5))
        # Stock Dwarf knee extended by 48 mm; the corrected candidate is 16 mm.
        self.assertFalse(audit.deformation_checks({**dense, "maxEdgeExtensionM": .048}, 1.5))
        self.assertTrue(audit.deformation_checks({**dense, "maxEdgeExtensionM": .016}, 1.5))
        self.assertFalse(audit.deformation_checks({**dense, "p99EdgeRatio": 2}, 1.5))
        self.assertFalse(audit.deformation_checks({**dense, "p01EdgeRatio": .1}, 1.5))
        self.assertFalse(audit.deformation_checks({**dense, "finite": False}, 1.5))


if __name__ == "__main__":
    unittest.main()
