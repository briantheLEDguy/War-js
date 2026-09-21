"""Build Crownward from purchased modules without modifying the reference city."""
import hashlib
import json
import math
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capital_kit_layout import build_layout
from capital_game_world import build_terrain, build_gameplay
from capital_materials import cloth_material

directory = ROOT / "artifacts/unreal/licensed-kits"
layout = build_layout()
target = layout["map"]
receipt_path = directory / "capital-kit-build.json"
if (ROOT / "unreal/AegisWar/Saved/WorldEdit/crownward-draft.json").exists():
    raise RuntimeError("Preserve the owner's Crownward draft; reconcile its baseline before regeneration")
if Path(unreal.Paths.project_dir()).resolve() != (ROOT / "unreal/AegisWar").resolve():
    raise RuntimeError("Build the playable city in AegisWar; CityKitStaging is only an import workspace")
package_file = ROOT / "unreal/AegisWar/Content" / (target.removeprefix("/Game/") + ".umap")
if unreal.EditorAssetLibrary.does_asset_exist(target):
    previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
    if not previous or hashlib.sha256(package_file.read_bytes()).hexdigest() != previous.get("mapSha256"):
        raise RuntimeError("Preserve the edited city; reconcile before regeneration")
else:
    if not unreal.EditorAssetLibrary.duplicate_asset("/Game/Capitals/aegis_capital/AegisCapital_Workbench", target):
        raise RuntimeError("Could not create the new capital workbench")
staged = json.loads((directory / "capital-kit-staged.json").read_text())
props = json.loads((directory / "capital-props-staged.json").read_text())
staged = {"meshes": staged["meshes"] + props["meshes"], "files": staged["files"] + props["files"]}
for row in staged["files"]:
    path = ROOT / "unreal/AegisWar/Content" / row["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
        raise RuntimeError("Kit dependency changed: " + row["path"])
fingerprint = hashlib.sha256(json.dumps(staged["files"], sort_keys=True).encode()).hexdigest()
metadata = {row["path"]: row for row in json.loads((directory / "house-kit-inventory.json").read_text())["meshes"]}
metadata.update({row["path"]: row for row in json.loads((directory / "capital-props-inventory.json").read_text())["meshes"]})
names = {"floor": "Stone_Floor_01", "wall": "Stone_Wall_01", "merlon": "Stone_Wall_Half_V_01",
         "window": "Stone_Wall_Window_01", "door": "Stone_Wall_Door_01",
         "buttress": "Stone_Wall_Buttress_01", "stairs": "Stone_Stairs_02"}
names.update({"house" + str(i + 1): "House_" + name for i, name in enumerate(["01", "02", "03", "04a", "04b", "04c"])})
names = {kind: "SM_MH_02_" + suffix for kind, suffix in names.items()}
names.update({"stall": "SM_Market_Stall_Cloth", "stallframe": "SM_Market_Stall",
              "bench": "SM_Bench", "barrel": "SM_Barrel", "crate": "SM_Crate"})
meshes, bounds = {}, {}
for kind, suffix in names.items():
    if not any(row["kind"] == kind for row in layout["placements"]):
        continue
    source = next(path for path in staged["meshes"] if path.endswith("." + suffix))
    destination = "/Game/LicensedKits/Crownward/" + suffix
    if not unreal.EditorAssetLibrary.does_asset_exist(destination):
        unreal.EditorAssetLibrary.duplicate_asset(source, destination)
    mesh = unreal.load_asset(destination)
    if not isinstance(mesh, unreal.StaticMesh) or not all(metadata[source]["materials"]):
        raise RuntimeError("Missing authored mesh or materials: " + kind)
    mesh.get_editor_property("body_setup").set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if kind == "stall":
        mesh.set_material(0, cloth_material(ROOT, unreal))
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError("Could not save collision adaptation")
    meshes[kind], bounds[kind] = mesh, metadata[source]
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not level.load_level(target):
    raise RuntimeError("Could not open new city workbench")
for actor in actors.get_all_level_actors():
    if ("WarCapitalBuilding" in [str(tag) for tag in actor.tags]
            or actor.get_actor_label().startswith("Authored Aegis ")
            or actor.get_actor_label() == "Crownward level terrain"
            or any(str(tag) in ["WarCrownwardTerrain", "WarCapitalGameplay"] for tag in actor.tags)):
        actors.destroy_actor(actor)
geography = build_terrain(actors)
gameplay = build_gameplay(actors, meshes["crate"])
placed = []
for row in layout["placements"]:
    kind, (sx, sy, sz) = row["kind"], row["scale"]
    b = bounds[kind]
    ox, oy, oz = b["boundsOrigin"]
    angle = math.radians(row["yaw"])
    x, y, bottom = row["centerBottom"]
    location = unreal.Vector(x - (ox * sx * math.cos(angle) - oy * sy * math.sin(angle)),
                             y - (ox * sx * math.sin(angle) + oy * sy * math.cos(angle)),
                             bottom - (oz - b["boundsExtent"][2]) * sz)
    if kind in ["stall", "stallframe"]:
        # The cloth and timber frame share an authored pivot, not bounds.
        location = unreal.Vector(x, y, bottom)
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, location, unreal.Rotator(yaw=row["yaw"]))
    actor.set_actor_scale3d(unreal.Vector(sx, sy, sz))
    actor.set_actor_label(row["id"].replace("_", " ").title())
    actor.tags = ["WarCapitalBuilding", "WarCrownward", "WarWorldObject_" + row["id"],
                  "WarModelSha256_" + fingerprint]
    actor.static_mesh_component.set_static_mesh(meshes[kind])
    actor.static_mesh_component.set_collision_profile_name("BlockAll")
    placed.append({**row, "mesh": meshes[kind].get_path_name()})
for actor in actors.get_all_level_actors():
    if isinstance(actor, unreal.PlayerStart):
        actor.set_actor_location_and_rotation(unreal.Vector(*layout["arrival"]), unreal.Rotator(yaw=0), False, True)
if not level.save_current_level():
    raise RuntimeError("Could not save Crownward")
receipt_path.write_text(json.dumps({**layout, "geography": geography, "gameplay": gameplay, "placements": placed, "dependencyFingerprint": fingerprint,
    "mapSha256": hashlib.sha256(package_file.read_bytes()).hexdigest(), "gmRuntimeVerified": False,
    "traversalVerified": False, "visualApproved": False}, indent=2) + "\n")
(ROOT / "unreal/AegisWar/Content/Migration/capital-development.json").write_text(json.dumps({"map": target,
    "routes": layout["routes"], "castleRoutes": layout["castleRoutes"], "gameplay": gameplay}) + "\n")
unreal.log("WAR_CROWNWARD_BUILT=" + str(len(placed)))
