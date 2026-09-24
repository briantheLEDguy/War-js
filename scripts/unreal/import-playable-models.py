"""Import body/rig and equipment independently of animation, preserving GLB PBR.

Uses the existing material importer; admission and visual acceptance are separate.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"artifacts/unreal/animation-replacement"
spec=importlib.util.spec_from_file_location("model_import",Path(__file__).with_name("import-models.py"))
model_import=importlib.util.module_from_spec(spec); spec.loader.exec_module(model_import)
manifest=json.loads((OUT/"model-sources.json").read_text())
library=unreal.EditorAssetLibrary; tools=unreal.AssetToolsHelpers.get_asset_tools()
unreal.SystemLibrary.execute_console_command(None,"Interchange.FeatureFlags.Import.FBX 0")

def import_one(name,record,skeletal):
    source=ROOT/record["source"]; fbx=ROOT/record["fbx"]
    if hashlib.sha256(source.read_bytes()).hexdigest()!=record["sourceSha256"] or hashlib.sha256(fbx.read_bytes()).hexdigest()!=record["fbxSha256"]:
        raise RuntimeError("Changed model source: "+name)
    gltf,images=model_import.read_glb(source)
    if gltf.get("animations"): raise RuntimeError("Body/rig sources must contain no animation tracks")
    destination="/Game/Characters/Models/"+name+"/"+record["sourceSha256"][:12]
    if name=="IconOfWrath": destination="/Game/Characters/Equipment"
    context=dict(profile=name,directory=source.parent,gltf=gltf,images=images,destination=destination,
        conversion=dict(kind="characterProfiles" if skeletal else "staticProps",sourceSha256=record["sourceSha256"]))
    path=destination+"/"+name
    mesh=unreal.load_asset(path) if library.does_asset_exist(path) else None
    if mesh:
        model_import.require_owned(unreal,mesh,context)
        return dict(mesh=mesh.get_path_name(),**record)
    options=unreal.FbxImportUI()
    kind=unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else unreal.FBXImportType.FBXIT_STATIC_MESH
    options.set_editor_properties(dict(automated_import_should_detect_type=False,mesh_type_to_import=kind,
        original_import_type=kind,import_as_skeletal=skeletal,import_mesh=True,import_animations=False,
        create_physics_asset=False,import_materials=False,import_textures=False))
    for data in (options.skeletal_mesh_import_data,options.static_mesh_import_data):
        data.set_editor_properties(dict(convert_scene=True,convert_scene_unit=True,force_front_x_axis=False,import_uniform_scale=1.))
    options.skeletal_mesh_import_data.set_editor_properties(dict(use_t0_as_ref_pose=False,update_skeleton_reference_pose=False,
        normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS))
    options.static_mesh_import_data.set_editor_properties(dict(combine_meshes=True,auto_generate_collision=False))
    task=unreal.AssetImportTask(); task.set_editor_properties(dict(filename=str(fbx),destination_path=destination,
        destination_name=name,automated=True,save=False,replace_existing=False,factory=unreal.FbxFactory(),options=options))
    tools.import_asset_tasks([task])
    mesh=unreal.load_asset(path)
    expected=unreal.SkeletalMesh if skeletal else unreal.StaticMesh
    if not isinstance(mesh,expected): raise RuntimeError("Body/equipment import failed: "+name)
    textures,_=model_import.import_textures(unreal,context)
    materials,_=model_import.create_materials(unreal,context,textures)
    mapping=model_import.material_slot_mapping(materials.keys())
    prop="materials" if skeletal else "static_materials"
    slots=list(mesh.get_editor_property(prop)); seen=set()
    for slot in slots:
        original=mapping.get(str(slot.material_slot_name))
        if not original: raise RuntimeError("Material slot changed: "+str(slot.material_slot_name))
        slot.material_interface=materials[original]; seen.add(original)
    if seen!=set(materials): raise RuntimeError("Missing authored material: "+name)
    mesh.set_editor_property(prop,slots)
    for asset_path in library.list_assets(destination,recursive=True):
        asset=unreal.load_asset(asset_path)
        model_import.mark_owned(unreal,asset,context)
        if not library.save_loaded_asset(asset,False): raise RuntimeError("Save failed: "+asset_path)
    return dict(mesh=mesh.get_path_name(),**record)

result={}
for profile,record in manifest["profiles"].items():
    skeletal=profile!="IconOfWrath"
    entry=import_one(profile,record,skeletal)
    for slot in ("weapon","shield"):
        if slot in record: entry[slot]=import_one(Path(record[slot]["source"]).stem,record[slot],False)
    result[profile]=entry
    (OUT/"bodies.json").write_text(json.dumps(dict(schemaVersion=1,profiles=result),indent=2)+"\n")
    unreal.log("WAR_REPLACEMENT_BODY="+profile)
