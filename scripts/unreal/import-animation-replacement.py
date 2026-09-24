"""UE commandlet: import supplied templates and retarget measured character rigs.

Creates new assets only. Installation requires separate equipped-motion checks.
"""
import hashlib
import json
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from animation_replacement import ROOT, SOURCE, OUT, CLIPS, PROFILES, RECIPES, CHAINS, locomotion, selected

OUT.mkdir(parents=True, exist_ok=True)
inventory = json.loads((OUT / "sources.json").read_text())["clips"]
identity = hashlib.sha256(json.dumps({k:v["sha256"] for k,v in inventory.items()}, sort_keys=True).encode()).hexdigest()[:12]
BASE = "/Game/Characters/AnimationReplacement/" + identity
OWNER = "WarSuppliedAnimationSet"
library = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
from native_animation_settings import compression_settings
compression=compression_settings()
unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")

def save(asset):
    library.set_metadata_tag(asset, OWNER, identity)
    if not library.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Could not save " + asset.get_path_name())

def own(path, cls, factory):
    asset = unreal.load_asset(path) if library.does_asset_exist(path) else None
    if asset and library.get_metadata_tag(asset, OWNER) != identity:
        raise RuntimeError("Unowned asset: " + path)
    return asset or tools.create_asset(path.rsplit("/",1)[1], path.rsplit("/",1)[0], cls, factory)

def source(key, skeleton=None):
    folder = BASE + "/Sources/" + key.replace(".", "_")
    if hashlib.sha256((SOURCE/CLIPS[key]).read_bytes()).hexdigest() != inventory[key]["sha256"]:
        raise RuntimeError("Source changed after inventory: " + key)
    existing = library.list_assets(folder, recursive=False)
    if existing:
        assets = [unreal.load_asset(p) for p in existing]
        if any(library.get_metadata_tag(a, OWNER) != identity for a in assets):
            raise RuntimeError("Unowned source import: " + folder)
        return assets
    options = unreal.FbxImportUI()
    kind = unreal.FBXImportType.FBXIT_ANIMATION if skeleton else unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.set_editor_properties(dict(automated_import_should_detect_type=False, mesh_type_to_import=kind,
        original_import_type=kind, import_as_skeletal=True, import_mesh=skeleton is None,
        import_animations=True, create_physics_asset=False, import_materials=False, import_textures=False))
    if skeleton: options.skeleton = skeleton
    for name in ("skeletal_mesh_import_data", "anim_sequence_import_data"):
        options.get_editor_property(name).set_editor_properties(dict(convert_scene=True, convert_scene_unit=True,
            force_front_x_axis=False, import_uniform_scale=1.0))
    options.anim_sequence_import_data.set_editor_properties(dict(
        animation_length=unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
        use_default_sample_rate=False, custom_sample_rate=round(inventory[key]["fps"]), import_bone_tracks=True,
        preserve_local_transform=False, remove_redundant_keys=False))
    task = unreal.AssetImportTask()
    task.set_editor_properties(dict(filename=str(SOURCE/CLIPS[key]), destination_path=folder,
        destination_name=key.replace(".", "_"), automated=True, save=False, replace_existing=False,
        factory=unreal.FbxFactory(), options=options))
    tools.import_asset_tasks([task])
    assets = [unreal.load_asset(p) for p in library.list_assets(folder, recursive=False)]
    if not any(isinstance(a, unreal.AnimSequence) for a in assets): raise RuntimeError("Import failed: " + key)
    for asset in assets: save(asset)
    return assets

first = source("two.idle")
source_mesh = next(a for a in first if isinstance(a, unreal.SkeletalMesh))
sequences = {"two.idle": next(a for a in first if isinstance(a, unreal.AnimSequence))}
for key in CLIPS:
    if key not in sequences:
        sequences[key] = next(a for a in source(key, source_mesh.skeleton) if isinstance(a, unreal.AnimSequence))

def rig(path, mesh, is_source):
    asset = own(path, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    controller = unreal.IKRigController.get_controller(asset)
    controller.set_skeletal_mesh(mesh)
    for chain in controller.get_retarget_chains(): controller.remove_retarget_chain(chain.chain_name)
    controller.set_retarget_root("Hips" if is_source else "hips")
    controller.set_root_motion_bone("Hips" if is_source else "root")
    for name,start,end,target_start,target_end in CHAINS:
        controller.add_retarget_chain(name, start if is_source else target_start, end if is_source else target_end, "None")
    save(asset)
    return asset

source_rig = rig(BASE+"/IK_Source", source_mesh, True)
registry = json.loads((ROOT/"unreal/AegisWar/Content/Migration/visual-imports.json").read_text())
targets = {e["profileKey"]: e["skeletalMeshPath"] for e in registry["entries"]}
extra = OUT/"bodies.json"
if extra.exists(): targets.update({k:v["mesh"] for k,v in json.loads(extra.read_text())["profiles"].items() if k in PROFILES})
result = dict(schemaVersion=1, identity=identity, sources={k:a.get_path_name() for k,a in sequences.items()}, profiles={})
if (OUT/'retarget.json').exists(): result['profiles']=json.loads((OUT/'retarget.json').read_text())['profiles']
for profile,path in targets.items():
    if not selected(profile): continue
    target = unreal.load_asset(path)
    if not isinstance(target, unreal.SkeletalMesh): raise RuntimeError("Missing target: " + path)
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(target)
    root_bone = str(component.get_bone_name(0))
    # A changed body gets its own retarget destination, avoiding stale baked poses.
    destination = BASE + "/" + profile
    target_rig = rig(destination+"/IK_Target", target, False)
    retarget = own(destination+"/RTG_Target", unreal.IKRetargeter, unreal.IKRetargetFactory())
    controller = unreal.IKRetargeterController.get_controller(retarget)
    for side,asset,mesh in ((unreal.RetargetSourceOrTarget.SOURCE,source_rig,source_mesh),
                            (unreal.RetargetSourceOrTarget.TARGET,target_rig,target)):
        controller.set_ik_rig(side,asset); controller.set_preview_mesh(side,mesh)
    controller.remove_all_ops(); controller.add_default_ops()
    for index in range(controller.get_num_retarget_ops()):
        if str(controller.get_op_name(index)) == "Root Motion": controller.set_retarget_op_enabled(index,False)
    controller.auto_map_chains(unreal.AutoMapChainType.EXACT, True)
    controller.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET)
    save(retarget)
    if profile in PROFILES:
        career,style = PROFILES[profile]
        keys = set(locomotion(style).values())
        for _,sources,*_ in RECIPES[career]: keys.update(sources)
    else:
        keys = set(locomotion("spell").values()) | {"shield.slash", "spell.bolt", "spell.focus"}
    keys = sorted(keys)
    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_properties(dict(assets_to_retarget=[library.find_asset_data(sequences[k].get_path_name()) for k in keys],
        source_mesh=source_mesh, target_mesh=target, ik_retarget_asset=retarget, target_path=destination+"/Clips",
        prefix="New_", use_source_path=False, include_referenced_assets=False, overwrite_existing_files=True))
    outputs = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    if len(outputs) != len(keys): raise RuntimeError("Incomplete retarget: " + profile)
    clips = {}
    for key in keys:
        animation = unreal.load_asset(destination+"/Clips/New_"+sequences[key].get_name())
        if not animation or animation.get_editor_property("skeleton") != target.skeleton: raise RuntimeError("Retarget skeleton mismatch: " + key)
        options = unreal.AnimPoseEvaluationOptions()
        options.optional_skeletal_mesh = target
        duration = unreal.AnimationLibrary.get_sequence_length(animation)
        count = round(duration*30)+1
        poses = [unreal.AnimPoseExtensions.get_anim_pose_at_time(animation,min(i/30,duration),options) for i in range(count)]
        top = unreal.AnimPoseExtensions.get_ref_bone_pose(poses[0],root_bone,unreal.AnimPoseSpaces.LOCAL)
        scale = top.scale3d
        if min(scale.x,scale.y,scale.z) <= 0 or max(scale.x,scale.y,scale.z)-min(scale.x,scale.y,scale.z) > .001:
            raise RuntimeError("Unsupported non-uniform bind units: " + profile)
        hips = [unreal.AnimPoseExtensions.get_bone_pose(p,"hips",unreal.AnimPoseSpaces.LOCAL) for p in poses]
        # Locomotion/capsule translation has one owner: CharacterMovement. Retain
        # articulated bob/rotation; eliminate cumulative horizontal root travel.
        positions = [h.translation/scale.x for h in hips]
        origin = positions[0]
        native_speed=(positions[-1]-origin).length()*scale.x/max(.001,duration)
        if key.rsplit('.',1)[-1] in {'walk','back','run','left','right'}:
            travel=positions[-1]-origin
            positions=[p-unreal.Vector(travel.x,travel.y,0)*(i/(count-1)) for i,p in enumerate(positions)]
        else:
            positions = [unreal.Vector(origin.x,origin.y,p.z) for p in positions]
        data = animation.controller
        data.open_bracket("Restore target bind units and remove duplicate horizontal travel",False)
        for bone,translations,rotations,scales in (
            (root_bone,[top.translation]*count,[top.rotation]*count,[scale]*count),
            ("hips",positions,[h.rotation for h in hips],[h.scale3d for h in hips])):
            if not data.set_bone_track_keys(bone,translations,rotations,scales,False): raise RuntimeError("Track correction failed: "+bone)
        data.close_bracket(False)
        animation.set_editor_property('bone_compression_settings',compression)
        if not unreal.WarImportLibrary.finalize_animation_sampling(animation): raise RuntimeError("Compression failed: "+key)
        save(animation)
        clips[key] = dict(animation=animation.get_path_name(),duration=duration,sourceSha256=inventory[key]["sha256"],
                          bindScale=scale.x,locomotionSpeedCm=native_speed,gameplayVerified=False)
    result["profiles"][profile] = dict(mesh=path,retargeter=retarget.get_path_name(),clips=clips)
    (OUT/"retarget.json").write_text(json.dumps(result,indent=2)+"\n")
    unreal.log("WAR_REPLACEMENT_RETARGETED="+profile+":"+str(len(clips)))
