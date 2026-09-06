"""Prepare/apply a hash-guarded local promotion; never builds or approves a model.

Preparation writes only below this authoring root. Applying a prepared plan is an
explicit command, requires fresh technical/review evidence, and archives every
overwritten file before changing the named target repository. No Git operation,
deployment, game code edit, or automatic visual acceptance is performed.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from validate_runtime import EVALUATED_ARCHIVE_NAME, ROOT, SLOTS, model_name, sha256, validate_bundle

MODELS = Path("public/assets/models")
APPROVED = Path("scripts/blender-character-pipeline/data/approved-assets")
PIPELINE = Path("scripts/blender-character-pipeline")
PUBLISH_SLOTS = tuple(slot for slot in SLOTS if slot not in {"body", "weapon"})
SHARED_SLOTS = ("body", "weapon")
MODEL_NAMES = {model_name(slot, lod) for slot in PUBLISH_SLOTS for lod in (0, 1, 2)}
MANIFEST_NAMES = {model_name(slot, 0).replace(".glb", ".approved.json") for slot in PUBLISH_SLOTS}
CORE_DESTINATIONS = {(MODELS / name).as_posix() for name in MODEL_NAMES}
CORE_DESTINATIONS |= {(MODELS / name.replace(".glb", ".qc.json")).as_posix() for name in MODEL_NAMES}
CORE_DESTINATIONS |= {(APPROVED / name).as_posix() for name in MANIFEST_NAMES}
CORE_DESTINATIONS.add((MODELS / "asset-index.json").as_posix())
REVIEW_CHECKS = {"reference_design", "material_response", "module_fit", "animation_stress", "weapon_socket", "lod_silhouette"}
REVIEW_VIEWS = {"front", "side", "back", "isometric"}
AUTHORING_INPUTS = (
    "DESIGN.md", "source/CONTRACT.md", "source/FULL_CHARACTER_CONTRACT.md", "source/scene.json",
    "tools/build_proof.py", "tools/rig_character.py", "tools/bake_atlas.py", "tools/correct_animation.py",
    "tools/tessellate_runtime.py", "tools/validate_runtime.py", "tools/promote_runtime.py",
    "tools/author_novitiate_core.py", "tools/author_novitiate_upper.py", "tools/author_novitiate_limbs.py",
    "tools/refine_novitiate_cloth.py", "tools/refine_novitiate_paint.py", "tools/paint_materials.py",
    "textures/paint_strokes.json", "textures/paint_manifest.json",
)


class PromotionError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PromotionError(message)


def within(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    require(path.is_relative_to(root) and path != root, f"Path escapes intended directory: {path}")
    return path


def file_hash(path):
    path = Path(path)
    return sha256(path.read_bytes()) if path.is_file() else None


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def expected_hashes(report):
    require(report.get("status") == "passed" and not report.get("errors"), "Full technical validation has not passed")
    require(report.get("full_bundle_requested") is True and set(report.get("lods", {})) == {"0", "1", "2"}, "Partial LOD validation cannot authorize promotion")
    hashes = {}
    for lod in (0, 1, 2):
        record = report["lods"][str(lod)]
        require(record.get("complete") is True and set(record.get("modules", {})) == set(SLOTS), f"LOD{lod} is incomplete")
        for slot in SLOTS:
            module = record["modules"][slot]
            name = model_name(slot, lod)
            require(module.get("model") == name, f"Unexpected model name for LOD{lod}/{slot}")
            digest = module.get("sha256", "")
            require(isinstance(digest, str) and re.fullmatch("[a-f0-9]{64}", digest), f"Missing model hash for {name}")
            hashes[name] = digest
    return hashes


def validate_review(review, review_path, validation_path, validation, authoring_root=ROOT):
    require(review.get("status") == "accepted_for_local_runtime", "A completed local visual review is required")
    require(bool(review.get("reviewed_by")) and bool(review.get("reviewed_at")), "Visual review must identify reviewer and time")
    require(review.get("validation_report_sha256") == file_hash(validation_path), "Visual review is tied to a different validation report")
    require(review.get("runtime_report_sha256") == validation.get("stage_report_sha256"), "Visual review is tied to a different runtime build")
    require(review.get("model_hashes") == expected_hashes(validation), "Visual review does not cover the exact 33 model hashes")
    require(all(review.get("checks", {}).get(name) == "passed" for name in REVIEW_CHECKS), "Visual review has unresolved design/material/fit/animation/socket/LOD checks")
    require(isinstance(review.get("findings"), list), "Visual review must include findings, even when empty")
    require(not any(f.get("blocking", False) for f in review["findings"]), "Visual review contains a blocking finding")
    evidence = review.get("evidence", [])
    require(isinstance(evidence, list) and evidence, "Visual review has no local image evidence")
    equipped = {e.get("view") for e in evidence if e.get("scope") == "equipped"}
    require(REVIEW_VIEWS.issubset(equipped), "Visual review needs final equipped front/side/back/isometric images")
    require(any(e.get("scope") == "animation_stress" for e in evidence), "Visual review needs a local animation stress image/contact sheet")
    paths = []
    seen = set()
    for entry in evidence:
        require(isinstance(entry, dict), "Malformed visual evidence record")
        name = entry.get("id", "")
        require(re.fullmatch("[a-z0-9_-]+", name) and name not in seen, "Evidence ids must be unique lowercase names")
        seen.add(name)
        path = within(authoring_root, Path(authoring_root) / entry.get("path", ""))
        require(path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}, "Evidence must be a local raster preview")
        require(file_hash(path) == entry.get("sha256") and path.is_file(), f"Visual evidence is missing or changed: {name}")
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        paths.append((entry, path))
    return paths


def verify_inputs(runtime, validation_path, review_path, authoring_root=ROOT):
    runtime = within(authoring_root, runtime)
    validation_path = within(authoring_root, validation_path)
    review_path = within(authoring_root, review_path)
    validation = read_json(validation_path)
    expected = expected_hashes(validation)
    require(Path(validation.get("runtime_directory", "")).resolve() == runtime, "Validation points at a different runtime directory")
    require(file_hash(runtime / "runtime_report.json") == validation.get("stage_report_sha256"), "Runtime build report changed after validation")
    for name, digest in expected.items():
        require(file_hash(runtime / name) == digest, f"Runtime model changed after validation: {name}")
    fresh = validate_bundle(runtime)
    require(fresh["status"] == "passed", "Fresh binary validation failed: " + "; ".join(fresh["errors"][:8]))
    require(fresh["assets"] == validation.get("assets"), "Validated bundle assets changed")
    require(expected_hashes(fresh) == expected, "Fresh model hashes differ from accepted evidence")
    require(fresh.get("evaluated_mesh_archive") == validation.get("evaluated_mesh_archive"), "Validated evaluated mesh archive changed")
    review = read_json(review_path)
    evidence = validate_review(review, review_path, validation_path, validation, authoring_root)
    return validation, review, evidence


def allowed_destination(relative):
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        return False
    if relative.parent == MODELS:
        return relative.name in MODEL_NAMES or relative.name.replace(".qc.json", ".glb") in MODEL_NAMES or relative.name == "asset-index.json"
    if relative.parent == APPROVED:
        return relative.name in MANIFEST_NAMES
    parts = relative.parts
    return (len(parts) >= 6 and parts[:5] == ("public", "assets", "models", "reviews", "battle-prelate-novitiate-set")) or (
        len(parts) >= 5 and parts[:3] == ("authoring", "archives", "battle-prelate-novitiate-set"))


def assert_registry_scope(before, after, manifests):
    expected = {f"novitiate_civic_battle_prelate_{slot}_m" for slot in PUBLISH_SLOTS}
    require(len(manifests) == len(PUBLISH_SLOTS) and {m.get("runtime", {}).get("itemKey") for m in manifests} == expected,
            "Scope requires exactly nine Novitiate armor item keys")
    require(all(m.get("runtime", {}).get("bodyVariant") == "m" and "profileKey" not in m["runtime"] for m in manifests),
            "Scope permits only male armor variants")
    for manifest in manifests:
        item = after.get("equipment", {}).get(manifest["runtime"]["itemKey"], {}).get("variants", {}).get("m", {})
        require(item.get("model") == manifest["model"] and item.get("assetId") == manifest["assetId"],
                "Compiler omitted or changed a Novitiate armor entry")
    before, after = copy.deepcopy(before), copy.deepcopy(after)
    for registry in (before, after):
        registry.pop("assetVersion", None)
        for manifest in manifests:
            runtime = manifest["runtime"]
            if "profileKey" in runtime:
                registry.get("characterProfiles", {}).pop(runtime["profileKey"], None)
            else:
                equipment = registry.get("equipment", {})
                logical = equipment.get(runtime["itemKey"], {})
                logical.get("variants", {}).pop("m", None)
                if logical == {"variants": {}}:
                    equipment.pop(runtime["itemKey"], None)
    require(before == after, "Compiler would change unrelated registry entries; resolve existing registry/manifest drift separately")


def registry_inputs(repo):
    paths = list((repo / APPROVED).glob("*.approved.json"))
    paths += list((repo / PIPELINE / "tools").glob("*.mjs"))
    paths += [repo / PIPELINE / "data/approved-asset.schema.json", repo / PIPELINE / "data/runtime-compatibility-allowlist.json",
              repo / PIPELINE / "config.json", repo / MODELS / "asset-index.json"]
    # Compatibility entries are included only while the referenced file exists.
    allowed = read_json(repo / PIPELINE / "data/runtime-compatibility-allowlist.json")
    result = {str(p.relative_to(repo)).replace("\\", "/"): file_hash(p) for p in sorted(set(paths))}
    for entry in allowed.get("assets", []):
        path = within(repo, repo / MODELS / entry["model"])
        result["compatibility_exists:" + path.relative_to(repo).as_posix()] = path.is_file()
    return result


def compile_registry(repo, manifests, output, node):
    inputs = output.parent / "candidate_manifests.json"
    inputs.write_bytes(json_bytes(manifests))
    code = """import {readFileSync,writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const mod=await import(pathToFileURL(process.argv[1]).href);
const manifests=JSON.parse(readFileSync(process.argv[2],'utf8'));
writeFileSync(process.argv[3],JSON.stringify(mod.compileRuntimeRegistry({additionalManifests:manifests}),null,2)+'\\n');
"""
    result = subprocess.run([str(node), "--input-type=module", "-e", code, str(repo / PIPELINE / "tools/runtime-registry.mjs"), str(inputs), str(output)],
                            cwd=repo, capture_output=True, text=True, check=False)
    require(result.returncode == 0, "Existing registry compiler rejected prepared manifests: " + result.stderr[-4000:])


def qc_record(slot, lod, manifest, validation, runtime_report, provenance, previews):
    module = validation["lods"][str(lod)]["modules"][slot]
    stage = runtime_report["lods"][str(lod)]["modules"][slot]
    # A manifest describes LOD0; each QC sidecar must describe its own GLB.
    provenance = dict(provenance, sourceRecords=copy.deepcopy(module["source_records"]))
    for name in ("boundary_edges", "nonmanifold_edges", "degenerate_triangles"):
        require(stage.get(name) == 0, f"Build topology audit failed or missing for {slot}/LOD{lod}: {name}")
    maximum = max((max(info["width"], info["height"]) for mat in module["materials"] for info in mat["channels"].values()), default=0)
    return {"schemaVersion": 1, "assetId": manifest["assetId"], "model": module["model"], "modelSha256": module["sha256"],
            "fileSizeBytes": module["bytes"], "category": manifest["category"], "slot": slot, "lod": lod,
            **manifest["compatibility"], "lifecycleStatus": "approved", "reviewStatus": "approved", "promotionEligible": True,
            "totalTriangles": module["triangles"], "totalTris": module["triangles"], "drawCalls": module["draw_calls"],
            "meshCount": len({g["mesh"] for g in module["geometry"]}), "maxInfluencesObserved": module["max_influences"],
            "unweightedVertices": 0, "nonManifoldEdges": stage["nonmanifold_edges"], "boundaryEdges": stage["boundary_edges"],
            "degenerateFaces": stage["degenerate_triangles"], "pbrChannels": ["baseColor", "normal", "roughness", "metallic", "occlusion"],
            "maxTextureDimension": maximum, "maxTextureResolution": maximum, "animationClips": [a["name"] for a in module["animations"]],
            "builtLods": [{"name": f"LOD{level}", "model": model_name(slot, level),
                           "sha256": validation["lods"][str(level)]["modules"][slot]["sha256"]} for level in (0, 1, 2)],
            "lodRuntimeStatus": "LOD0 mapped; LOD1/2 published, no current runtime distance switching",
            "previewImages": list(previews.values()), "previewScope": "equipped final character; shared context for modular armor",
            "previews": [{"view": view, "path": path} for view, path in previews.items()], "provenance": provenance,
            "checks": {"freshBinaryValidation": True, "matchingReviewEvidence": True, "matchingSourceHashes": True,
                       "topologyBuildAudit": True, "requiredPbrMaps": True, "triangleBudget": True, "drawCallBudget": True}, "qcPassed": True}


def provenance_source_paths(authoring_root, validation):
    authoring_root = Path(authoring_root).resolve()
    runtime = within(authoring_root, validation.get("runtime_directory", ""))
    stage = read_json(runtime / "runtime_report.json")
    sources = {}
    for level, lod in validation["lods"].items():
        for slot, module in lod["modules"].items():
            flag = stage["lods"][level]["modules"][slot].get("shared_asset")
            shared = slot in SHARED_SLOTS and bool(flag)
            require(shared == (slot in SHARED_SLOTS), "Shared body/weapon provenance flag is missing")
            require(not flag or shared, "New armor must not declare a shared asset")
            source_root = authoring_root.parent / "battle-prelate-reference-rebuild" if shared else authoring_root
            for record in module["source_records"]:
                relative = Path(record["file"])
                source = within(source_root, source_root / relative)
                require(source.is_relative_to(source_root / "source"), "Source records must remain in the source directory")
                require(source.is_file() and file_hash(source) == record["sha256"], f"Provenance source is missing or changed: {relative}")
                key = ((Path("shared_source") / relative) if shared else relative).as_posix()
                sources[key] = source
    for relative in AUTHORING_INPUTS:
        source = within(authoring_root, authoring_root / relative)
        require(source.is_file(), f"Provenance source is missing: {relative}")
        sources[relative] = source
    paint = read_json(authoring_root / "textures/paint_manifest.json")
    require(paint.get("paint_source_sha256") == file_hash(authoring_root / "textures/paint_strokes.json"),
            "Paint manifest refers to a different authored paint record")
    require(isinstance(paint.get("materials"), dict) and paint["materials"], "Paint manifest has no materials")
    texture_root = authoring_root / "textures/source"
    for material in paint["materials"].values():
        require(set(material.get("maps", {})) == {"basecolor", "roughness", "metallic", "height"},
                "Paint manifest omits a required authored channel")
        for record in material["maps"].values():
            path = within(authoring_root / "textures", authoring_root / "textures" / record.get("path", ""))
            require(path.is_relative_to(texture_root) and path.suffix == ".png", "Paint map must remain in textures/source")
            require(path.is_file() and file_hash(path) == record.get("sha256"), f"Paint map is missing or changed: {path.name}")
    # Include inherited skin/chainmail source maps too; the ledger identifies the
    # exact bytes, while shared body/weapon GLBs remain unchanged and unpublished.
    for source in sorted(texture_root.glob("*.png")):
        source = within(texture_root, source)
        sources[source.relative_to(authoring_root).as_posix()] = source
    archive = validation.get("evaluated_mesh_archive")
    require(isinstance(archive, dict) and archive.get("file") == EVALUATED_ARCHIVE_NAME,
            "Validation is missing the evaluated mesh archive record")
    archive_path = within(runtime, runtime / EVALUATED_ARCHIVE_NAME)
    require(archive_path.is_file() and file_hash(archive_path) == archive.get("sha256"),
            "Validated evaluated mesh archive is missing or changed")
    sources["runtime/" + EVALUATED_ARCHIVE_NAME] = archive_path
    return sources


def source_archive_payloads(paths):
    """Bind the ledger to the bytes actually copied into this source archive."""
    payloads = {name: path.read_bytes() for name, path in sorted(paths.items())}
    ledger = json_bytes({"schema_version": 1, "scope": "Exact authoring inputs captured during promotion preparation; runtime validation and visual evidence are separate records",
                         "files": {name: {"sha256": sha256(payload), "bytes": len(payload)} for name, payload in payloads.items()}})
    return payloads, ledger


ARMOR_NAMES = {"head": "Gorget", "shoulders": "Shoulder Plates", "chest": "Cuirass", "hands": "Handguards",
               "waist": "Field Belt", "legs": "Legguards", "feet": "Boots", "back": "Backplate", "tabard": "Tabard"}


def module_manifest_metadata(manifest, slot):
    require(slot in PUBLISH_SLOTS, "Only additional armor modules may be published")
    manifest = copy.deepcopy(manifest)
    manifest["assetId"] = f"arm.civic.battle_prelate.{slot}.novitiate.m"
    manifest["displayName"] = "Novitiate " + ARMOR_NAMES[slot]
    manifest["model"] = model_name(slot, 0)
    manifest["runtime"] = {"itemKey": f"novitiate_civic_battle_prelate_{slot}_m", "bodyVariant": "m", "skinned": True}
    return manifest


def shared_assets(repo, validation):
    expected = expected_hashes(validation)
    result = {(MODELS / model_name(slot, lod)).as_posix(): expected[model_name(slot, lod)]
              for slot in SHARED_SLOTS for lod in (0, 1, 2)}
    check_shared_assets(repo, result)
    return result


def check_shared_assets(repo, records):
    required = {(MODELS / model_name(slot, lod)).as_posix() for slot in SHARED_SLOTS for lod in (0, 1, 2)}
    require(set(records) == required, "Plan must bind all six existing body/weapon assets")
    for relative, digest in records.items():
        require(isinstance(digest, str) and re.fullmatch("[a-f0-9]{64}", digest), "Invalid shared asset hash")
        require(file_hash(within(repo, repo / relative)) == digest, f"Existing shared asset changed: {relative}")


def prepare(repo, runtime, validation_path, review_path, node="node", authoring_root=ROOT):
    authoring_root = Path(authoring_root).resolve()
    repo = Path(repo).resolve()
    require((repo / "package.json").is_file() and (repo / APPROVED).is_dir(), "Explicit target is not a War-js runtime repository")
    validation, review, evidence = verify_inputs(runtime, validation_path, review_path, authoring_root)
    watched = registry_inputs(repo)
    shared = shared_assets(repo, validation)
    baseline = {relative: file_hash(within(repo, repo / relative)) for relative in CORE_DESTINATIONS}
    validation_hash, review_hash = file_hash(validation_path), file_hash(review_path)
    token = validation_hash[:12]
    transaction = f"novitiate-{token}-{uuid.uuid4().hex[:8]}"
    stage = within(authoring_root, authoring_root / "promotion" / transaction)
    stage.mkdir(parents=True, exist_ok=False)
    publication = stage / "publication"
    publication.mkdir()
    entries = {}
    def add(relative, payload):
        relative = Path(relative)
        require(allowed_destination(relative), f"Unapproved publication destination: {relative}")
        destination = within(repo, repo / relative)
        previous = file_hash(destination)
        if relative.as_posix() in baseline:
            require(previous == baseline[relative.as_posix()], f"Target changed during preparation: {relative}")
        staged = within(publication, publication / relative)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(payload)
        entries[relative.as_posix()] = {"sha256": sha256(payload), "previous_sha256": previous, "bytes": len(payload)}
    preview_root = MODELS / "reviews/battle-prelate-novitiate-set" / token
    previews, preview_hashes = {}, {}
    for entry, path in evidence:
        relative = preview_root / (entry["id"] + path.suffix.lower())
        add(relative, path.read_bytes())
        if entry.get("scope") == "equipped" and entry.get("view") in REVIEW_VIEWS:
            previews[entry["view"]] = relative.relative_to(MODELS).as_posix()
            preview_hashes[entry["view"]] = entry["sha256"]
    archive_root = Path("authoring/archives/battle-prelate-novitiate-set") / token
    runtime_report = read_json(Path(runtime) / "runtime_report.json")
    provenance = {"kind": "explicit_novitiate_armor_variant", "geometrySource": "Explicit authored cages adapted from the accepted reference set; permitted finishing only",
                  "rigReuse": "Existing body, warhammer, canonical armature and actions shared unchanged", "sharedAssets": shared,
                  "rigSourceSha256": runtime_report["rig_source_sha256"], "validationReportSha256": validation_hash,
                  "runtimeReportSha256": validation["stage_report_sha256"], "visualReviewSha256": review_hash,
                  "evidenceArchive": archive_root.as_posix(), "authorization": "User requested local game integration when complete; no deployment"}
    for label, source in (("validation_report.json", validation_path), ("visual_review.json", review_path), ("runtime_report.json", Path(runtime)/"runtime_report.json")):
        add(archive_root / label, Path(source).read_bytes())
    source_payloads, source_ledger = source_archive_payloads(provenance_source_paths(authoring_root, validation))
    provenance["sourceLedgerSha256"] = sha256(source_ledger)
    provenance["sourceLedger"] = (archive_root / "source_ledger.json").as_posix()
    add(archive_root / "source_ledger.json", source_ledger)
    for relative, payload in source_payloads.items():
        add(archive_root / relative, payload)
    manifests = []
    for slot in PUBLISH_SLOTS:
        manifest_name = model_name(slot, 0).replace(".glb", ".approved.json")
        template_name = f"arm_civic_battle_prelate_{slot}_t1_m.glb"
        manifest = read_json(repo / APPROVED / template_name.replace(".glb", ".approved.json"))
        require(manifest.get("model") == template_name and manifest.get("compatibility", {}).get("bodyVariant") == "m", "Target manifest does not match the male Battle Prelate module")
        manifest = module_manifest_metadata(manifest, slot)
        module_provenance = dict(provenance, sourceRecords=validation["lods"]["0"]["modules"][slot]["source_records"])
        for lod in (0, 1, 2):
            name = model_name(slot, lod)
            add(MODELS / name, (Path(runtime) / name).read_bytes())
            qc = qc_record(slot, lod, manifest, validation, runtime_report, module_provenance, previews)
            add(MODELS / name.replace(".glb", ".qc.json"), json_bytes(qc))
        manifest["qc"] = model_name(slot, 0).replace(".glb", ".qc.json")
        manifest["hashes"] = {"modelSha256": validation["lods"]["0"]["modules"][slot]["sha256"],
                              "qcSha256": entries[(MODELS / manifest["qc"]).as_posix()]["sha256"], "previews": preview_hashes}
        manifest["previews"] = previews
        manifest["provenance"] = module_provenance
        manifest["review"] = {"reviewedBy": review["reviewed_by"], "reviewedAt": review["reviewed_at"], "reviewHash": review_hash}
        manifest["approvalState"] = "approved"
        manifests.append(manifest)
        add(APPROVED / manifest_name, json_bytes(manifest))
    # External textures retain the GLB-relative path; embedded images need no copy.
    for path in validation["assets"]:
        source = within(runtime, path)
        if source.suffix.lower() != ".glb":
            raise PromotionError("Promotion currently requires self-contained GLBs; re-export with embedded textures before publishing")
    compiled = stage / "compiled_asset_index.json"
    compile_registry(repo, manifests, compiled, node)
    assert_registry_scope(read_json(repo / MODELS / "asset-index.json"), read_json(compiled), manifests)
    add(MODELS / "asset-index.json", compiled.read_bytes())
    require(registry_inputs(repo) == watched, "Registry inputs changed during preparation; prepare a fresh plan")
    plan = {"schema_version": 1, "status": "prepared", "transaction": transaction, "target_repo": str(repo), "authoring_root": str(authoring_root),
            "runtime": str(Path(runtime).resolve()), "validation_path": str(Path(validation_path).resolve()), "validation_sha256": validation_hash,
            "review_path": str(Path(review_path).resolve()), "review_sha256": review_hash, "created_utc": datetime.now(timezone.utc).isoformat(),
            "registry_inputs": watched, "shared_assets": shared, "publication": entries, "lod_runtime_status": "Nine additional LOD0 armor entries; existing body, weapon and ornate set preserved"}
    (stage / "promotion_plan.json").write_bytes(json_bytes(plan))
    return stage / "promotion_plan.json"


def check_preconditions(plan, stage, repo, authoring_root):
    require(plan.get("status") == "prepared", "Plan is not in prepared state")
    require(Path(plan["target_repo"]).resolve() == repo and Path(plan["authoring_root"]).resolve() == authoring_root, "Plan target/authoring directory differs from explicit command")
    require(file_hash(plan["validation_path"]) == plan["validation_sha256"] and file_hash(plan["review_path"]) == plan["review_sha256"], "Validation/review report changed after preparation")
    require(registry_inputs(repo) == plan["registry_inputs"], "Registry inputs changed after preparation; prepare a fresh plan")
    check_shared_assets(repo, plan.get("shared_assets", {}))
    require(CORE_DESTINATIONS.issubset(plan.get("publication", {})), "Prepared plan omits required model/QC/manifest/index files")
    for relative, record in plan["publication"].items():
        require(allowed_destination(relative), f"Unapproved publication path: {relative}")
        target = within(repo, repo / relative)
        source = within(stage / "publication", stage / "publication" / relative)
        require(file_hash(source) == record["sha256"], f"Prepared file changed: {relative}")
        require(file_hash(target) == record["previous_sha256"], f"Target changed after preparation: {relative}")


def atomic_copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".codex-promote-" + uuid.uuid4().hex)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def apply(plan_path, repo, authoring_root=ROOT):
    authoring_root, repo = Path(authoring_root).resolve(), Path(repo).resolve()
    plan_path = within(authoring_root, plan_path)
    stage, plan = plan_path.parent, read_json(plan_path)
    check_preconditions(plan, stage, repo, authoring_root)
    verify_inputs(plan["runtime"], plan["validation_path"], plan["review_path"], authoring_root)
    check_preconditions(plan, stage, repo, authoring_root)
    transaction = plan["transaction"]
    require(re.fullmatch("novitiate-[a-f0-9]{12}-[a-f0-9]{8}", transaction), "Invalid transaction id")
    archive = within(repo, repo / "authoring/archives/battle-prelate-promotions" / transaction)
    archive.mkdir(parents=True, exist_ok=False)
    for relative, record in plan["publication"].items():
        if record["previous_sha256"]:
            backup = within(archive, archive / "previous" / relative)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(within(repo, repo / relative), backup)
            require(file_hash(backup) == record["previous_sha256"], "Target changed while archiving; no replacement started")
    (archive / "promotion_plan.json").write_bytes(json_bytes(plan))
    changed = []
    try:
        order = sorted(plan["publication"], key=lambda p: (p == (MODELS / "asset-index.json").as_posix(), p))
        for relative in order:
            record = plan["publication"][relative]
            target = within(repo, repo / relative)
            require(file_hash(target) == record["previous_sha256"], f"Concurrent target edit detected: {relative}")
            atomic_copy(within(stage / "publication", stage / "publication" / relative), target)
            changed.append(relative)
            require(file_hash(target) == record["sha256"], f"Published hash mismatch: {relative}")
        check_shared_assets(repo, plan["shared_assets"])
    except Exception:
        conflicts = []
        for relative in reversed(changed):
            record = plan["publication"][relative]
            target = within(repo, repo / relative)
            if file_hash(target) != record["sha256"]:
                conflicts.append(relative)
                continue
            if record["previous_sha256"]:
                atomic_copy(within(archive, archive / "previous" / relative), target)
            else:
                target.unlink()
        (archive / "failed_transaction.json").write_bytes(json_bytes({"status": "failed", "rollback_conflicts": conflicts}))
        raise
    plan["status"] = "promoted_local"
    plan["archive"] = str(archive)
    plan["promoted_utc"] = datetime.now(timezone.utc).isoformat()
    (archive / "result.json").write_bytes(json_bytes(plan))
    plan_path.write_bytes(json_bytes(plan))
    return {"status": plan["status"], "files": len(changed), "archive": str(archive), "target_repo": str(repo)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-repo", required=True, type=Path)
    parser.add_argument("--runtime", type=Path, default=ROOT / "runtime")
    parser.add_argument("--validation", type=Path, default=ROOT / "runtime/validation_report.json")
    parser.add_argument("--review", type=Path, default=ROOT / "review/runtime_visual_review.json")
    parser.add_argument("--node", default="node", help="Node executable used by the existing registry compiler")
    parser.add_argument("--apply", type=Path, metavar="PREPARED_PLAN", help="Apply this exact prepared local plan after revalidation")
    args = parser.parse_args()
    try:
        if args.apply:
            result = apply(args.apply, args.target_repo)
        else:
            path = prepare(args.target_repo, args.runtime, args.validation, args.review, args.node)
            result = {"status": "prepared_only", "plan": str(path), "target_unchanged": True}
        print(json.dumps(result))
        return 0
    except (PromotionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
