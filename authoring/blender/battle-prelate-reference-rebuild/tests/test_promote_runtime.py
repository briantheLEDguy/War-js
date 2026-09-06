"""Promotion safety tests; only temporary fake files are published by fixtures."""
import base64
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import promote_runtime as promote


def passed_report():
    return {"status": "passed", "errors": [], "full_bundle_requested": True, "stage_report_sha256": "c" * 64,
            "lods": {str(lod): {"complete": True, "modules": {slot: {"model": promote.model_name(slot, lod), "sha256": "a"*64}
                     for slot in promote.SLOTS}} for lod in (0, 1, 2)}}


class PromotionGateTests(unittest.TestCase):
    def test_failed_validation_cannot_promote(self):
        report = passed_report()
        report["status"] = "failed"
        with self.assertRaisesRegex(promote.PromotionError, "has not passed"):
            promote.expected_hashes(report)

    def test_partial_validation_cannot_promote(self):
        report = passed_report()
        report["full_bundle_requested"] = False
        with self.assertRaisesRegex(promote.PromotionError, "Partial LOD"):
            promote.expected_hashes(report)

    def test_missing_module_cannot_promote(self):
        report = passed_report()
        del report["lods"]["2"]["modules"]["back"]
        with self.assertRaisesRegex(promote.PromotionError, "incomplete"):
            promote.expected_hashes(report)

    def test_renamed_asset_cannot_promote(self):
        report = passed_report()
        report["lods"]["0"]["modules"]["body"]["model"] = "female.glb"
        with self.assertRaisesRegex(promote.PromotionError, "Unexpected model name"):
            promote.expected_hashes(report)

    def test_destinations_reject_traversal_and_gameplay_files(self):
        self.assertFalse(promote.allowed_destination("src/game/Player.ts"))
        self.assertFalse(promote.allowed_destination("authoring/archives/battle-prelate-reference-rebuild/x/../../../../src/game/Player.ts"))
        self.assertFalse(promote.allowed_destination(promote.APPROVED / "chr_civic_battle_prelate_t1_f.approved.json"))
        self.assertTrue(promote.allowed_destination(promote.MODELS / promote.model_name("body", 2)))

    def test_registry_changes_preserve_unrelated_entries_and_female_variant(self):
        manifest = {"runtime": {"itemKey": "prelate_chest", "bodyVariant": "m"}}
        old = {"assetVersion": "old", "equipment": {"prelate_chest": {"variants": {"m": {"model": "old.glb"}, "f": {"model": "female.glb"}}}, "other": {"variants": {"m": {"model": "other.glb"}}}}}
        new = copy.deepcopy(old)
        new["assetVersion"] = "new"
        new["equipment"]["prelate_chest"]["variants"]["m"]["model"] = "new.glb"
        promote.assert_registry_scope(old, new, [manifest])
        new["equipment"]["prelate_chest"]["variants"]["f"]["model"] = "modified.glb"
        with self.assertRaisesRegex(promote.PromotionError, "unrelated registry"):
            promote.assert_registry_scope(old, new, [manifest])


class VisualReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.report = passed_report()
        self.validation = self.root / "validation.json"
        self.validation.write_bytes(promote.json_bytes(self.report))
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        (self.root / "image.png").write_bytes(png)
        evidence = [{"id": view, "scope": "equipped", "view": view, "path": "image.png", "sha256": promote.sha256(png)} for view in sorted(promote.REVIEW_VIEWS)]
        evidence.append({"id": "stress", "scope": "animation_stress", "path": "image.png", "sha256": promote.sha256(png)})
        self.review = {"status": "accepted_for_local_runtime", "reviewed_by": "test-reviewer", "reviewed_at": "2026-09-06T00:00:00Z",
                       "validation_report_sha256": promote.file_hash(self.validation), "runtime_report_sha256": self.report["stage_report_sha256"],
                       "model_hashes": promote.expected_hashes(self.report), "checks": {name: "passed" for name in promote.REVIEW_CHECKS},
                       "findings": [], "evidence": evidence}

    def tearDown(self):
        self.temp.cleanup()

    def audit(self):
        return promote.validate_review(self.review, self.root / "review.json", self.validation, self.report, self.root)

    def test_structurally_complete_local_review_is_read(self):
        self.assertEqual(len(self.audit()), 5)

    def test_review_is_not_accepted_without_actual_reviewer_state(self):
        self.review["status"] = "pending"
        with self.assertRaisesRegex(promote.PromotionError, "completed local visual review"):
            self.audit()

    def test_review_rejects_changed_evidence_bytes(self):
        (self.root / "image.png").write_bytes(b"changed")
        with self.assertRaisesRegex(promote.PromotionError, "missing or changed"):
            self.audit()

    def test_review_rejects_different_model_revision(self):
        self.review["model_hashes"][promote.model_name("body", 0)] = "b" * 64
        with self.assertRaisesRegex(promote.PromotionError, "exact 33 model hashes"):
            self.audit()

    def test_blocking_finding_is_not_overridden_by_passed_flags(self):
        self.review["findings"] = [{"blocking": True, "detail": "Hand does not reach grip"}]
        with self.assertRaisesRegex(promote.PromotionError, "blocking finding"):
            self.audit()


class SocketWeaponRegistryTests(unittest.TestCase):
    def test_compiled_weapon_is_explicitly_rigid_while_armor_remains_skinned(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node is required to run the existing runtime registry compiler")
        repo = Path(__file__).resolve().parents[4]
        weapon = promote.read_json(repo / promote.APPROVED / "wep_civic_battle_prelate_dawn_maul.approved.json")
        armor = promote.read_json(repo / promote.APPROVED / "arm_civic_battle_prelate_hands_t1_m.approved.json")
        # Reproduce older manifests that carry skeleton compatibility without
        # declaring whether the mesh itself is skinned.
        weapon["runtime"].pop("skinned", None)
        armor["runtime"].pop("skinned", None)
        original = copy.deepcopy(weapon)
        candidate_weapon = promote.module_manifest_metadata(weapon, "weapon")
        candidate_armor = promote.module_manifest_metadata(armor, "hands")
        self.assertEqual(weapon, original)
        self.assertIs(candidate_weapon["runtime"]["skinned"], False)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "registry.json"
            promote.compile_registry(repo, [candidate_weapon, candidate_armor], output, node)
            registry = promote.read_json(output)
        compiled_weapon = registry["equipment"][weapon["runtime"]["itemKey"]]["variants"]["m"]
        compiled_armor = registry["equipment"][armor["runtime"]["itemKey"]]["variants"]["m"]
        self.assertIs(compiled_weapon["skinned"], False)
        self.assertIs(compiled_armor["skinned"], True)
        self.assertEqual(compiled_weapon["model"], "wep_civic_battle_prelate_dawn_maul.glb")
        self.assertEqual(compiled_weapon["skeletonId"], "humanoid_game_v2")


class LodQcProvenanceTests(unittest.TestCase):
    def test_qc_preserves_each_lods_actual_source_parts_and_finishing(self):
        validation = {"lods": {}}
        runtime_report = {"lods": {}}
        for lod in (0, 1, 2):
            records = [{"file": "source/breastplate.json", "part": "breastplate_shell", "sha256": "b"*64,
                        "finishing": [{"type": "SUBSURF", "level": 1 if lod == 0 else 0},
                                      {"type": "BEVEL", "segments": 1 if lod == 2 else 2}]}]
            if lod != 2:
                records.append({"file": "source/medallion.json", "part": "reliquary_dental_crowns",
                                "sha256": "c"*64, "finishing": []})
            module = {"model": promote.model_name("chest", lod), "sha256": str(lod)*64,
                      "bytes": 100, "triangles": 20, "draw_calls": 1, "materials": [],
                      "geometry": [{"mesh": 0}], "max_influences": 1, "animations": [],
                      "source_records": records}
            validation["lods"][str(lod)] = {"modules": {"chest": module}}
            runtime_report["lods"][str(lod)] = {"modules": {"chest": {
                "boundary_edges": 0, "nonmanifold_edges": 0, "degenerate_triangles": 0}}}
        inherited = {"kind": "explicit_reference_mesh_rebuild",
                     "sourceRecords": copy.deepcopy(validation["lods"]["0"]["modules"]["chest"]["source_records"])}
        original = copy.deepcopy(inherited)
        manifest = {"assetId": "fixture_chest", "category": "armor", "compatibility": {"bodyVariant": "m"}}
        for lod in (0, 1, 2):
            with self.subTest(lod=lod):
                qc = promote.qc_record("chest", lod, manifest, validation, runtime_report, inherited, {})
                actual = validation["lods"][str(lod)]["modules"]["chest"]["source_records"]
                self.assertEqual(qc["provenance"]["sourceRecords"], actual)
                if lod:
                    self.assertNotEqual(qc["provenance"]["sourceRecords"], inherited["sourceRecords"])
                qc["provenance"]["sourceRecords"][0]["finishing"][0]["level"] = 99
                self.assertNotEqual(actual[0]["finishing"][0]["level"], 99)
        self.assertEqual(inherited, original)


class ProvenanceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.validation = {"lods": {"0": {"modules": {"body": {"source_records": [{"file": "source/head.json"}]}}}}}
        runtime = self.root / "runtime"
        runtime.mkdir()
        self.archive = runtime / "evaluated_lods.json.gz"
        self.archive.write_bytes(b"fixture evaluated mesh archive")
        self.validation["runtime_directory"] = str(runtime)
        self.validation["evaluated_mesh_archive"] = {"file": self.archive.name,
            "sha256": promote.file_hash(self.archive), "bytes": self.archive.stat().st_size}
        for relative in ("source/head.json", "source/CONTRACT.md", "source/FULL_CHARACTER_CONTRACT.md", "source/scene.json",
                         "tools/build_proof.py", "tools/rig_character.py", "tools/bake_atlas.py", "tools/validate_runtime.py",
                         "tools/promote_runtime.py", "tools/correct_animation.py", "tools/tessellate_runtime.py"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("fixture source: " + relative).encode())

    def tearDown(self):
        self.temp.cleanup()

    def test_archive_includes_actual_motion_and_tangent_helper_bytes(self):
        sources = promote.provenance_source_paths(self.root, self.validation)
        for relative in ("tools/correct_animation.py", "tools/tessellate_runtime.py"):
            self.assertEqual(sources[relative].read_bytes(), ("fixture source: " + relative).encode())
        self.assertEqual(sources["source/head.json"], self.root / "source/head.json")

    def test_archive_includes_exact_validated_evaluated_mesh_bytes(self):
        sources = promote.provenance_source_paths(self.root, self.validation)
        self.assertEqual(sources["runtime/evaluated_lods.json.gz"], self.archive)
        self.assertEqual(promote.file_hash(sources["runtime/evaluated_lods.json.gz"]),
                         self.validation["evaluated_mesh_archive"]["sha256"])

    def test_missing_evaluated_archive_blocks_preparation(self):
        self.archive.unlink()
        with self.assertRaisesRegex(promote.PromotionError, "evaluated mesh archive is missing or changed"):
            promote.provenance_source_paths(self.root, self.validation)

    def test_changed_evaluated_archive_blocks_preparation(self):
        self.archive.write_bytes(b"changed archive after validation")
        with self.assertRaisesRegex(promote.PromotionError, "evaluated mesh archive is missing or changed"):
            promote.provenance_source_paths(self.root, self.validation)

    def test_legacy_validation_without_archive_record_blocks_preparation(self):
        del self.validation["evaluated_mesh_archive"]
        with self.assertRaisesRegex(promote.PromotionError, "missing the evaluated mesh archive record"):
            promote.provenance_source_paths(self.root, self.validation)

    def test_missing_motion_helper_prevents_archive_preparation(self):
        (self.root / "tools/correct_animation.py").unlink()
        with self.assertRaisesRegex(promote.PromotionError, "Provenance source is missing: tools/correct_animation.py"):
            promote.provenance_source_paths(self.root, self.validation)

    def test_missing_tangent_helper_prevents_archive_preparation(self):
        (self.root / "tools/tessellate_runtime.py").unlink()
        with self.assertRaisesRegex(promote.PromotionError, "Provenance source is missing: tools/tessellate_runtime.py"):
            promote.provenance_source_paths(self.root, self.validation)

    def test_source_record_cannot_escape_authoring_root(self):
        self.validation["lods"]["0"]["modules"]["body"]["source_records"] = [{"file": "../outside.py"}]
        with self.assertRaisesRegex(promote.PromotionError, "escapes intended directory"):
            promote.provenance_source_paths(self.root, self.validation)


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.author = base / "author"
        self.repo = base / "target"
        self.author.mkdir()
        self.repo.mkdir()
        allowed = self.repo / promote.PIPELINE / "data/runtime-compatibility-allowlist.json"
        allowed.parent.mkdir(parents=True)
        allowed.write_text('{"assets": []}')
        self.stage = self.author / "promotion/reference-aaaaaaaaaaaa-bbbbbbbb"
        self.publication = self.stage / "publication"
        self.publication.mkdir(parents=True)
        validation = self.author / "validation.json"
        review = self.author / "review.json"
        validation.write_text("{}")
        review.write_text("{}")
        self.old_relative = (promote.MODELS / "arm_civic_battle_prelate_back_t1_m.glb").as_posix()
        old = self.repo / self.old_relative
        old.parent.mkdir(parents=True)
        old.write_bytes(b"previous user asset")
        entries = {}
        for relative in promote.CORE_DESTINATIONS:
            destination = self.publication / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload = b"test payload:" + relative.encode()
            destination.write_bytes(payload)
            entries[relative] = {"sha256": promote.sha256(payload), "previous_sha256": promote.file_hash(self.repo / relative), "bytes": len(payload)}
        self.plan = {"status": "prepared", "transaction": "reference-aaaaaaaaaaaa-bbbbbbbb", "target_repo": str(self.repo), "authoring_root": str(self.author),
                     "runtime": str(self.author / "runtime"), "validation_path": str(validation), "validation_sha256": promote.file_hash(validation),
                     "review_path": str(review), "review_sha256": promote.file_hash(review), "registry_inputs": promote.registry_inputs(self.repo), "publication": entries}
        self.plan_path = self.stage / "promotion_plan.json"
        self.plan_path.write_bytes(promote.json_bytes(self.plan))

    def tearDown(self):
        self.temp.cleanup()

    def test_source_change_after_prepare_is_rejected(self):
        (self.publication / self.old_relative).write_bytes(b"changed")
        with self.assertRaisesRegex(promote.PromotionError, "Prepared file changed"):
            promote.check_preconditions(self.plan, self.stage, self.repo, self.author)

    def test_dirty_target_edit_after_prepare_is_preserved(self):
        (self.repo / self.old_relative).write_bytes(b"concurrent user edit")
        with self.assertRaisesRegex(promote.PromotionError, "Target changed"):
            promote.check_preconditions(self.plan, self.stage, self.repo, self.author)
        self.assertEqual((self.repo / self.old_relative).read_bytes(), b"concurrent user edit")

    def test_plan_cannot_silently_omit_one_module(self):
        del self.plan["publication"][self.old_relative]
        with self.assertRaisesRegex(promote.PromotionError, "omits required"):
            promote.check_preconditions(self.plan, self.stage, self.repo, self.author)

    def test_apply_archives_previous_files_and_leaves_unrelated_changes(self):
        unrelated = self.repo / "user_notes.txt"
        unrelated.write_text("keep me")
        with patch.object(promote, "verify_inputs"):
            result = promote.apply(self.plan_path, self.repo, self.author)
        self.assertEqual(result["status"], "promoted_local")
        self.assertEqual((Path(result["archive"]) / "previous" / self.old_relative).read_bytes(), b"previous user asset")
        self.assertEqual(unrelated.read_text(), "keep me")
        self.assertEqual(promote.file_hash(self.repo / self.old_relative), self.plan["publication"][self.old_relative]["sha256"])

    def test_copy_failure_restores_prior_asset(self):
        real_copy = promote.atomic_copy
        calls = 0
        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated interrupted publication")
            return real_copy(source, target)
        with patch.object(promote, "verify_inputs"), patch.object(promote, "atomic_copy", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "simulated"):
                promote.apply(self.plan_path, self.repo, self.author)
        self.assertEqual((self.repo / self.old_relative).read_bytes(), b"previous user asset")
        self.assertEqual(promote.read_json(self.plan_path)["status"], "prepared")


if __name__ == "__main__":
    unittest.main()
