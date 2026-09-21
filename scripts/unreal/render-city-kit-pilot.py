"""Render the saved kit pilot offscreen; no mouse, keyboard or window control."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT / "artifacts/unreal/licensed-kits"
receipt = json.loads((directory / "house-kit-pilot.json").read_text())
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt["map"]):
    raise RuntimeError("Kit pilot is missing")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
fill = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 20000), unreal.Rotator(pitch=-35, yaw=145))
fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
fill.light_component.set_editor_property("intensity", 12500.0)
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
component = capture.capture_component2d
target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 960, unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.texture_target = target
component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
component.capture_every_frame = False
component.capture_on_movement = False
component.always_persist_rendering_state = True
component.fov_angle = 65
component.post_process_blend_weight = 1
settings = component.post_process_settings
settings.override_auto_exposure_method = True
settings.auto_exposure_method = unreal.AutoExposureMethod.AEM_MANUAL
settings.override_auto_exposure_bias = True
settings.auto_exposure_bias = 0
settings.override_auto_exposure_apply_physical_camera_exposure = True
settings.auto_exposure_apply_physical_camera_exposure = True
component.post_process_settings = settings
views = []
for actor in actors.get_all_level_actors():
    if "WarKitPilot" not in [str(tag) for tag in actor.tags]:
        continue
    center, extent = actor.get_actor_bounds(False)
    distance = max(extent.x, extent.y, extent.z) * 2.5 + 200
    eye = center + unreal.Vector(distance, distance, distance * 0.65)
    rotation = unreal.MathLibrary.find_look_at_rotation(eye, center)
    capture.set_actor_location_and_rotation(eye, rotation, False, True)
    unreal.WarImportLibrary.prepare_world_preview_frame(world)
    for _ in range(5):
        component.capture_scene()
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
    name = actor.static_mesh_component.static_mesh.get_name() + ".png"
    (directory / name).unlink(missing_ok=True)
    unreal.RenderingLibrary.export_render_target(world, target, str(directory), name)
    if not (directory / name).is_file():
        raise RuntimeError("Kit image was not written")
    actual = capture.get_actor_location()
    views.append({"image": name, "center": [center.x, center.y, center.z],
                  "extent": [extent.x, extent.y, extent.z], "eye": [eye.x, eye.y, eye.z],
                  "actualEye": [actual.x, actual.y, actual.z]})
(directory / "pilot-render-views.json").write_text(json.dumps(views, indent=2) + "\n")
unreal.log("WAR_CITY_KIT_PILOT_RENDERED")
