"""Add measured kit timber ceilings to fresh copies of verified private home shells."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_home_ceiling import ceiling_recipe, TIMBER
from t1_materials import protected_saved, verify_protected, sha, same_state
from t1_material_clone import inventory, clone

DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
CONTENT = ROOT/'unreal/AegisWar/Content'
package_file = lambda p: CONTENT/(p.split('.')[0].removeprefix('/Game/')+'.umap')
asset_file = lambda p: CONTENT/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
parent = json.loads((DIRECTORY/'shells-latest.json').read_text())
seams = json.loads((DIRECTORY/'shell-seam-review.json').read_text())
homes_review = json.loads((DIRECTORY/'shell-home-review.json').read_text())
if (parent.get('study') != 'home-shell-refit' or parent['activeCampaignChanged']
    or seams['signature'] != parent['signature'] or not seams['seamRaysClosed']
    or homes_review['signature'] != parent['signature'] or not homes_review['capsuleClear']):
    raise RuntimeError('Ceilings require the verified isolated roof/capsule parent')
if [z['id'] for z in parent['zones']] != ['sunmeadow_march','cinderfen_outskirts'] or any(len(z['homes']) != 2 for z in parent['zones']):
    raise RuntimeError('Ceiling authoring admits only four reserved first-batch homes')
for zone in parent['zones']:
    if not zone['map'].startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_'+parent['signature'][:12]+'_') or not zone['map'].endswith('/'+zone['id']+'/Review'):
        raise RuntimeError('Ceiling parent is outside the isolated first-pair namespace')
if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower(): raise RuntimeError('Ceiling merging requires rendering')
for package,digest in {**parent['inputs']['parentPackages'],**parent['packageHashes']}.items():
    if sha(package_file(package)) != digest: raise RuntimeError('Preserve edited parent maps')
for file,digest in {**parent['inputs']['sourceHashes'],**parent['inputs']['tools'],**parent['inputs']['parentAssetHashes'],**parent['assetHashes']}.items():
    if sha(ROOT/file) != digest: raise RuntimeError('Parent inputs or assets changed')
verify_protected(ROOT,parent['inputs']['protectedHashes'])
protected = protected_saved(ROOT)
staged_file = ROOT/'artifacts/unreal/capital-expansion/staged.json'
staged = {r['path']:r['sha256'] for r in json.loads(staged_file.read_text())['files']}
registry = unreal.AssetRegistryHelpers.get_asset_registry()
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,
    include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
dependencies = dict(parent['inputs']['dependencyHashes']); pending = [TIMBER.split('.')[0]]
while pending:
    package = pending.pop()
    if package in dependencies: continue
    if not package.startswith(('/Game/Medieval_Environment/','/Game/Medieval_Mod_Town/')) or '..' in package or len(dependencies)>2048:
        raise RuntimeError('Ceiling dependency is outside the staged private kits')
    dependencies[package] = sha(asset_file(package))
    pending.extend(str(p) for p in registry.get_dependencies(package,options) if str(p).startswith('/Game/'))
for package,digest in dependencies.items():
    if sha(asset_file(package)) != digest: raise RuntimeError('Preserve changed source dependencies')
    if package.startswith(('/Game/Medieval_Environment/','/Game/Medieval_Mod_Town/')) and staged.get(package.removeprefix('/Game/')+'.uasset') != digest:
        raise RuntimeError('Timber sources differ from their reviewed staging receipt')
timber = unreal.load_asset(TIMBER)
if not isinstance(timber,unreal.StaticMesh) or len(timber.static_materials)!=1:
    raise RuntimeError('Measured timber source is unavailable or changed slots')
b = timber.get_bounds(); timber_bounds = dict(origin=[b.origin.x,b.origin.y,b.origin.z],extent=[b.box_extent.x,b.box_extent.y,b.box_extent.z])
recipes = {}
for zone in parent['zones']:
    for home in zone['homes']:
        template = parent['inputs']['refits'][home['template']]['template']
        recipes[home['id']] = ceiling_recipe(template,parent['inputs']['sourceBounds'],timber_bounds,zone['id'])
source_material = timber.get_material(0)
parameters = list(map(str,unreal.MaterialEditingLibrary.get_vector_parameter_names(source_material)))
if 'Base_Color_Tint' not in parameters: raise RuntimeError('Timber palette parameter needs a new review')
tint = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(source_material,'Base_Color_Tint')
source_tint = [tint.r,tint.g,tint.b,tint.a]
tools = ['scripts/unreal/build-t1-ceiling-studies.py','scripts/unreal/t1_home_ceiling.py','scripts/unreal/t1_home_shell.py',
    'scripts/unreal/t1_material_clone.py','scripts/unreal/t1_materials.py','unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll']
inputs = dict(parentShellSignature=parent['signature'],parentPlanSha256=parent['inputs']['parentPlanSha256'],
    parentPackages={**parent['inputs']['parentPackages'],**parent['packageHashes']},dependencyHashes=dependencies,
    parentAssetHashes={**parent['inputs']['parentAssetHashes'],**parent['assetHashes']},protectedHashes=protected,
    sourceHashes={**parent['inputs']['sourceHashes'],staged_file.relative_to(ROOT).as_posix():sha(staged_file)},
    tools={p:sha(ROOT/p) for p in tools},timberBounds=timber_bounds,sourceTint=source_tint,recipes=recipes)
signature = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
# The same strict native first-pair fixture admits these atmosphere copies.
folder = '/Game/WorldRebuild/T1Redesign_Atmosphere_'+signature[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh_tools = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.get_default_object(unreal.StaticMeshEditorSubsystem)
ceilings = {}; packages = []; zones = []; palettes = {}
try:
    if not levels.new_level(folder+'/AssemblyWorkspace'): raise RuntimeError('Cannot create isolated ceiling workspace')
    for home_id,recipe in recipes.items():
        region = recipe['zone']
        if region not in palettes:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_Timber_'+region,folder+'/Materials',
                unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
            if not material: raise RuntimeError('Cannot create private timber palette')
            unreal.MaterialEditingLibrary.set_material_instance_parent(material,source_material)
            color = [a*b for a,b in zip(source_tint[:3],recipe['tint'])]+[source_tint[3]]
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(material,'Base_Color_Tint',unreal.LinearColor(*color))
            actual = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(material,'Base_Color_Tint')
            if not same_state([actual.r,actual.g,actual.b,actual.a],color): raise RuntimeError('Timber tint readback differs')
            if not unreal.EditorAssetLibrary.save_loaded_asset(material,False): raise RuntimeError('Cannot save private timber palette')
            palettes[region] = material
        instances = []
        for panel in recipe['panels']:
            pitch,yaw,roll = panel['rotation']
            actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*panel['location']),unreal.Rotator(pitch=pitch,yaw=yaw,roll=roll))
            actor.set_actor_scale3d(unreal.Vector(*panel['scale'])); actor.static_mesh_component.set_static_mesh(timber)
            actor.static_mesh_component.set_material(0,palettes[region]); instances.append(actor)
        settings = unreal.MeshMergingSettings()
        for name,value in dict(lod_selection_type=unreal.MeshLODSelectionType.ALL_LODS,merge_materials=False,
            merge_equivalent_materials=False,bake_vertex_data_to_mesh=True,generate_light_map_uv=False,
            pivot_type=unreal.MeshMergePivotType.WORLD_ORIGIN).items(): settings.set_editor_property(name,value)
        options = unreal.MergeStaticMeshActorsOptions(); options.base_package_name = folder+'/Ceilings/SM_'+home_id
        options.mesh_merging_settings = settings
        merged = mesh_tools.merge_static_mesh_actors(instances,options)
        mesh = merged.static_mesh_component.static_mesh if merged else None
        if not isinstance(mesh,unreal.StaticMesh): raise RuntimeError('Ceiling merge failed')
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        lod = unreal.EditorScriptingMeshReductionOptions(); lod.auto_compute_lod_screen_size = True
        lod.reduction_settings = [unreal.EditorScriptingMeshReductionSettings(percent_triangles=p,screen_size=s) for p,s in ((1,1),(.5,.5),(.2,.2))]
        mesh_tools.set_lods(mesh,lod)
        if not unreal.EditorAssetLibrary.save_loaded_asset(mesh,False): raise RuntimeError('Cannot save private ceiling')
        b = mesh.get_bounds()
        if abs(b.origin.z-b.box_extent.z-recipe['bottomZ'])>.01 or abs(b.origin.z+b.box_extent.z-recipe['topZ'])>.01:
            raise RuntimeError('Merged ceiling moved its surveyed height')
        materials = [s.material_interface.get_path_name() for s in mesh.static_materials]
        if materials != [palettes[region].get_path_name()]: raise RuntimeError('Ceiling changed its palette slots')
        ceilings[home_id] = dict(mesh=mesh.get_path_name(),sha256=sha(asset_file(mesh.get_path_name())),materials=materials,
            triangles=[mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())],recipe=recipe)
        for actor in instances+[merged]:
            if unreal.SystemLibrary.is_valid(actor): actors.destroy_actor(actor)
        unreal.log('WAR_T1_CEILING_ASSEMBLED='+home_id)
    for zone in parent['zones']:
        identity = zone['id']; source = json.loads((DIRECTORY/(identity+'.json')).read_text())
        if not levels.load_level(zone['map']): raise RuntimeError('Parent shell map unavailable')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        states = inventory(actors)
        if not same_state(states,zone['actorInventory']): raise RuntimeError('Parent shell inventory changed')
        effects = [a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarRegionalAtmosphere)]
        recipe = zone['atmosphere']
        if len(effects)!=1 or str(effects[0].zone_id)!=identity or effects[0].weather_material.get_path_name()!=recipe['material']:
            raise RuntimeError('Parent atmosphere binding changed')
        for name,key in [('village_centre','villageCentre'),('military_centres','militaryCentres'),('steam_sites','steamSites')]:
            value=effects[0].get_editor_property(name)
            actual=[value.x,value.y,value.z] if name=='village_centre' else [[v.x,v.y,v.z] for v in value]
            if not same_state(actual,recipe[key]): raise RuntimeError('Parent atmosphere sites changed')
        if not same_state(effects[0].audio_gain,recipe['audioGain']): raise RuntimeError('Parent audio setting changed')
        homes = copy.deepcopy(zone['homes'])
        for home in homes:
            label = home['id']+'_timber_ceiling'; definition = ceilings[home['id']]
            if label in states: raise RuntimeError('Preserve an existing ceiling actor')
            house = states[home['id']]
            states[label] = dict(kind='mesh',location=house['location'],rotation=house['rotation'],scale=house['scale'],
                tags=['WarT1TimberCeilingStudy',identity,home['id']],mesh=definition['mesh'],materials=definition['materials'],collision='BlockAll')
            home['ceiling'] = dict(label=label,**definition)
            fill=definition['recipe']['fill']; fill_label=home['id']+'_ceiling_fill'
            if fill_label in states: raise RuntimeError('Preserve an existing interior fill')
            existing_house=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==home['id'])
            location=existing_house.get_actor_transform().transform_location(unreal.Vector(*fill['position']))
            states[fill_label]=dict(kind='light',location=[location.x,location.y,location.z],rotation=[0,0,0],scale=[1,1,1],
                tags=['WarT1PrototypePractical','WarT1InteriorPractical','WarT1CeilingFill'],zone=identity,
                day=fill['dayLumens'],night=fill['nightLumens'],color=fill['color'],properties=dict(
                    attenuation_radius=fill['attenuationRadiusCm'],cast_shadows=fill['castShadows'],
                    source_radius=fill['sourceRadiusCm'],soft_source_radius=0,source_length=0,
                    temperature=6500,use_temperature=False,specular_scale=1))
            home['ceiling']['fillLabel']=fill_label
        destination = folder+'/'+identity
        if not levels.new_level(destination+'/Review'): raise RuntimeError('Cannot create fresh ceiling review map')
        anchor = actors.spawn_actor_from_class(unreal.WarZoneAnchor,unreal.Vector())
        anchor.set_editor_property('zone_id',identity); anchor.set_editor_property('zone_origin',unreal.Vector())
        anchor.set_editor_property('use_spatial_bounds',True); b=source['spatial']['bounds']
        anchor.set_editor_property('content_min',unreal.Vector2D(b['minZ']*100,b['minX']*100))
        anchor.set_editor_property('content_max',unreal.Vector2D(b['maxZ']*100,b['maxX']*100))
        anchor.set_editor_property('playable_outline',[unreal.Vector2D(p['z']*100,p['x']*100) for p in source['spatial']['playableOutline']])
        generated=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Generated',False)
        if not generated: raise RuntimeError('Cannot create ceiling generated layer')
        unreal.EditorLevelUtils.make_level_current(generated); clone(actors,states,{})
        effect=actors.spawn_actor_from_class(unreal.WarRegionalAtmosphere,unreal.Vector())
        effect.set_actor_label(identity+'_regional_atmosphere'); effect.set_editor_property('zone_id',identity)
        effect.set_editor_property('village_centre',unreal.Vector(*recipe['villageCentre']))
        for name,key in [('military_centres','militaryCentres'),('steam_sites','steamSites')]: effect.set_editor_property(name,[unreal.Vector(*p) for p in recipe[key]])
        effect.set_editor_property('weather_material',unreal.load_asset(recipe['material'])); effect.set_editor_property('audio_gain',recipe['audioGain'])
        actual = inventory(actors)
        if not same_state(actual,states):
            changed = [k for k in states if k not in actual or not same_state(actual[k],states[k])]
            raise RuntimeError('Ceiling clone changed actor bindings: '+', '.join(changed))
        if not levels.save_current_level(): raise RuntimeError('Cannot save ceiling generated layer')
        authored=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Authored',False)
        if not authored: raise RuntimeError('Cannot reserve empty owner layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level(): raise RuntimeError('Cannot save empty owner layer')
        levels.set_current_level_by_name('Review'); anchor.set_editor_property('content_levels',[destination+'/Generated',destination+'/Authored'])
        if not levels.save_current_level(): raise RuntimeError('Cannot save ceiling review map')
        packages.extend(destination+'/'+n for n in ('Review','Generated','Authored'))
        zones.append({**zone,'map':destination+'/Review','parentMap':zone['map'],'homes':homes,'actorInventory':states,
                      'surroundingsPreserved':True,'geometryPreserved':False})
finally:
    verify_protected(ROOT,protected)
    for package,digest in dependencies.items():
        if sha(asset_file(package))!=digest: raise RuntimeError('Ceiling authoring changed frozen kit assets')
result = dict(signature=signature,kind='atmosphere',study='timber-ceilings',inputs=inputs,zones=zones,ceilings=ceilings,
    packageHashes={p:sha(package_file(p)) for p in packages},
    assetHashes={p.relative_to(ROOT).as_posix():sha(p) for p in (CONTENT/folder.removeprefix('/Game/')).rglob('*.uasset')},
    parentCandidatesUnchanged=True,activeCampaignChanged=False,visualApproved=False,walkDriveAccepted=False,licensedDistributionApproved=False)
target = DIRECTORY/('ceilings-'+signature[:12]+'.json')
if target.exists(): raise RuntimeError('Preserve existing ceiling receipt')
target.write_text(json.dumps(result,indent=2)+'\n'); (DIRECTORY/'ceilings-latest.json').write_text(target.read_text())
unreal.log('WAR_T1_CEILINGS_BUILT='+signature[:12])
