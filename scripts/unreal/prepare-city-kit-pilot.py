"""Build a separate capital kit pilot; keep the original capital map intact."""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT / "artifacts/unreal/licensed-kits"
receipt_path = directory / "house-kit-pilot.json"
previous = json.loads(receipt_path.read_text()) if receipt_path.is_file() else None
baseline_hash = hashlib.sha256((ROOT / "artifacts/unreal/capitals/aegis_capital/buildings-import.json").read_bytes()).hexdigest()
if previous and previous["baselineImportSha256"] != baseline_hash:
    raise RuntimeError("Capital baseline changed; reconcile the pilot explicitly before regeneration")
staged = json.loads((directory / "house-kit-staged.json").read_text())
inventory = json.loads((directory / "house-kit-inventory.json").read_text())
metadata = {row["path"]: row for row in inventory["meshes"]}
for row in staged["files"]:
    path = ROOT / "unreal/AegisWar/Content" / row["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
        raise RuntimeError("Staged kit dependency changed: " + row["path"])
fingerprint = hashlib.sha256(json.dumps(staged["files"], sort_keys=True).encode()).hexdigest()
base = "/Game/Capitals/aegis_capital/AegisCapital_Workbench"
target = "/Game/Capitals/kit_pilot/AegisCapital_Workbench"
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not unreal.EditorAssetLibrary.does_asset_exist(target):
    if not unreal.EditorAssetLibrary.duplicate_asset(base, target):
        raise RuntimeError("Could not copy capital for the kit pilot")
if not level.load_level(target):
    raise RuntimeError("Kit pilot map missing")
specs = {
    "SM_MH_02_House_02": ("aegis_infill_house_5_16", -9871.8, -3794.9),
    "SM_MH_02_Stone_Floor_01": ("kit_pilot_floor", -11000, -2200),
    "SM_MH_02_Stone_Wall_01": ("kit_pilot_wall", -11000, -1600),
    "SM_MH_02_Stone_Wall_Door_01": ("kit_pilot_doorway", -11000, -1000),
    "SM_MH_02_Stone_Stairs_01": ("kit_pilot_stairs", -11000, -400),
}
placed = []
for path in staged["meshes"]:
    name = path.rsplit(".", 1)[1]
    identity, x, y = specs[name]
    row = metadata[path]
    if not all(row["materials"]):
        raise RuntimeError("Pilot mesh lacks materials: " + name)
    adapted_path = "/Game/LicensedKits/MH2/" + name
    if not unreal.EditorAssetLibrary.does_asset_exist(adapted_path):
        if not unreal.EditorAssetLibrary.duplicate_asset(path, adapted_path):
            raise RuntimeError("Could not create private mesh adaptation")
    mesh = unreal.load_asset(adapted_path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("Required kit mesh unavailable")
    if row["simpleCollisionCount"] == 0:
        # Preserve the visible door openings/stairs exactly; never approximate
        # an entire assembled building with a solid bounding-box collider.
        mesh.get_editor_property("body_setup").set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError("Could not save reviewed collision configuration")
    matches = [actor for actor in actors.get_all_level_actors()
               if "WarWorldObject_" + identity in [str(tag) for tag in actor.tags]]
    if len(matches) > 1:
        raise RuntimeError("Ambiguous pilot identity")
    for old in matches:
        if "WarCapitalBuilding" not in [str(tag) for tag in old.tags]:
            raise RuntimeError("Refusing to replace unrelated actor")
        if "WarKitPilot" in [str(tag) for tag in old.tags]:
            prior = next((entry for entry in (previous or {}).get("placed", []) if entry["id"] == identity), None)
            location = old.get_actor_location()
            if not prior or any(abs(a - b) > 0.01 for a, b in zip([location.x, location.y, location.z], prior["position"])):
                raise RuntimeError("Pilot object was moved outside the generator; preserve its edits")
            rotation, scale = old.get_actor_rotation(), old.get_actor_scale3d()
            if max(abs(rotation.pitch), abs(rotation.yaw), abs(rotation.roll)) > 0.01 or any(abs(v - 1) > 0.001 for v in [scale.x, scale.y, scale.z]):
                raise RuntimeError("Pilot object transform was edited; reconcile it explicitly")
        actors.destroy_actor(old)
    # All pilot entries sit on the existing ground level, with original UE units.
    bottom = row["boundsOrigin"][2] - row["boundsExtent"][2]
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, -bottom))
    actor.set_actor_label("Kit pilot " + name)
    actor.tags = ["WarCapitalBuilding", "WarKitPilot", "WarWorldObject_" + identity,
                  "WarModelSha256_" + fingerprint]
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name("BlockAll")
    placed.append({"id": identity, "mesh": mesh.get_path_name(), "sourceMesh": path,
                   "collisionAdapted": row["simpleCollisionCount"] == 0, "position": [x, y, -bottom]})
if not level.save_current_level():
    raise RuntimeError("Could not save kit pilot")
receipt = {"schemaVersion": 1, "map": target, "placed": placed, "additionalObjects": 4,
    "additionalModels": 5, "dependencyFingerprint": fingerprint,
    "baselineImportSha256": baseline_hash,
    "runtimeApproved": False, "visualApproved": False, "capitalReady": False}
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
unreal.log("WAR_CITY_KIT_PILOT_CREATED=" + target)
