"""Render actual capital terrain through Unreal without modifying the saved map."""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT / "artifacts/unreal/capitals/aegis_capital"
receipt_path = directory / "terrain-render.json"
receipt_path.unlink(missing_ok=True)
receipt = json.loads((directory / "terrain-import.json").read_text())
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
if digest(ROOT / "public/assets/maps/aegis_capital.json") != receipt["sourceSha256"]:
    raise RuntimeError("Stale capital source")
if digest(directory / "terrain.json") != receipt["terrainInputSha256"]:
    raise RuntimeError("Stale capital terrain")
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt["map"]):
    raise RuntimeError("Capital workbench missing")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
component = capture.capture_component2d
target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 960, unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.set_editor_property("texture_target", target)
component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
component.set_editor_property("capture_every_frame", False)
component.set_editor_property("capture_on_movement", False)
component.set_editor_property("always_persist_rendering_state", True)
component.set_editor_property("fov_angle", 65.0)
component.set_editor_property("post_process_blend_weight", 1.0)
settings = component.get_editor_property("post_process_settings")
settings.set_editor_property("override_auto_exposure_method", True)
settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 0.0)
settings.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
settings.set_editor_property("auto_exposure_apply_physical_camera_exposure", True)
component.set_editor_property("post_process_settings", settings)
views = []
for name, eye, focus in (("overview", (-30000, -26000, 28000), (5000, 0, 0)),
                         ("raised-ground", (3000, -4500, 2400), (9000, 0, 1300))):
    position = unreal.Vector(*eye)
    capture.set_actor_location_and_rotation(position, unreal.MathLibrary.find_look_at_rotation(position, unreal.Vector(*focus)), False, True)
    unreal.WarImportLibrary.prepare_preview_frame(None)
    for _ in range(4):
        component.capture_scene()
        unreal.WarImportLibrary.prepare_preview_frame(None)
    filename = "terrain-" + name + ".png"
    path = directory / filename
    path.unlink(missing_ok=True)
    unreal.RenderingLibrary.export_render_target(world, target, str(directory), filename)
    if not path.is_file():
        raise RuntimeError("Missing capital rendered image")
    views.append({"view": name, "path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)})
receipt_path.write_text(json.dumps({"schemaVersion": 1, "sourceSha256": receipt["sourceSha256"],
    "terrainInputSha256": receipt["terrainInputSha256"], "views": views,
    "capitalReady": False, "fullTraversalAccepted": False}, indent=2) + "\n")
unreal.log("WAR_CAPITAL_TERRAIN_RENDERED=" + str(receipt_path))
