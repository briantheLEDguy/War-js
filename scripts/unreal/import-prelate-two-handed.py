"""Import local supplied FBXs and retarget onto the equipped Battle Prelate.

Run with UnrealEditor-Cmd -unattended -run=pythonscript -script=<this file>.
The source mannequin is only a retarget reference, never a gameplay visual.
"""
import hashlib
import json
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from prelate_two_handed import CLIPS, CHAINS

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "unreal/AegisWar/AnimationImport/Two-handed"
OUT = ROOT / "artifacts/unreal/two-handed"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "retarget.json").unlink(missing_ok=True)
OWNER = "WarPrelateTwoHanded"
tools = unreal.AssetToolsHelpers.get_asset_tools()
library = unreal.EditorAssetLibrary
receipt = json.loads((ROOT / "artifacts/unreal/converted/civic_battle_prelate_m/editor-import.json").read_text())
target = unreal.load_asset(receipt["meshes"][0]["path"])
if not target:
    raise RuntimeError("Import the equipped Battle Prelate first")
hashes = {key: hashlib.sha256((SOURCE / filename).read_bytes()).hexdigest() for key, filename in CLIPS.items()}
identity = hashlib.sha256(json.dumps([hashes, receipt['fbxSha256']], sort_keys=True).encode()).hexdigest()[:12]
PACKAGE = "/Game/Imported/PrelateTwoHanded/" + identity
unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")


def save(asset):
    library.set_metadata_tag(asset, OWNER, identity)
    if not library.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Could not save " + asset.get_path_name())


def owned_asset(name, cls, factory):
    asset = unreal.load_asset(PACKAGE + "/" + name) if library.does_asset_exist(PACKAGE + "/" + name) else None
    if asset and library.get_metadata_tag(asset, OWNER) != identity:
        raise RuntimeError("Refusing to overwrite an unowned asset: " + name)
    return asset or tools.create_asset(name, PACKAGE, cls, factory)


def import_fbx(key, skeleton=None):
    destination = PACKAGE + "/Source/" + key
    existing = library.list_assets(destination, recursive=False)
    if existing:
        assets = [unreal.load_asset(path) for path in existing]
        if any(library.get_metadata_tag(asset, OWNER) != identity for asset in assets):
            raise RuntimeError("Unowned source import: " + destination)
        return assets
    options = unreal.FbxImportUI()
    kind = unreal.FBXImportType.FBXIT_ANIMATION if skeleton else unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.set_editor_properties(dict(automated_import_should_detect_type=False, mesh_type_to_import=kind,
        original_import_type=kind, import_as_skeletal=True, import_mesh=skeleton is None,
        import_animations=True, create_physics_asset=False, import_materials=False, import_textures=False))
    if skeleton:
        options.skeleton = skeleton
    for name in ("skeletal_mesh_import_data", "anim_sequence_import_data"):
        options.get_editor_property(name).set_editor_properties(dict(convert_scene=True, convert_scene_unit=True,
            force_front_x_axis=False, import_uniform_scale=1.0))
    options.anim_sequence_import_data.set_editor_properties(dict(
        animation_length=unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
        use_default_sample_rate=False, custom_sample_rate=30, import_bone_tracks=True,
        preserve_local_transform=False, remove_redundant_keys=False))
    task = unreal.AssetImportTask()
    task.set_editor_properties(dict(filename=str(SOURCE / CLIPS[key]), destination_path=destination,
        destination_name=key, automated=True, save=False, replace_existing=False, factory=unreal.FbxFactory(), options=options))
    tools.import_asset_tasks([task])
    assets = [unreal.load_asset(path) for path in library.list_assets(destination, recursive=False)]
    if not any(isinstance(asset, unreal.AnimSequence) for asset in assets):
        raise RuntimeError("Animation import failed: " + key)
    for asset in assets:
        save(asset)
    return assets


first = import_fbx("idle")
source_mesh = next(asset for asset in first if isinstance(asset, unreal.SkeletalMesh))
source_skeleton = source_mesh.skeleton
sequences = {"idle": next(asset for asset in first if isinstance(asset, unreal.AnimSequence))}
for key in CLIPS:
    if key != "idle":
        sequences[key] = next(asset for asset in import_fbx(key, source_skeleton) if isinstance(asset, unreal.AnimSequence))


def make_rig(name, mesh, source):
    rig = owned_asset(name, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    controller = unreal.IKRigController.get_controller(rig)
    controller.set_skeletal_mesh(mesh)
    for chain in controller.get_retarget_chains():
        controller.remove_retarget_chain(chain.chain_name)
    # The native FBX importer removes Mixamo namespaces.
    controller.set_retarget_root("Hips" if source else "hips")
    controller.set_root_motion_bone("Hips" if source else "root")
    for chain, start, end, target_start, target_end in CHAINS:
        controller.add_retarget_chain(chain, start if source else target_start, end if source else target_end, "None")
    save(rig)
    return rig


source_rig = make_rig("IK_Source", source_mesh, True)
target_rig = make_rig("IK_Prelate", target, False)
retarget = owned_asset("RTG_Prelate", unreal.IKRetargeter, unreal.IKRetargetFactory())
controller = unreal.IKRetargeterController.get_controller(retarget)
controller.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, source_rig)
controller.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, target_rig)
controller.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, source_mesh)
controller.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, target)
controller.remove_all_ops()
controller.add_default_ops()
for index in range(controller.get_num_retarget_ops()):
    if str(controller.get_op_name(index)) == "Root Motion":
        controller.set_retarget_op_enabled(index, False)
controller.auto_map_chains(unreal.AutoMapChainType.EXACT, True)
controller.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET)
save(retarget)
# Keep the original skeleton and every source material. The adapted mesh differs
# only in the rigid hammer's position along its own shaft.
grip_source = json.loads((OUT / "weapon.json").read_text())
if grip_source["sourceSha256"] != receipt["sourceSha256"]:
    raise RuntimeError("Grip adaptation belongs to a different equipped body")
adaptation_path = PACKAGE + "/Grip_" + grip_source["fbxSha256"][:12]
adapted = unreal.load_asset(adaptation_path + "/PrelateTwoHanded") if library.does_asset_exist(adaptation_path + "/PrelateTwoHanded") else None
if adapted and library.get_metadata_tag(adapted, OWNER) != identity:
    raise RuntimeError("Refusing to replace an unowned grip adaptation")
if not adapted:
    options = unreal.FbxImportUI()
    options.set_editor_properties(dict(automated_import_should_detect_type=False,
        mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH,
        original_import_type=unreal.FBXImportType.FBXIT_SKELETAL_MESH,
        import_as_skeletal=True, import_mesh=True, import_animations=False,
        import_materials=False, import_textures=False, create_physics_asset=False, skeleton=target.skeleton))
    options.skeletal_mesh_import_data.set_editor_properties(dict(convert_scene=True, convert_scene_unit=True,
        force_front_x_axis=False, update_skeleton_reference_pose=False, use_t0_as_ref_pose=False))
    task = unreal.AssetImportTask()
    task.set_editor_properties(dict(filename=str(OUT / "prelate-two-handed.fbx"), destination_path=adaptation_path,
        destination_name="PrelateTwoHanded", automated=True, save=False, factory=unreal.FbxFactory(), options=options))
    tools.import_asset_tasks([task])
    adapted = unreal.load_asset(adaptation_path + "/PrelateTwoHanded")
if not adapted or adapted.skeleton != target.skeleton:
    raise RuntimeError("Adapted hammer changed the equipped skeleton")
old_materials = {str(material.material_slot_name).replace(".", "_"): material.material_interface for material in target.materials}
if set(old_materials) != {str(material.material_slot_name) for material in adapted.materials}:
    raise RuntimeError("Adapted mesh changed material slots: " + str(list(old_materials)) + " -> " + str([str(m.material_slot_name) for m in adapted.materials]))
materials = list(adapted.materials)
for material in materials:
    material.material_interface = old_materials[str(material.material_slot_name)]
adapted.set_editor_property("materials", materials)
save(adapted)
inputs = unreal.IKRetargetBatchOperationInputs()
inputs.set_editor_properties(dict(assets_to_retarget=[library.find_asset_data(asset.get_path_name()) for asset in sequences.values()],
    source_mesh=source_mesh, target_mesh=target, ik_retarget_asset=retarget, target_path=PACKAGE + "/Animations",
    prefix="Prelate_", use_source_path=False, include_referenced_assets=False, overwrite_existing_files=True))
outputs = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
if len(outputs) != len(CLIPS):
    raise RuntimeError("Retarget did not produce every source clip")
result = {}
for key, source in sequences.items():
    path = PACKAGE + "/Animations/Prelate_" + source.get_name()
    animation = unreal.load_asset(path)
    if not animation or animation.get_editor_property("skeleton") != target.skeleton:
        raise RuntimeError("Retarget skeleton mismatch: " + key)
    # The existing FBX skeleton has a 100x armature above meter-space bones.
    # UE's retargeter strips this bind scale; restore it and convert the pelvis
    # motion back to that parent's units, without changing the mesh/skeleton.
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property("optional_skeletal_mesh", target)
    duration = unreal.AnimationLibrary.get_sequence_length(animation)
    count = round(duration * 30) + 1
    poses = [unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, min(i / 30, duration), options)
             for i in range(count)]
    top = unreal.AnimPoseExtensions.get_ref_bone_pose(poses[0], "humanoid_game_v2", unreal.AnimPoseSpaces.LOCAL)
    if (top.scale3d - unreal.Vector(100, 100, 100)).length() > .001:
        raise RuntimeError("This recipe's 100x bind-unit correction does not match the target rig")
    hips = [unreal.AnimPoseExtensions.get_bone_pose(pose, "hips", unreal.AnimPoseSpaces.LOCAL) for pose in poses]
    data = animation.controller
    data.open_bracket("Restore equipped skeleton bind units", False)
    if not data.set_bone_track_keys("humanoid_game_v2", [top.translation] * count, [top.rotation] * count,
                                   [top.scale3d] * count, False):
        raise RuntimeError("Cannot restore armature scale")
    if not data.set_bone_track_keys("hips", [hip.translation / 100 for hip in hips],
                                   [hip.rotation for hip in hips], [hip.scale3d for hip in hips], False):
        raise RuntimeError("Cannot restore pelvis units")
    data.close_bracket(False)
    if not unreal.WarImportLibrary.prepare_compressed_animation(animation):
        raise RuntimeError("Animation compression failed")
    save(animation)
    result[key] = dict(sourceFile=CLIPS[key], sourceSha256=hashes[key], sourceAnimation=source.get_path_name(),
        animation=animation.get_path_name(), duration=unreal.AnimationLibrary.get_sequence_length(animation))
ops = []
for index in range(controller.get_num_retarget_ops()):
    op = controller.get_op_controller(index)
    ops.append(dict(name=str(controller.get_op_name(index)), type=op.get_class().get_name(),
        methods=[name for name in dir(op) if 'setting' in name]))
(OUT / "retarget.json").write_text(json.dumps(dict(schemaVersion=1, status="retargeted-pending-grip-review", identity=identity,
    targetMesh=adapted.get_path_name(), originalMesh=target.get_path_name(), sourceMesh=source_mesh.get_path_name(), retargeter=retarget.get_path_name(),
    clips=result, ops=ops), indent=2) + "\n")
unreal.log("WAR_PRELATE_RETARGETED=" + str(len(result)))
