"""Read installed house-kit mesh/dependency metadata without loading its Blueprints.

Run in the private CityKitStaging project. This produces candidates, not runtime
or license approval, and never modifies downloaded assets.
"""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
KIT = "/Game/Medieval_Mod_Town/Meshes"
project = Path(unreal.Paths.project_dir()).resolve()
output = ROOT / "artifacts/unreal/licensed-kits/capital-props-inventory.json"
if project.name != "CityKitStaging":
    raise RuntimeError("Run this inspection in the isolated kit staging project")
output.unlink(missing_ok=True)
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
mesh_tools = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
rows = []
for data in registry.get_assets_by_path(KIT, recursive=True):
    if str(data.asset_class_path.asset_name) != "StaticMesh":
        continue
    if str(data.asset_name) not in {"SM_Market_Stall", "SM_Market_Stall_Cloth", "SM_Bench", "SM_Barrel", "SM_Crate"}:
        continue
    mesh = data.get_asset()
    bounds = mesh.get_bounds()
    body = mesh.get_editor_property("body_setup")
    package = str(data.package_name)
    source = project / "Content" / (package.removeprefix("/Game/") + ".uasset")
    rows.append({"path": mesh.get_path_name(), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "boundsOrigin": [bounds.origin.x, bounds.origin.y, bounds.origin.z],
        "boundsExtent": [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
        "lodCount": mesh.get_num_lods(), "simpleCollisionCount": mesh_tools.get_simple_collision_count(mesh),
        "collisionTraceFlag": str(body.get_editor_property("collision_trace_flag")) if body else None,
        "materials": [str(slot.material_interface.get_path_name()) if slot.material_interface else None
                      for slot in mesh.get_editor_property("static_materials")]})
output.write_text(json.dumps({"schemaVersion": 1, "kit": KIT, "meshes": sorted(rows, key=lambda row: row["path"]),
    "runtimeApproved": False, "licenseReviewed": False}, indent=2) + "\n")
unreal.log("WAR_CITY_KIT_INSPECTED=" + str(output))
