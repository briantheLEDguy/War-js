"""Check saved native building transforms and collision, without claiming city parity."""
import hashlib
import json
import math
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT / "artifacts/unreal/capitals/aegis_capital"
output = directory / "buildings-proof.json"
output.unlink(missing_ok=True)
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
receipt = json.loads((directory / "buildings-import.json").read_text())
document = json.loads((directory / "props.json").read_text())
if digest(ROOT / "public/assets/maps/aegis_capital.json") != receipt["sourceSha256"] or digest(directory / "props.json") != receipt["propsInputSha256"]:
    raise RuntimeError("Stale capital buildings")
for profile, expected in receipt["modelImports"].items():
    if profile not in tuple("aegis_house_" + str(index) for index in range(1, 7)):
        raise RuntimeError("Unknown house profile")
    if digest(ROOT / "artifacts/unreal/converted" / profile / "editor-import.json") != expected:
        raise RuntimeError("House import changed after placement")
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt["map"]):
    raise RuntimeError("Missing capital map")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = {actor.get_actor_label(): actor for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
unreal.WarImportLibrary.prepare_preview_frame(None)
results = []
for placement in document["housePlacements"]:
    actor = actors.get("Capital prop " + placement["id"])
    if not isinstance(actor, unreal.StaticMeshActor) or actor.static_mesh_component.static_mesh is None:
        raise RuntimeError("Missing complex building: " + placement["id"])
    position = placement["position"]
    actual = actor.get_actor_location()
    if max(abs(actual.x - position["X"]), abs(actual.y - position["Y"]), abs(actual.z - position["Z"])) > 0.02:
        raise RuntimeError("Building position changed")
    scale = actor.get_actor_scale3d()
    if max(abs(value - expected) for value, expected in zip((scale.x, scale.y, scale.z), placement["scale"])) > 0.0001:
        raise RuntimeError("Building basis scale changed")
    yaw = actor.get_actor_rotation().yaw
    if abs((yaw - placement["yawDegrees"] + 180) % 360 - 180) > 0.001:
        raise RuntimeError("Building orientation changed")
    for collider in placement["colliders"]:
        center = collider["center"]
        half = collider["halfSize"]
        angle = math.radians(collider["yawDegrees"])
        axes = ((math.cos(angle), math.sin(angle), 0), (-math.sin(angle), math.cos(angle), 0), (0, 0, 1))
        # Trace each pair of side walls plus the top, requiring this exact actor.
        for axis, signs in ((0, (-1, 1)), (1, (-1, 1)), (2, (1,))):
            for sign in signs:
                direction = tuple(value * sign for value in axes[axis])
                point = (center["X"], center["Y"], center["Z"])
                start = unreal.Vector(*(point[i] + direction[i] * (half[axis] + 25) for i in range(3)))
                end = unreal.Vector(*point)
                hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.ECC_VISIBILITY,
                    True, [], unreal.DrawDebugTrace.NONE, True)
                if not isinstance(hit, unreal.HitResult):
                    raise RuntimeError(f"Missing building collision: {placement['id']}/{axis}/{sign}")
                parts = hit.to_tuple()
                if not parts[0] or parts[9] != actor:
                    raise RuntimeError("Wrong actor blocked building trace")
                impact = parts[5]
                measured = (impact.x, impact.y, impact.z)
                error = max(abs(measured[i] - point[i] - direction[i] * half[axis]) for i in range(3))
                if error > 0.2:
                    raise RuntimeError(f"Building collision extent mismatch: {error} cm")
                results.append({"id": placement["id"], "collider": collider["index"], "axis": axis, "sign": sign, "errorCm": error})
output.write_text(json.dumps({"schemaVersion": 1, "sourceSha256": receipt["sourceSha256"], "passed": True,
    "buildingCount": len(document["housePlacements"]), "traces": results, "capitalReady": False,
    "fullTraversalAccepted": False, "geometryApproved": False}, indent=2) + "\n")
unreal.log("WAR_CAPITAL_BUILDINGS_VERIFIED=" + str(output))
