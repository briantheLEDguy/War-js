"""Render imported characters through Unreal's real renderer; requires -AllowCommandletRendering."""
import json
import argparse
import importlib.util
import math
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/unreal/visual-proof"
parser = argparse.ArgumentParser()
parser.add_argument("--rest", action="store_true")
parser.add_argument("--profile", action="append")
parser.add_argument("--clip", default="idle")
parser.add_argument("--time", type=float, default=0.4)
options = parser.parse_args()
if not math.isfinite(options.time) or options.time < 0:
    raise ValueError("Preview time must be finite and nonnegative")
spec = importlib.util.spec_from_file_location("war_imports", Path(__file__).with_name("import-models.py"))
imports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imports)
profiles = tuple(dict.fromkeys(options.profile or ("npc_frontier_sunmeadow_empire_herbalist", "mire_warbrute_m")))
receipts = []
for profile in profiles:
    context = imports.validate_inputs(profile)
    receipt = imports.load_json(context["directory"] / "editor-import.json")
    imports.require(receipt["importSucceeded"] and receipt["conversionSha256"] == context["conversionSha256"]
                    and receipt["sourceSha256"] == context["conversion"]["sourceSha256"], "Stale preview import evidence")
    imports.require(receipt["kind"] == "characterProfiles", "Character preview requires skeletal geometry")
    if not options.rest:
        clip = next((clip for clip in receipt["animations"] if clip["sourceClipName"] == options.clip), None)
        imports.require(clip is not None and options.time <= clip["durationSeconds"], "Unknown clip or preview time beyond duration")
    receipts.append(receipt)
if options.profile:
    OUTPUT = OUTPUT / "__".join(profiles)
OUTPUT.mkdir(parents=True, exist_ok=True)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level("/Game/MigrationProof/EngineProof"):
    raise RuntimeError("Prepare the proof map before rendering")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
# Isolate the inspected character from proof NPCs/props without changing the
# saved proof map. Otherwise their overlapping silhouettes can hide defects.
for existing in actors.get_all_level_actors():
    if existing.get_actor_label() != "Development terrain (allowed terrain construction)":
        for primitive in existing.get_components_by_class(unreal.PrimitiveComponent):
            primitive.set_visibility(False, True)
characters = []
rendered_models = []
for index, (profile, receipt) in enumerate(zip(profiles, receipts, strict=True)):
    actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, (index - (len(profiles) - 1) / 2) * 180, 0), unreal.Rotator(yaw=-90))
    component = actor.skeletal_mesh_component
    component.set_skeletal_mesh(unreal.load_asset(receipt["meshes"][0]["path"]))
    if not options.rest:
        clip = next(clip for clip in receipt["animations"] if clip["sourceClipName"] == options.clip)
        component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        component.play_animation(unreal.load_asset(clip["path"]), True)
        component.set_position(options.time, False)
    unreal.WarImportLibrary.prepare_preview_frame(component)
    measured = unreal.WarImportLibrary.get_skinned_bounds(component)
    unreal.log(f"WAR_SKIN_BOUNDS {profile} {measured}")
    rendered_models.append({"profileKey": profile, "sourceSha256": receipt["sourceSha256"],
        "importReceiptSha256": imports.sha256(ROOT / "artifacts/unreal/converted" / profile / "editor-import.json"),
        "skeletalMeshPath": receipt["meshes"][0]["path"], "skinnedBoundsCm": {
            "min": [measured.min.x, measured.min.y, measured.min.z],
            "max": [measured.max.x, measured.max.y, measured.max.z]}})
    characters.append(component)

for location in ((400, -250, 350), (400, 250, 250), (-300, 0, 350)):
    light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*location))
    light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.light_component.set_editor_property("intensity", 200.0)
    light.light_component.set_editor_property("attenuation_radius", 2000.0)

capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(500, 0, 160))
component = capture.capture_component2d
target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 960, unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.set_editor_property("texture_target", target)
component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
component.set_editor_property("capture_every_frame", False)
component.set_editor_property("capture_on_movement", False)
component.set_editor_property("fov_angle", 45.0)
component.set_editor_property("post_process_blend_weight", 1.0)
settings = component.get_editor_property("post_process_settings")
settings.set_editor_property("override_auto_exposure_method", True)
settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 0.0)
settings.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
settings.set_editor_property("auto_exposure_apply_physical_camera_exposure", True)
settings.set_editor_property("override_bloom_intensity", True)
settings.set_editor_property("bloom_intensity", 0.0)
component.set_editor_property("post_process_settings", settings)
rendered_views = []
suffix = "rest" if options.rest else f"{imports.safe_name(options.clip)}-{options.time:g}s"
receipt_path = OUTPUT / (suffix + ".json")
receipt_path.unlink(missing_ok=True)
for name, position in (("front", (550, 0, 150)), ("back", (-550, 0, 150)), ("side", (0, -550, 150))):
    eye = unreal.Vector(*position)
    rotation = unreal.MathLibrary.find_look_at_rotation(eye, unreal.Vector(0, 0, 100))
    capture.set_actor_location_and_rotation(eye, rotation, False, True)
    for character in characters:
        unreal.WarImportLibrary.prepare_preview_frame(character)
    component.capture_scene()
    unreal.WarImportLibrary.prepare_preview_frame(characters[0])
    filename = name + "-" + suffix + ".png"
    (OUTPUT / filename).unlink(missing_ok=True)
    unreal.RenderingLibrary.export_render_target(world, target, str(OUTPUT), filename)
    if not (OUTPUT / filename).is_file():
        raise RuntimeError("Unreal did not write a rendered preview")
    rendered_views.append({"view": name, "path": (OUTPUT / filename).relative_to(ROOT).as_posix(),
                           "sha256": imports.sha256(OUTPUT / filename)})
receipt_path.write_text(json.dumps({"schemaVersion": 1, "engineVersion": unreal.SystemLibrary.get_engine_version(),
    "models": rendered_models, "clip": None if options.rest else options.clip,
    "timeSeconds": None if options.rest else options.time, "views": rendered_views,
    "artApproved": False, "limitations": ["A rendered pose is not complete animation, LOD, equipment or gameplay acceptance."]},
    indent=2, allow_nan=False) + "\n", encoding="utf-8")
unreal.log("WAR_VISUAL_PROOF=" + str(OUTPUT))
