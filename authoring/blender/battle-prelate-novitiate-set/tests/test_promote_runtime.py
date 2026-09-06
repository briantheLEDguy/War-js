"""Additive promotion checks using temporary fixtures, never game assets."""
import base64
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import promote_runtime as promote


def passed_report():
    return {"status": "passed", "errors": [], "full_bundle_requested": True, "stage_report_sha256": "c"*64,
            "lods": {str(lod): {"complete": True, "modules": {slot: {"model": promote.model_name(slot, lod), "sha256": "a"*64}
                     for slot in promote.SLOTS}} for lod in (0, 1, 2)}}


def manifests():
    return [promote.module_manifest_metadata({"category": "armor", "compatibility": {"bodyFamily": "civic_battle_prelate_m",
            "bodyVariant": "m", "skeletonId": "humanoid_game_v2", "bindPoseId": "a_pose_v2"}}, slot) for slot in promote.PUBLISH_SLOTS]


class AdditiveScopeTests(unittest.TestCase):
    def test_only_new_armor_destinations_are_publishable(self):
        self.assertEqual(len(promote.MODEL_NAMES), 27)
        self.assertEqual(len(promote.MANIFEST_NAMES), 9)
        self.assertEqual(len(promote.CORE_DESTINATIONS), 64)
        for slot in promote.PUBLISH_SLOTS:
            for lod in (0, 1, 2):
                self.assertTrue(promote.allowed_destination(promote.MODELS / promote.model_name(slot, lod)))
        for slot in promote.SHARED_SLOTS:
            for lod in (0, 1, 2):
                self.assertFalse(promote.allowed_destination(promote.MODELS / promote.model_name(slot, lod)))
        for path in ("src/game/Player.ts", "public/assets/models/arm_civic_battle_prelate_chest_t1_m.glb",
                     "authoring/archives/battle-prelate-novitiate-set/x/../../escape.py",
                     "public/assets/models/arm_civic_battle_prelate_chest_novitiate_f.glb"):
            self.assertFalse(promote.allowed_destination(path))

    def test_full_assembly_validation_remains_required(self):
        report = passed_report()
        self.assertEqual(len(promote.expected_hashes(report)), 33)
        for mutation in (lambda r: r.update(status="failed"), lambda r: r.update(full_bundle_requested=False),
                         lambda r: r["lods"]["0"]["modules"].pop("body"),
                         lambda r: r["lods"]["0"]["modules"]["chest"].update(model="old.glb")):
            changed = copy.deepcopy(report); mutation(changed)
            with self.assertRaises(promote.PromotionError): promote.expected_hashes(changed)

    def test_manifest_is_additive_and_does_not_mutate_template(self):
        template = {"assetId": "old", "category": "armor", "runtime": {"itemKey": "starter_chest"},
                    "compatibility": {"bodyVariant": "m", "coveredRegions": ["torso"]}}
        before = copy.deepcopy(template)
        candidate = promote.module_manifest_metadata(template, "chest")
        self.assertEqual(template, before)
        self.assertEqual(candidate["assetId"], "arm.civic.battle_prelate.chest.novitiate.m")
        self.assertEqual(candidate["runtime"]["itemKey"], "novitiate_civic_battle_prelate_chest_m")
        self.assertTrue(candidate["runtime"]["skinned"])
        self.assertEqual(candidate["compatibility"], template["compatibility"])
        with self.assertRaises(promote.PromotionError): promote.module_manifest_metadata(template, "body")

    def test_compiled_scope_preserves_complete_existing_registry(self):
        candidates = manifests()
        before = {"assetVersion": "before", "characterProfiles": {"body": {"model": "body.glb"}},
                  "equipment": {"ornate": {"variants": {"m": {"model": "ornate.glb"}}}}}
        after = copy.deepcopy(before); after["assetVersion"] = "after"
        for manifest in candidates:
            after["equipment"][manifest["runtime"]["itemKey"]] = {"variants": {"m": {
                "model": manifest["model"], "assetId": manifest["assetId"]}}}
        promote.assert_registry_scope(before, after, candidates)
        altered = copy.deepcopy(after); altered["characterProfiles"]["body"]["model"] = "changed.glb"
        with self.assertRaisesRegex(promote.PromotionError, "unrelated registry"):
            promote.assert_registry_scope(before, altered, candidates)
        altered = copy.deepcopy(after); altered["equipment"]["ornate"]["variants"]["m"]["model"] = "changed.glb"
        with self.assertRaisesRegex(promote.PromotionError, "unrelated registry"):
            promote.assert_registry_scope(before, altered, candidates)
        altered = copy.deepcopy(after); altered["equipment"].pop(candidates[0]["runtime"]["itemKey"])
        with self.assertRaisesRegex(promote.PromotionError, "omitted"):
            promote.assert_registry_scope(before, altered, candidates)
        with self.assertRaisesRegex(promote.PromotionError, "exactly nine"):
            promote.assert_registry_scope(before, after, candidates[:-1])


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


class SourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'battle-prelate-novitiate-set'
        self.original = self.root.parent / 'battle-prelate-reference-rebuild'
        for folder in (self.root / 'source', self.root / 'tools', self.root / 'runtime', self.root / 'textures/source', self.original / 'source'):
            folder.mkdir(parents=True, exist_ok=True)
        self.records = {}
        for slot, root in [('chest', self.root), ('body', self.original)]:
            path = root / 'source' / f'{slot}.json'
            path.write_bytes(('source ' + slot).encode())
            self.records[slot] = {'file': f'source/{slot}.json', 'sha256': promote.file_hash(path), 'part': slot}
        for name in promote.AUTHORING_INPUTS:
            (self.root / name).write_bytes(b'fixture')
        self.paint_manifest = {'paint_source_sha256': promote.file_hash(self.root / 'textures/paint_strokes.json'), 'materials': {'cloth': {'maps': {}}}}
        for channel in ('basecolor', 'roughness', 'metallic', 'height'):
            path = self.root / 'textures/source' / ('cloth_' + channel + '.png')
            path.write_bytes(b'fixture pixel bytes ' + channel.encode())
            self.paint_manifest['materials']['cloth']['maps'][channel] = {'path': 'source/' + path.name, 'sha256': promote.file_hash(path)}
        (self.root / 'textures/source/skin_basecolor.png').write_bytes(b'unchanged shared skin map')
        (self.root / 'textures/paint_manifest.json').write_bytes(promote.json_bytes(self.paint_manifest))
        archive = self.root / 'runtime' / promote.EVALUATED_ARCHIVE_NAME
        archive.write_bytes(b'evaluated fixture')
        self.validation = {'runtime_directory': str(self.root / 'runtime'),
                           'evaluated_mesh_archive': {'file': promote.EVALUATED_ARCHIVE_NAME, 'sha256': promote.file_hash(archive)},
                           'lods': {'0': {'modules': {slot: {'source_records': [record]} for slot, record in self.records.items()}}}}
        self.stage = {'lods': {'0': {'modules': {'chest': {}, 'body': {'shared_asset': {'package': 'battle-prelate-reference-rebuild'}}}}}}
        (self.root / 'runtime/runtime_report.json').write_bytes(promote.json_bytes(self.stage))

    def tearDown(self):
        self.temp.cleanup()

    def test_shared_sources_are_archived_separately_from_new_armor(self):
        paths = promote.provenance_source_paths(self.root, self.validation)
        self.assertEqual(paths['source/chest.json'], self.root / 'source/chest.json')
        self.assertEqual(paths['shared_source/source/body.json'], self.original / 'source/body.json')
        self.assertIn('tools/author_novitiate_core.py', paths)
        self.assertIn('tools/refine_novitiate_cloth.py', paths)
        self.assertIn('tools/refine_novitiate_paint.py', paths)
        self.assertIn('tools/paint_materials.py', paths)
        self.assertIn('textures/paint_strokes.json', paths)
        self.assertIn('textures/paint_manifest.json', paths)
        self.assertIn('textures/source/skin_basecolor.png', paths)
        self.assertIn('textures/source/cloth_height.png', paths)
        self.assertIn('runtime/' + promote.EVALUATED_ARCHIVE_NAME, paths)

    def test_changed_shared_source_is_rejected(self):
        (self.original / 'source/body.json').write_bytes(b'changed')
        with self.assertRaisesRegex(promote.PromotionError, 'missing or changed'):
            promote.provenance_source_paths(self.root, self.validation)

    def test_shared_source_requires_the_same_stage_flag_as_binary_validation(self):
        self.stage['lods']['0']['modules']['body'].pop('shared_asset')
        (self.root / 'runtime/runtime_report.json').write_bytes(promote.json_bytes(self.stage))
        with self.assertRaisesRegex(promote.PromotionError, 'provenance flag is missing'):
            promote.provenance_source_paths(self.root, self.validation)

    def test_shared_record_cannot_escape_original_source_package(self):
        self.records['body']['file'] = '../../outside.json'
        with self.assertRaisesRegex(promote.PromotionError, 'escapes intended directory'):
            promote.provenance_source_paths(self.root, self.validation)

    def test_required_variant_authoring_helper_cannot_be_omitted(self):
        (self.root / 'tools/author_novitiate_limbs.py').unlink()
        with self.assertRaisesRegex(promote.PromotionError, 'author_novitiate_limbs.py'):
            promote.provenance_source_paths(self.root, self.validation)

    def test_paint_helpers_and_record_are_required(self):
        for relative in ('tools/refine_novitiate_paint.py', 'tools/refine_novitiate_cloth.py', 'tools/paint_materials.py', 'textures/paint_strokes.json'):
            with self.subTest(relative=relative):
                path = self.root / relative
                previous = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(promote.PromotionError, 'Provenance source is missing'):
                    promote.provenance_source_paths(self.root, self.validation)
                path.write_bytes(previous)

    def test_paint_manifest_must_bind_record_and_all_channel_bytes(self):
        record = self.root / 'textures/paint_strokes.json'
        previous = record.read_bytes()
        record.write_bytes(b'changed stroke')
        with self.assertRaisesRegex(promote.PromotionError, 'different authored paint record'):
            promote.provenance_source_paths(self.root, self.validation)
        record.write_bytes(previous)
        path = self.root / 'textures/source/cloth_height.png'
        path.write_bytes(b'changed map')
        with self.assertRaisesRegex(promote.PromotionError, 'Paint map is missing or changed'):
            promote.provenance_source_paths(self.root, self.validation)

    def test_paint_channel_omission_and_external_map_are_rejected(self):
        manifest = copy.deepcopy(self.paint_manifest)
        del manifest['materials']['cloth']['maps']['height']
        (self.root / 'textures/paint_manifest.json').write_bytes(promote.json_bytes(manifest))
        with self.assertRaisesRegex(promote.PromotionError, 'required authored channel'):
            promote.provenance_source_paths(self.root, self.validation)
        manifest = copy.deepcopy(self.paint_manifest)
        manifest['materials']['cloth']['maps']['height']['path'] = '../source/chest.json'
        (self.root / 'textures/paint_manifest.json').write_bytes(promote.json_bytes(manifest))
        with self.assertRaisesRegex(promote.PromotionError, 'escapes intended directory'):
            promote.provenance_source_paths(self.root, self.validation)

    def test_source_ledger_binds_all_exact_copied_payloads(self):
        paths = promote.provenance_source_paths(self.root, self.validation)
        payloads, ledger_bytes = promote.source_archive_payloads(paths)
        ledger = json.loads(ledger_bytes)
        self.assertEqual(set(ledger['files']), set(paths))
        for name, data in payloads.items():
            self.assertEqual(ledger['files'][name], {'sha256': promote.sha256(data), 'bytes': len(data)})
        (self.root / 'textures/source/skin_basecolor.png').write_bytes(b'later source edit')
        self.assertEqual(payloads['textures/source/skin_basecolor.png'], b'unchanged shared skin map')


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
        self.stage = self.author / "promotion/novitiate-aaaaaaaaaaaa-bbbbbbbb"
        self.publication = self.stage / "publication"
        self.publication.mkdir(parents=True)
        validation = self.author / "validation.json"
        review = self.author / "review.json"
        validation.write_text("{}")
        review.write_text("{}")
        self.old_relative = (promote.MODELS / "arm_civic_battle_prelate_back_novitiate_m.glb").as_posix()
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
        shared = {}
        for slot in promote.SHARED_SLOTS:
            for lod in (0, 1, 2):
                path = self.repo / promote.MODELS / promote.model_name(slot, lod)
                path.write_bytes(b"unchanged original body or weapon")
                shared[path.relative_to(self.repo).as_posix()] = promote.file_hash(path)
        self.plan = {"status": "prepared", "transaction": "novitiate-aaaaaaaaaaaa-bbbbbbbb", "target_repo": str(self.repo), "authoring_root": str(self.author),
                     "runtime": str(self.author / "runtime"), "validation_path": str(validation), "validation_sha256": promote.file_hash(validation),
                     "review_path": str(review), "review_sha256": promote.file_hash(review), "registry_inputs": promote.registry_inputs(self.repo), "shared_assets": shared, "publication": entries}
        self.plan_path = self.stage / "promotion_plan.json"
        self.plan_path.write_bytes(promote.json_bytes(self.plan))

    def tearDown(self):
        self.temp.cleanup()

    def test_shared_model_change_is_rejected_without_replacing_it(self):
        relative = next(iter(self.plan["shared_assets"]))
        (self.repo / relative).write_bytes(b"concurrent original body change")
        with self.assertRaisesRegex(promote.PromotionError, "shared asset changed"):
            promote.check_preconditions(self.plan, self.stage, self.repo, self.author)
        self.assertEqual((self.repo / relative).read_bytes(), b"concurrent original body change")

    def test_shared_dependency_cannot_be_added_to_publication(self):
        relative = next(iter(self.plan["shared_assets"]))
        self.plan["publication"][relative] = {"sha256": "a"*64, "previous_sha256": "b"*64}
        with self.assertRaisesRegex(promote.PromotionError, "Unapproved publication"):
            promote.check_preconditions(self.plan, self.stage, self.repo, self.author)

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
        promote.check_shared_assets(self.repo, self.plan["shared_assets"])
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
