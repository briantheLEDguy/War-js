"""Pure file/hash gates and contact-sheet checks, without requiring Blender."""
import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import reimport_review as review


class DisplayHelperTests(unittest.TestCase):
    def test_custom_shape_reference_identifies_helper_without_name_heuristic(self):
        class Object:
            pass
        helper, real_mesh, rig = Object(), Object(), Object()
        helper.type = real_mesh.type = "MESH"
        helper.name, real_mesh.name = "arbitrary helper name", "Icosphere_authored_emblem"
        rig.type = "ARMATURE"
        rig.pose = SimpleNamespace(bones=[SimpleNamespace(custom_shape=helper), SimpleNamespace(custom_shape=None)])
        self.assertEqual(review.bone_display_helpers([helper, real_mesh, rig]), {helper})


class ReimportGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        (self.runtime / "runtime_report.json").write_text("{}")
        self.validation = self.runtime / "validation_report.json"
        modules = {}
        for slot in review.SLOTS:
            name = review.model_name(slot, 0)
            (self.runtime / name).write_bytes(b"test-only file hash fixture")
            modules[slot] = {"model": name, "sha256": review.digest(self.runtime / name)}
        self.report = {"status": "passed", "errors": [], "runtime_directory": str(self.runtime),
                       "stage_report_sha256": review.digest(self.runtime / "runtime_report.json"),
                       "lods": {"0": {"complete": True, "modules": modules}}}
        self.write()

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        self.validation.write_text(json.dumps(self.report))

    def test_gate_checks_all_requested_module_hashes(self):
        _, hashes = review.check_files(self.runtime, self.validation, (0,))
        self.assertEqual(len(hashes), 11)

    def test_failed_validation_does_not_start_reimport(self):
        self.report["status"] = "failed"
        self.write()
        with self.assertRaisesRegex(ValueError, "must pass"):
            review.check_files(self.runtime, self.validation, (0,))

    def test_partial_validation_does_not_cover_missing_lod(self):
        with self.assertRaisesRegex(ValueError, "LOD1 is not fully validated"):
            review.check_files(self.runtime, self.validation, (0, 1))

    def test_stale_export_is_rejected(self):
        (self.runtime / review.model_name("hands", 0)).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Export changed"):
            review.check_files(self.runtime, self.validation, (0,))

    def test_stale_build_report_is_rejected(self):
        (self.runtime / "runtime_report.json").write_text('{"new": true}')
        with self.assertRaisesRegex(ValueError, "Runtime build changed"):
            review.check_files(self.runtime, self.validation, (0,))


class ContactSheetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.review_dir = self.root / "review"
        self.review_dir.mkdir()
        self.image = self.review_dir / "fixture.png"
        self.image.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="))
        self.report_path = self.review_dir / "reimport_report.json"
        self.report = {"status": "rendered_pending_visual_review", "evidence": [], "motion_frames": [
            {"path": "review/fixture.png", "sha256": review.digest(self.image), "clip": name, "fraction": fraction, "frame": 1+fraction*20}
            for name in review.CLIPS for fraction in (.15, .5, .85)]}
        self.write()

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        self.report_path.write_text(json.dumps(self.report))

    def test_contact_sheet_does_not_approve_visual_review(self):
        with patch.object(review, "ROOT", self.root):
            review.compose(self.report_path)
        result = json.loads(self.report_path.read_text())
        self.assertEqual(result["status"], "rendered_pending_visual_review")
        self.assertEqual(result["contact_sheet"]["sha256"], review.digest(self.root / result["contact_sheet"]["path"]))

    def test_missing_motion_sample_is_rejected(self):
        self.report["motion_frames"].pop()
        self.write()
        with patch.object(review, "ROOT", self.root), self.assertRaisesRegex(ValueError, "all three recorded samples"):
            review.compose(self.report_path)

    def test_changed_frame_is_not_composited(self):
        self.image.write_bytes(b"changed")
        with patch.object(review, "ROOT", self.root), self.assertRaisesRegex(ValueError, "changed since render"):
            review.compose(self.report_path)


if __name__ == "__main__":
    unittest.main()
