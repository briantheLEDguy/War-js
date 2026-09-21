"""Inspect a purchased town assembly's templates without spawning its Blueprint."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
project = Path(unreal.Paths.project_dir()).resolve()
if project.name != "CityKitStaging":
    raise RuntimeError("Run town inspection in the private staging project")
output = ROOT / "artifacts/unreal/licensed-kits/town-kit-inventory.json"
output.unlink(missing_ok=True)
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
assets = registry.get_assets_by_path("/Game/Medieval_Mod_Town", recursive=True)
classes = Counter(str(data.asset_class_path.asset_name) for data in assets)
blueprint_path = "/Game/Medieval_Mod_Town/Blueprints/Buildings/BP_Building"
source = project / "Content/Medieval_Mod_Town/Blueprints/Buildings/BP_Building.uasset"
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
blueprint = unreal.load_asset(blueprint_path)
if not isinstance(blueprint, unreal.Blueprint):
    raise RuntimeError("Town building template missing")
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
components = []
seen = set()
for handle in subsystem.k2_gather_subobject_data_for_blueprint(blueprint):
    data = library.get_data(handle)
    obj = library.get_object_for_blueprint(data, blueprint)
    if not isinstance(obj, unreal.ActorComponent):
        continue
    if obj.get_path_name() in seen:
        continue
    seen.add(obj.get_path_name())
    row = {"name": obj.get_name(), "objectPath": obj.get_path_name(), "class": obj.get_class().get_name()}
    parent_handle = library.get_parent_handle(data)
    if library.is_handle_valid(parent_handle):
        parent = library.get_object_for_blueprint(library.get_data(parent_handle), blueprint)
        row["parent"] = parent.get_name() if parent else None
    if isinstance(obj, unreal.SceneComponent):
        location, rotation, scale = (obj.get_editor_property(name) for name in
                                     ["relative_location", "relative_rotation", "relative_scale3d"])
        row.update({"location": [location.x, location.y, location.z],
                    "rotation": [rotation.pitch, rotation.yaw, rotation.roll], "scale": [scale.x, scale.y, scale.z]})
    if isinstance(obj, unreal.StaticMeshComponent):
        row["mesh"] = obj.static_mesh.get_path_name() if obj.static_mesh else None
        row["materials"] = [obj.get_material(index).get_path_name() if obj.get_material(index) else None
                            for index in range(obj.get_num_materials())]
        row["collisionProfile"] = str(obj.get_collision_profile_name())
    components.append(row)
if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
    raise RuntimeError("The assembly changed during inspection; wait for its installation to finish")
output.write_text(json.dumps({"schemaVersion": 1, "assetClasses": dict(classes), "assembly": blueprint_path,
    "sourceSha256": source_hash, "components": components,
    "blueprintSpawned": False, "constructionScriptPreserved": False, "runtimeApproved": False,
    "licenseReviewed": False}, indent=2) + "\n")
unreal.log("WAR_TOWN_KIT_INSPECTED=" + str(output))
