"""Render the saved kit pilot offscreen; no mouse, keyboard or window control."""
import json
import os
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT / "artifacts/unreal/licensed-kits"
receipt = json.loads((directory / "capital-appearance-preview.json").read_text())
preview_map = os.environ.get("WAR_APPEARANCE_PREVIEW_MAP", receipt["map"])
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(preview_map):
    raise RuntimeError("Kit pilot is missing")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
component = capture.capture_component2d
target = unreal.RenderingLibrary.create_render_target2d(world, 1600, 1000, unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.texture_target = target
component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
component.capture_every_frame = False
component.capture_on_movement = False
component.always_persist_rendering_state = True
component.fov_angle = 65
# Review the saved daylight and exposure, without capture-only compensating light.
component.post_process_blend_weight = 0
views = []
for view, eye_values, center_values in [
    ("city", (-37000, -31000, 23500), (12000, 0, 5200)),
    ("castle", (11000, -8000, 10600), (17800, 0, 5100)),
    ("avenue", (-11000, 0, 230), (20000, 0, 6800)),
    ("market", (-13300, -3700, 620), (-9200, 1500, 200)),
    ("courtyard", (14800, -2400, 4450), (18500, 0, 5000)),
    ("herb-patch", (-13500, -10500, 260), (-13200, -10200, 30)),
    ("supplies", (-13700, -12400, 260), (-13200, -12200, 30)),
    ("soil-patch", (-13500, -9500, 240), (-13200, -9200, 20))]:
    eye, center = unreal.Vector(*eye_values), unreal.Vector(*center_values)
    rotation = unreal.MathLibrary.find_look_at_rotation(eye, center)
    capture.set_actor_location_and_rotation(eye, rotation, False, True)
    unreal.WarImportLibrary.prepare_world_preview_frame(world)
    for _ in range(5):
        component.capture_scene()
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
    name = "crownward-appearance-" + view + ".png"
    (directory / name).unlink(missing_ok=True)
    unreal.RenderingLibrary.export_render_target(world, target, str(directory), name)
    if not (directory / name).is_file():
        raise RuntimeError("Kit image was not written")
    actual = capture.get_actor_location()
    views.append({"image": name, "center": [center.x, center.y, center.z],
                  "eye": [eye.x, eye.y, eye.z],
                  "actualEye": [actual.x, actual.y, actual.z]})
(directory / "crownward-appearance-render-views.json").write_text(json.dumps({"map":preview_map,"savedSceneLighting":True,"captureExposureOverride":False,"views":views}, indent=2) + "\n")
unreal.log("WAR_CROWNWARD_RENDERED")
