"""Record diagnostic entrance capsule sweeps without claiming traversal acceptance."""
import json
import hashlib
import uuid
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT / "artifacts/unreal/licensed-kits"
receipt = json.loads((directory / "town-kit-staged.json").read_text())
for row in receipt["files"]:
    path = ROOT / "unreal/AegisWar/Content" / row["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
        raise RuntimeError("Staged dependency changed: " + row["path"])
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.new_level("/Game/WarKitAdaptations/Preview_" + uuid.uuid4().hex):
    raise RuntimeError("Could not create isolated preview")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh = unreal.load_asset(receipt["meshes"][0])
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Town adaptation missing")
actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
actor.static_mesh_component.set_static_mesh(mesh)
actor.static_mesh_component.set_collision_profile_name("BlockAll")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.WarImportLibrary.prepare_world_preview_frame(world)
probes = []
for height in [120, 130, 140, 150, 160]:
    start, end = unreal.Vector(600, 200, height), unreal.Vector(600, -200, height)
    hit = unreal.SystemLibrary.capsule_trace_single(world, start, end, 42, 96,
        unreal.TraceTypeQuery.ECC_VISIBILITY, False, [], unreal.DrawDebugTrace.NONE, True)
    row = {"height": height, "radius": 42, "halfHeight": 96, "blocked": hit is not None}
    if hit:
        values = hit.to_tuple()
        point, normal = values[5], values[7]
        row.update({"initialOverlap": values[1], "distance": values[3],
                    "impactPoint": [point.x, point.y, point.z],
                    "impactNormal": [normal.x, normal.y, normal.z]})
    probes.append(row)
(directory / "town-collision-probes.json").write_text(json.dumps({"asset": receipt["meshes"][0],
    "probes": probes, "traversalApproved": False,
    "scope": "Front entrance candidate at local x=600; diagnostic sweeps only, not walking acceptance"}, indent=2) + "\n")
unreal.log("WAR_TOWN_COLLISION_PROBED")
