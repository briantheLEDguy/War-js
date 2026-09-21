"""Place the first verified house profile; preserve and report all pending identities."""
import importlib.util
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("war_imports", Path(__file__).with_name("import-models.py"))
imports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imports)
require = imports.require
directory = ROOT / "artifacts/unreal/capitals/aegis_capital"
output = directory / "buildings-import.json"
output.unlink(missing_ok=True)
document = imports.load_json(directory / "props.json")
terrain = imports.load_json(directory / "terrain-import.json")
source = ROOT / "public/assets/maps/aegis_capital.json"
source_hash = imports.sha256(source)
require(document["schemaVersion"] == 1 and document["sourceSha256"] == terrain["sourceSha256"] == source_hash,
        "Stale capital placement inputs")
input_hash = imports.sha256(directory / "props.json")
context = imports.validate_inputs("aegis_house_1")
receipt_path = context["directory"] / "editor-import.json"
receipt = imports.load_json(receipt_path)
require(receipt["importSucceeded"] and receipt["conversionSha256"] == context["conversionSha256"]
        and receipt["sourceSha256"] == context["conversion"]["sourceSha256"] and len(receipt["meshes"]) == 1,
        "House native import evidence is stale")
mesh = unreal.load_asset(receipt["meshes"][0]["path"])
require(isinstance(mesh, unreal.StaticMesh), "Missing imported complex house")
imports.require_owned(unreal, mesh, context)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
require(level.load_level(terrain["map"]), "Capital terrain map is missing")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
existing = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
placed = []
for placement in document["housePlacements"]:
    original = placement["source"]
    require(placement["profileKey"] == "aegis_house_1" and original.get("model") == context["source"].name,
            "House identity/model mismatch")
    require(not original.get("interaction") and not original.get("walkableSurfaces"),
            "This placement requires an interaction or walkable-surface implementation")
    require(all(c["source"].get("blocksWhen", "always") == "always" and not c["source"].get("interactionId")
                for c in placement["colliders"]), "Conditional collision is not yet implemented")
    label = "Capital prop " + placement["id"]
    actor = existing.get(label)
    require(actor is None or (isinstance(actor, unreal.StaticMeshActor) and "WarCapitalBuilding" in [str(tag) for tag in actor.tags]),
            "Refusing to overwrite an unrelated capital actor")
    position = placement["position"]
    point = unreal.Vector(position["X"], position["Y"], position["Z"])
    rotation = unreal.Rotator(yaw=placement["yawDegrees"])
    if actor is None:
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, point, rotation)
    require(actor is not None, "Could not create capital building")
    actor.set_actor_label(label)
    actor.set_editor_property("tags", ["WarCapitalBuilding", placement["id"], "aegis_house_1"])
    actor.set_actor_location_and_rotation(point, rotation, False, True)
    actor.set_actor_scale3d(unreal.Vector(*placement["scale"]))
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name("NoCollision")
    expected_names = {"AuthoredCollision_" + str(c["index"]) for c in placement["colliders"]}
    # A changed schema cannot quietly leave old blocking volumes in the level.
    for component in actor.get_components_by_class(unreal.BoxComponent):
        require(component.get_name() in expected_names, "Unexpected existing building collision; reconcile explicitly")
    for collider in placement["colliders"]:
        center = collider["center"]
        box = unreal.WarImportLibrary.set_capital_building_collision(actor, collider["index"],
            unreal.Vector(center["X"], center["Y"], center["Z"]), unreal.Vector(*collider["halfSize"]), collider["yawDegrees"])
        require(box is not None, "Native authored collision construction failed")
    placed.append({"id": placement["id"], "actor": actor.get_path_name(), "profileKey": placement["profileKey"],
                   "colliders": len(placement["colliders"]), "nativeLodsComplete": False})
require(imports.sha256(source) == source_hash and imports.sha256(directory / "props.json") == input_hash,
        "Capital source changed during placement")
require(level.save_current_level(), "Could not save capital buildings")
placed_ids = {row["id"] for row in placed}
output.write_text(json.dumps({"schemaVersion": 1, "sourceSha256": source_hash, "propsInputSha256": input_hash,
    "modelImportSha256": imports.sha256(receipt_path), "map": terrain["map"], "placed": placed,
    "pendingPropIds": [row["id"] for row in document["objects"] if row["id"] not in placed_ids],
    "capitalReady": False, "gmBuilderReady": False, "geometryApproved": False}, indent=2) + "\n")
unreal.log("WAR_CAPITAL_BUILDINGS_CREATED=" + str(output))
