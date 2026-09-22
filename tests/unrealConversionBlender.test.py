"""Run with Blender --background --factory-startup --python-exit-code 1 --python this_file."""
import copy
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
import bpy


source = Path(__file__).resolve().parents[1] / "scripts/unreal/convert-model.py"
spec = importlib.util.spec_from_file_location("unreal_convert_model", source)
conversion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conversion)


def snapshot(x=0.0):
    return {
        "joints": {"rig/root": [x, 0.0, 0.0]},
        "deformations": {"rig/root": [1.0, 0.0, 0.0, x]},
        "meshBoundsMeters": {"body": {"min": [x, 0.0, 0.0], "max": [x + 1.0, 1.0, 2.0]}},
    }


def clip():
    return {"walk": {
        "durationSeconds": 1.0, "sampleTimesSeconds": [0.0, 0.5, 1.0],
        "boundObjects": ["rig"], "actions": ["walk"], "curveCount": 3,
        "keyframeCount": 9, "samples": [snapshot(), snapshot(0.5), snapshot(1.0)],
    }}


class RoundtripVerificationTest(unittest.TestCase):
    def test_float32_endpoint_keeps_the_final_fbx_sample(self):
        strip = SimpleNamespace(frame_end=119.999992)
        conversion.stabilize_strip_endpoint(strip)
        self.assertEqual(strip.frame_end, 120.0)
        for frame in (119.5, 120.0, 120.000008):
            strip = SimpleNamespace(frame_end=frame)
            conversion.stabilize_strip_endpoint(strip)
            self.assertEqual(strip.frame_end, frame)

    def test_source_graph_rejects_generated_display_mesh(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        source_graph = {"nodes": [{"name": "authored_body", "mesh": 0}],
                        "meshes": [{"primitives": [{"indices": 0, "attributes": {"POSITION": 1}}]}],
                        "accessors": [{"count": 3}, {"count": 3}]}
        def add_triangle(name):
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
            bpy.context.scene.collection.objects.link(bpy.data.objects.new(name, mesh))
        add_triangle("authored_body")
        self.assertEqual(conversion.validate_source_geometry(source_graph)["triangles"], 1)
        add_triangle("generated_bone_display")
        with self.assertRaisesRegex(ValueError, "generated helpers are forbidden"):
            conversion.validate_source_geometry(source_graph)
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_authored_mesh_identity_is_not_filtered_by_primitive_name(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new("authored")
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        bpy.context.scene.collection.objects.link(bpy.data.objects.new("Icosphere", mesh))
        graph = {"nodes": [{"name": "Icosphere", "mesh": 0}],
                 "meshes": [{"primitives": [{"indices": 0, "attributes": {"POSITION": 1}}]}],
                 "accessors": [{"count": 3}, {"count": 3}]}
        self.assertEqual(conversion.validate_source_geometry(graph)["meshes"], 1)
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_baked_curve_count_may_change_when_motion_matches(self):
        source_clip = clip()
        converted = copy.deepcopy(source_clip)
        converted["walk"]["curveCount"] = 12
        converted["walk"]["keyframeCount"] = 120
        report = conversion.validate_animation_samples(source_clip, converted)[0]
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["sourceMaximumJointMotionMeters"], 1.0)

    def test_static_bake_is_rejected_even_with_nonempty_curves(self):
        converted = clip()
        converted["walk"]["samples"] = [snapshot(), snapshot(), snapshot()]
        with self.assertRaisesRegex(ValueError, "sampled pose mismatch"):
            conversion.validate_animation_samples(clip(), converted)

    def test_lost_clip_and_missing_sample_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "changed clip names"):
            conversion.validate_animation_samples(clip(), {})
        converted = clip()
        converted["walk"]["samples"].pop()
        with self.assertRaisesRegex(ValueError, "sample coverage changed"):
            conversion.validate_animation_samples(clip(), converted)

    def test_centimeter_as_meter_scale_error_is_rejected(self):
        converted = clip()
        converted["walk"]["samples"][1]["meshBoundsMeters"]["body"]["max"][2] *= 100
        with self.assertRaisesRegex(ValueError, "sampled pose mismatch"):
            conversion.validate_animation_samples(clip(), converted)

    def test_missing_joint_and_clip_duration_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "changed joints identities"):
            conversion.compare_snapshots(snapshot(), {**snapshot(), "joints": {}})
        converted = clip()
        converted["walk"]["durationSeconds"] = 2.0
        with self.assertRaisesRegex(ValueError, "changed duration"):
            conversion.validate_animation_samples(clip(), converted)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RoundtripVerificationTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("Unreal Blender conversion tests failed")
