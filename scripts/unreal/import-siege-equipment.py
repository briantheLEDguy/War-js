"""Import authored engines and fit the supplied walk to measured engineer grips.

Writes owned private assets only. Review and map installation are separate.
"""
import hashlib,importlib.util,json,math,sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from supplied_stow import component_pose,between,inverse,unit
from native_animation_settings import compression_settings
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/siege/equipment'
BASE='/Game/Siege/Equipment'
OWNER='WarSiegeEquipmentV1'
library=unreal.EditorAssetLibrary;tools=unreal.AssetToolsHelpers.get_asset_tools()
spec=importlib.util.spec_from_file_location('model_import',Path(__file__).with_name('import-models.py'))
models=importlib.util.module_from_spec(spec);spec.loader.exec_module(models)
manifest=json.loads((OUT/'sources.json').read_text())
unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')

def save(asset):
    library.set_metadata_tag(asset,OWNER,'1')
    if not library.save_loaded_asset(asset,False): raise RuntimeError('Save failed: '+asset.get_path_name())

def owned(path):
    asset=unreal.load_asset(path) if library.does_asset_exist(path) else None
    if asset and library.get_metadata_tag(asset,OWNER)!='1': raise RuntimeError('Preserve unowned asset: '+path)
    return asset

def mesh(record):
    source=ROOT/record['source'];fbx=ROOT/record['fbx'];name=fbx.stem
    if hashlib.sha256(source.read_bytes()).hexdigest()!=record['sourceSha256'] or hashlib.sha256(fbx.read_bytes()).hexdigest()!=record['fbxSha256']:
        raise RuntimeError('Changed source: '+name)
    directory=BASE+'/Meshes/'+record['sourceSha256'][:12];path=directory+'/'+name
    # Identical adapted pennants share their exact source digest and native mesh.
    for candidate in library.list_assets(directory,recursive=False):
        asset=unreal.load_asset(candidate)
        if isinstance(asset,unreal.StaticMesh) and library.get_metadata_tag(asset,OWNER)=='1':return asset
    current=owned(path)
    if current:return current
    gltf,images=models.read_glb(source)
    context=dict(profile=name,directory=source.parent,gltf=gltf,images=images,destination=directory,
        conversion=dict(kind='staticProps',sourceSha256=record['sourceSha256']))
    options=unreal.FbxImportUI()
    options.set_editor_properties(dict(automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
        original_import_type=unreal.FBXImportType.FBXIT_STATIC_MESH,import_as_skeletal=False,import_mesh=True,
        import_animations=False,import_materials=False,import_textures=False))
    options.static_mesh_import_data.set_editor_properties(dict(convert_scene=True,convert_scene_unit=True,force_front_x_axis=False,
        import_uniform_scale=1.,combine_meshes=True,auto_generate_collision=False))
    task=unreal.AssetImportTask();task.set_editor_properties(dict(filename=str(fbx),destination_path=directory,destination_name=name,
        automated=True,save=False,replace_existing=False,factory=unreal.FbxFactory(),options=options))
    tools.import_asset_tasks([task]);result=unreal.load_asset(path)
    if not isinstance(result,unreal.StaticMesh):raise RuntimeError('Missing mesh: '+name)
    textures,_=models.import_textures(unreal,context);materials,_=models.create_materials(unreal,context,textures)
    mapping=models.material_slot_mapping(materials.keys());slots=list(result.static_materials)
    for slot in slots:slot.material_interface=materials[mapping[str(slot.material_slot_name)]]
    result.static_materials=slots
    for item in library.list_assets(directory,recursive=True):save(unreal.load_asset(item))
    return result

visual=unreal.load_asset('/Game/Characters/SiegeStaging/Visual_npc_siege_riftbound_breach_engineer')
body=visual.skeletal_mesh
component=unreal.new_object(unreal.SkeletalMeshComponent);component.set_skeletal_mesh_asset(body)
walk=visual.imported_animations['walk']
options=unreal.AnimPoseEvaluationOptions();options.set_editor_properties(dict(optional_skeletal_mesh=body,evaluation_type=unreal.AnimDataEvalType.RAW))
corrections=json.loads((Path(__file__).parent/'animation-recipes/corrections/engineer-push.json').read_text())
all_clips={};grip_errors={}
for engine,correction in corrections.items():
    duration=unreal.AnimationLibrary.get_sequence_length(walk);count=round(duration*30)+1
    rows=[];maximum_error=0
    for i in range(count):
        pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(walk,min(i/30,duration),options)
        row={str(n):unreal.AnimPoseExtensions.get_bone_pose(pose,n,unreal.AnimPoseSpaces.LOCAL) for n in unreal.AnimPoseExtensions.get_bone_names(pose)}
        world=component_pose(row,component)
        angle=-math.radians(correction['spineLeanDegrees'])/2
        lean=unreal.Quat(math.sin(angle),0,0,math.cos(angle))
        row['spine'].rotation=inverse(world['hips'].rotation)*lean*world['spine'].rotation
        world=component_pose(row,component)
        for side,sign in [('L',1),('R',-1)]:
            upper,lower,hand='upper_arm_'+side,'forearm_'+side,'hand_'+side
            shoulder,elbow,wrist=world[upper],world[lower],world[hand]
            start=shoulder.translation
            target=unreal.Vector(sign*correction['handX'],correction['handY'],correction['handZ'])
            delta=target-start;a=(elbow.translation-start).length();b=(wrist.translation-elbow.translation).length()
            distance=max(abs(a-b)+.01,min(a+b-.01,delta.length()))
            maximum_error=max(maximum_error,abs(distance-delta.length()))
            direction=unit(delta);hint=unreal.Vector(sign*.6,0,-1)
            pole=unit(hint-direction*hint.dot(direction))
            along=(a*a-b*b+distance*distance)/(2*distance)
            joint=start+direction*along+pole*math.sqrt(max(0,a*a-along*along))
            end=start+direction*distance
            qr=between(elbow.translation-start,joint-start)*shoulder.rotation
            ql=between(wrist.translation-elbow.translation,end-joint)*elbow.rotation
            row[upper].rotation=inverse(world['shoulder_'+side].rotation)*qr
            row[lower].rotation=inverse(qr)*ql
            # Preserve the source wrist orientation while locking its palm to the timber.
            row[hand].rotation=inverse(ql)*wrist.rotation
        actual=component_pose(row,component)
        for side,sign in [('L',1),('R',-1)]:
            maximum_error=max(maximum_error,(actual['hand_'+side].translation-unreal.Vector(sign*correction['handX'],correction['handY'],correction['handZ'])).length())
        rows.append(row)
    if maximum_error>1:raise RuntimeError(engine+' engineer grip is unreachable: '+str(maximum_error))
    clips={}
    for name,frames in [('EngineerPush',rows),('EngineerHold',[rows[0]]*31)]:
        path=BASE+'/Crew/'+engine+'_'+name;asset=owned(path) or library.duplicate_asset(walk.get_path_name(),path)
        data=asset.controller;data.open_bracket('Character-specific supplied-walk grip fit',False)
        data.set_frame_rate(unreal.FrameRate(30,1),False);data.set_number_of_frames(unreal.FrameNumber(len(frames)-1),False)
        for bone in frames[0]:
            if not data.set_bone_track_keys(bone,[r[bone].translation for r in frames],[r[bone].rotation for r in frames],[r[bone].scale3d for r in frames],False):
                raise RuntimeError('Failed track: '+bone)
        data.close_bracket(False);asset.set_editor_property('bone_compression_settings',compression_settings())
        if not unreal.WarImportLibrary.finalize_animation_sampling(asset):raise RuntimeError('Compression failed')
        save(asset);clips[name]=asset
    all_clips[engine]=clips;grip_errors[engine]=maximum_error

def transform(frame):
    return unreal.Transform(location=unreal.Vector(*frame['p']),rotation=unreal.Quat(*frame['q']).rotator(),scale=unreal.Vector(*frame['s']))

result={}
for name,record in manifest.items():
    parts=[]
    for item in record['parts']:
        part=unreal.WarSiegeEquipmentPart();part.set_editor_properties(dict(mesh=mesh(item),
            roll=[transform(f) for f in item.get('roll',[dict(p=[0,0,0],q=[0,0,0,1],s=[1,1,1])]*2)],
            strike=[transform(f) for f in item.get('strike',[])] if any(key in item['fbx'] for key in ('striker','suspension')) else []))
        parts.append(part)
    if name=='RiftboundStandard':result[name]=[p.get_editor_property('mesh').get_path_name() for p in parts];continue
    path=BASE+'/'+name
    factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',unreal.WarSiegeEquipmentDefinition)
    definition=owned(path) or tools.create_asset(name,BASE,unreal.WarSiegeEquipmentDefinition,factory)
    definition.set_editor_properties(dict(parts=parts,hull_extent=unreal.Vector(245 if name=='Ram' else 210,178,120),
        crew_positions=[unreal.Vector(corrections[name]['crewX'],s*corrections[name]['crewY'],0) for s in (-1,1)],
        push_animation=all_clips[name]['EngineerPush'],hold_animation=all_clips[name]['EngineerHold'],walk_speed=100.,wheel_circumference=424.,
        battering_ram=name=='Ram',strike_duration=1.5,source_sha256=record['sourceSha256'],reviewed=False))
    save(definition);result[name]=definition.get_path_name()
(OUT/'native.json').write_text(json.dumps(dict(assets=result,gripErrorCm=grip_errors,walkSource=walk.get_path_name(),reviewed=False,
    sourceManifestSha256=hashlib.sha256((OUT/'sources.json').read_bytes()).hexdigest(),
    gripRecipeSha256=hashlib.sha256((Path(__file__).parent/'animation-recipes/corrections/engineer-push.json').read_bytes()).hexdigest()),indent=2)+'\n')
