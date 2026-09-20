"""Render imported characters through Unreal's real renderer; requires -AllowCommandletRendering."""
import json
import argparse
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/unreal/visual-proof"
OUTPUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument("--rest", action="store_true")
options = parser.parse_args()
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level("/Game/MigrationProof/EngineProof"):
    raise RuntimeError("Prepare the proof map before rendering")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
profiles = ("npc_frontier_sunmeadow_empire_herbalist", "mire_warbrute_m")
characters = []
for index, profile in enumerate(profiles):
    receipt = json.loads((ROOT / "artifacts/unreal/converted" / profile / "editor-import.json").read_text())
    actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, (index - 0.5) * 180, 0), unreal.Rotator(yaw=-90))
    component = actor.skeletal_mesh_component
    component.set_skeletal_mesh(unreal.load_asset(receipt["meshes"][0]["path"]))
    idle = next(clip for clip in receipt["animations"] if clip["sourceClipName"] == "idle")
    if not options.rest:
        component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        component.play_animation(unreal.load_asset(idle["path"]), True)
        component.set_position(0.4, False)
    unreal.WarImportLibrary.prepare_preview_frame(component)
    measured = unreal.WarImportLibrary.get_skinned_bounds(component)
    unreal.log(f"WAR_SKIN_BOUNDS {profile} {measured}")
    characters.append(component)

for location in ((400, -250, 350), (400, 250, 250), (-300, 0, 350)):
    light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*location))
    light.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.light_component.set_editor_property("intensity", 1000.0)
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
for name, position in (("front", (550, 0, 150)), ("back", (-550, 0, 150)), ("side", (0, -550, 150))):
    eye = unreal.Vector(*position)
    rotation = unreal.MathLibrary.find_look_at_rotation(eye, unreal.Vector(0, 0, 100))
    capture.set_actor_location_and_rotation(eye, rotation, False, True)
    for character in characters:
        unreal.WarImportLibrary.prepare_preview_frame(character)
    component.capture_scene()
    unreal.WarImportLibrary.prepare_preview_frame(characters[0])
    filename = name + ("-rest" if options.rest else "-idle") + ".png"
    (OUTPUT / filename).unlink(missing_ok=True)
    unreal.RenderingLibrary.export_render_target(world, target, str(OUTPUT), filename)
    if not (OUTPUT / filename).is_file():
        raise RuntimeError("Unreal did not write a rendered preview")
unreal.log("WAR_VISUAL_PROOF=" + str(OUTPUT))
