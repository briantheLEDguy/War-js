"""Create a private static adaptation from inspected town component templates.

No purchased Blueprint is executed. Interactive/construction-script behavior
requires a separate adapter; this output is not a runtime acceptance receipt.
"""
import hashlib
import json
import uuid
from pathlib import Path
import unreal

if "-nullrhi" in unreal.SystemLibrary.get_command_line().lower():
    raise RuntimeError("Mesh merging needs material render data; use -RenderOffscreen, not -NullRHI")

ROOT = Path(__file__).resolve().parents[2]
project = Path(unreal.Paths.project_dir()).resolve()
if project.name != "CityKitStaging":
    raise RuntimeError("Run adaptation in the private staging project")
directory = ROOT / "artifacts/unreal/licensed-kits"
receipt_path = directory / "town-kit-adaptation.json"
receipt_path.unlink(missing_ok=True)
inventory_path = directory / "town-kit-inventory.json"
inventory = json.loads(inventory_path.read_text())
source = project / "Content/Medieval_Mod_Town/Blueprints/Buildings/BP_Building.uasset"
if hashlib.sha256(source.read_bytes()).hexdigest() != inventory["sourceSha256"]:
    raise RuntimeError("Building source changed; inspect again")
rows = inventory["components"]
roots = [row for row in rows if row["class"] == "SceneComponent"]
if len(roots) != 1 or roots[0]["location"] != [0, 0, 0] or roots[0]["rotation"] != [0, 0, 0] or roots[0]["scale"] != [1, 1, 1]:
    raise RuntimeError("Only an identity shared root is supported")
meshes = [row for row in rows if row["class"] == "StaticMeshComponent"]
if len(meshes) + 1 != len(rows) or not meshes:
    raise RuntimeError("Unsupported component behavior requires an explicit adapter")
if any(row.get("parent") != roots[0]["name"] or not row.get("mesh") or
       row.get("collisionProfile") != "BlockAll" or not all(row["materials"]) for row in meshes):
    raise RuntimeError("Unsupported hierarchy, missing geometry/material, or collision profile")
target = "/Game/WarKitAdaptations/Town_Building_" + uuid.uuid4().hex

# Fingerprint the full pack before loading components so an ongoing installation
# cannot silently change a source package during this adaptation.
pack = project / "Content/Medieval_Mod_Town"
def fingerprint():
    return {str(path.relative_to(pack)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(pack.rglob("*")) if path.is_file()}
before = fingerprint()
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.new_level("/Game/WarKitAdaptations/Inspection_" + uuid.uuid4().hex):
    raise RuntimeError("Could not create private inspection world")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
instances = []
for row in meshes:
    mesh = unreal.load_asset(row["mesh"])
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("Mesh could not load: " + row["mesh"])
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*row["location"]),
                                         unreal.Rotator(*row["rotation"]))
    actor.set_actor_scale3d(unreal.Vector(*row["scale"]))
    component = actor.static_mesh_component
    component.set_static_mesh(mesh)
    for index, path in enumerate(row["materials"]):
        material = unreal.load_asset(path)
        if not isinstance(material, unreal.MaterialInterface):
            raise RuntimeError("Material could not load: " + path)
        component.set_material(index, material)
    instances.append(actor)
settings = unreal.MeshMergingSettings()
settings.set_editor_property("lod_selection_type", unreal.MeshLODSelectionType.ALL_LODS)
settings.set_editor_property("merge_materials", False)
settings.set_editor_property("merge_equivalent_materials", False)
settings.set_editor_property("bake_vertex_data_to_mesh", True)
settings.set_editor_property("generate_light_map_uv", False)
settings.set_editor_property("pivot_type", unreal.MeshMergePivotType.WORLD_ORIGIN)
options = unreal.MergeStaticMeshActorsOptions()
options.set_editor_property("base_package_name", target)
options.set_editor_property("mesh_merging_settings", settings)
options.set_editor_property("new_actor_label", "Town static adaptation")
mesh_tools = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
if not mesh_tools:
    mesh_tools = unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
merged = mesh_tools.merge_static_mesh_actors(instances, options)
mesh = merged.static_mesh_component.static_mesh if merged else None
if not merged or not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Native mesh merge failed")
mesh.get_editor_property("body_setup").set_editor_property(
    "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
    raise RuntimeError("Could not save adapted mesh")
if fingerprint() != before:
    raise RuntimeError("Pack changed during adaptation; output is not approved")
triangles = [mesh.get_num_triangles(index) for index in range(mesh.get_num_lods())]
if not triangles or any(count <= 0 for count in triangles):
    raise RuntimeError("Adaptation has empty geometry")
expected_materials = {path for row in meshes for path in row["materials"]}
actual_materials = {slot.material_interface.get_path_name() for slot in mesh.static_materials
                    if slot.material_interface}
if actual_materials != expected_materials:
    raise RuntimeError("Merged material coverage differs from inspected source; reject adaptation")
receipt = {"schemaVersion": 1, "asset": mesh.get_path_name(), "componentCount": len(meshes),
           "sourceSha256": inventory["sourceSha256"], "sourceFiles": before,
           "trianglesPerLod": triangles, "materialSlots": len(mesh.static_materials),
           "materials": sorted(actual_materials),
           "blueprintExecuted": False, "constructionScriptPreserved": False,
           "runtimeApproved": False, "visualApproved": False, "licenseReviewed": False}
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
unreal.log("WAR_TOWN_KIT_ADAPTED=" + target)
