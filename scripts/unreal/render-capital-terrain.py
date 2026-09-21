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
building_receipt = directory / "buildings-import.json"
building_hash = None
if building_receipt.is_file():
    buildings = json.loads(building_receipt.read_text())
    if buildings["sourceSha256"] != receipt["sourceSha256"] or digest(directory / "props.json") != buildings["propsInputSha256"]:
        raise RuntimeError("Stale building placements")
    for profile, expected in buildings["modelImports"].items():
        if profile not in tuple("aegis_house_" + str(index) for index in range(1, 7)) + ("aegis_rowhouse_1", "aegis_rowhouse_2", "aegis_wall"):
            raise RuntimeError("Unknown building profile")
        if digest(ROOT / "artifacts/unreal/converted" / profile / "editor-import.json") != expected:
            raise RuntimeError("Building import changed")
    building_hash = digest(building_receipt)
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt["map"]):
    raise RuntimeError("Capital workbench missing")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
review_fill = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 20000), unreal.Rotator(pitch=-35, yaw=145))
review_fill.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
review_fill.light_component.set_editor_property("intensity", 12500.0)
review_fill.light_component.set_visibility(False)
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
house_actors = [actor for actor in actors.get_all_level_actors()
                if isinstance(actor, unreal.StaticMeshActor) and "WarCapitalBuilding" in [str(tag) for tag in actor.tags]]
isolated_ids = {}
view_specs = [("overview", (-30000, -26000, 28000), (5000, 0, 0)),
                         ("raised-ground", (3000, -4500, 2400), (9000, 0, 1300)),
                         ("house", (-13992, -14420, 950), (-12492, -12920, 600)),
                         ("house-front", (-10992, -11420, 950), (-12492, -12920, 600))]
if building_hash:
    placements = json.loads((directory / "props.json").read_text())["housePlacements"]
    arrival = json.loads((ROOT / "public/assets/maps/aegis_capital.json").read_text())["spawnPoint"]
    for profile in sorted(buildings["modelImports"]):
        placement = next(row for row in placements if row["profileKey"] == profile)
        if profile.startswith("aegis_rowhouse_"):
            # Elevated first instances can be occluded by adjacent authored
            # terrain. Inspect an arrival-side instance without altering it.
            placement = min((row for row in placements if row["profileKey"] == profile),
                key=lambda row: (row["position"]["X"] - arrival["z"] * 100) ** 2
                    + (row["position"]["Y"] - arrival["x"] * 100) ** 2)
        isolated_ids[profile] = placement["id"]
        p = placement["position"]
        bounds = json.loads((ROOT / "artifacts/unreal/converted" / profile / "conversion.json").read_text())["before"]["boundsMeters"]
        height = (bounds["max"][2] - bounds["min"][2]) * 100
        distance = max(bounds["max"][i] - bounds["min"][i] for i in range(3)) * 130
        view_specs.append((profile, (p["X"] + distance, p["Y"] + distance, p["Z"] + height * 0.8),
                           (p["X"], p["Y"], p["Z"] + height * 0.45)))
        if profile.startswith("aegis_rowhouse_"):
            isolated_ids[profile + "-reverse"] = placement["id"]
            view_specs.append((profile + "-reverse", (p["X"] - distance, p["Y"] - distance, p["Z"] + height * 0.8),
                               (p["X"], p["Y"], p["Z"] + height * 0.45)))
        if profile == "aegis_wall":
            isolated_ids[profile + "-walkway"] = placement["id"]
            view_specs.append((profile + "-walkway", (p["X"] - distance * 0.35, p["Y"] - distance * 0.35, p["Z"] + height * 1.8),
                               (p["X"], p["Y"], p["Z"] + height * 0.8)))
for name, eye, focus in view_specs:
    selected_id = isolated_ids.get(name)
    # An inspection-only fill exposes the unlit side of isolated models. It is
    # disabled in world views and never saved into the playable map.
    review_fill.light_component.set_visibility(selected_id is not None)
    for actor in house_actors:
        actor.static_mesh_component.set_visibility(selected_id is None or selected_id in [str(tag) for tag in actor.tags])
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
    views.append({"view": name, "path": path.relative_to(ROOT).as_posix(), "sha256": digest(path),
                  "isolatedObjectId": selected_id, "inspectionFillLight": selected_id is not None})
receipt_path.write_text(json.dumps({"schemaVersion": 1, "sourceSha256": receipt["sourceSha256"],
    "terrainInputSha256": receipt["terrainInputSha256"], "views": views,
    "buildingImportSha256": building_hash,
    "capitalReady": False, "fullTraversalAccepted": False}, indent=2) + "\n")
unreal.log("WAR_CAPITAL_TERRAIN_RENDERED=" + str(receipt_path))
