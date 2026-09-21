"""Regression cases for the importer bind-pose defect."""
import copy
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location("pose_parity", Path(__file__).resolve().parents[1] / "scripts/unreal/pose_parity.py")
parity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parity)


class PoseParityTest(unittest.TestCase):
    def setUp(self):
        self.source = {"joints": {"rig/root": [0, 0, 0]},
                       "deformations": {"rig/root": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]}}
        self.actual = {"root": {"position": [0, 0, 0],
                                "deformedBasis": [[0, 0, 0], [100, 0, 0], [0, 100, 0], [0, 0, 100]]}}

    def test_fixed_coordinate_basis(self):
        self.assertEqual(parity.to_unreal([1, 2, 3]), [100, -200, 300])
        self.assertEqual(parity.compare_frame(self.source, self.actual), (0, 0))

    def test_matching_joint_positions_do_not_hide_wrong_bind_rotation(self):
        self.actual["root"]["deformedBasis"][1] = [0, 0, -100]
        with self.assertRaisesRegex(ValueError, "pose mismatch"):
            parity.compare_frame(self.source, self.actual)

    def test_missing_bone_and_nonfinite_values_fail(self):
        with self.assertRaisesRegex(ValueError, "lost source bone"):
            parity.compare_frame(self.source, {})
        for field in ("position", "deformedBasis"):
            broken = copy.deepcopy(self.actual)
            if field == "position":
                broken["root"][field][0] = float("nan")
            else:
                broken["root"][field][0][0] = float("nan")
            with self.assertRaisesRegex(ValueError, "Nonfinite"):
                parity.compare_frame(self.source, broken)

    def test_import_failure_identifies_clip_mode_and_time(self):
        unreal = SimpleNamespace(load_asset=Mock(return_value=object()),
            AnimDataEvalType=SimpleNamespace(RAW="RAW", COMPRESSED="COMPRESSED"),
            AnimPoseEvaluationOptions=Mock(return_value=Mock()))
        samples = {"attack_melee": {"sampleTimesSeconds": [0.25], "samples": [self.source]}}
        broken = copy.deepcopy(self.actual)
        broken["root"]["deformedBasis"][1][0] += 1
        with patch.object(parity, "evaluate_frame", side_effect=[self.actual, broken]):
            with self.assertRaisesRegex(ValueError, "Clip attack_melee, COMPRESSED, time 0.250000s.*pose mismatch"):
                parity.verify_animations(unreal, [{"sourceClipName": "attack_melee", "path": "/example"}], samples)


if __name__ == "__main__":
    unittest.main()
