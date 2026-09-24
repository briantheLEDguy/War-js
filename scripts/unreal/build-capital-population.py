"""Build only the owned population layer; never save the owner's persistent city."""
import hashlib
import json
from pathlib import Path
import sys
import unreal
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capital_population import ROOT, POPULATION_MAP, OFFICER, official_map, records
from capital_geography import height
from native_animation_bindings import installed

assets = unreal.EditorAssetLibrary
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
output = ROOT/'artifacts/unreal/population'
output.mkdir(parents=True, exist_ok=True)
city_file = ROOT/'unreal/AegisWar/Content'/ (official_map().removeprefix('/Game/')+'.umap')
city_hash = hashlib.sha256(city_file.read_bytes()).hexdigest()
receipt_file = output/'population-build.json'
package = ROOT/'unreal/AegisWar/Content'/(POPULATION_MAP.removeprefix('/Game/')+'.umap')
if not level.load_level(official_map()): raise RuntimeError('Official city is unavailable for grounding')
city_world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if package.exists() and not unreal.GameplayStatics.get_streaming_level(city_world,POPULATION_MAP):
    unreal.EditorLevelUtils.add_level_to_world(city_world,POPULATION_MAP,unreal.LevelStreamingAlwaysLoaded)
unreal.GameplayStatics.flush_level_streaming(city_world)
ground_positions={}
for row in records():
    if row['profile']=='existing': continue
    x,y=row['z']*100,row['x']*100
    floor=4210 if row['district']=='crownwatch' else height(row['x'],row['z'])*100
    hit=unreal.SystemLibrary.line_trace_single(city_world,unreal.Vector(x,y,floor+100),unreal.Vector(x,y,floor-250),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE)
    if not hit or hit.to_tuple()[7].z<.65: raise RuntimeError('No walkable ground for '+row['id'])
    ground_positions[row['id']]=hit.to_tuple()[5].z
if package.exists():
    prior = json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
    if hashlib.sha256(package.read_bytes()).hexdigest() != prior.get('sha256'):
        raise RuntimeError('Population layer was edited; preserve owner changes before regenerating')
    if not level.load_level(POPULATION_MAP): raise RuntimeError('Population map failed to load')
    for actor in actors.get_all_level_actors():
        if 'WarCityPopulation' in [str(t) for t in actor.tags]: actors.destroy_actor(actor)
else:
    unreal.EditorLoadingAndSavingUtils.new_blank_map(False)

loaded = {}
for row in records():
    profile = row['profile']
    if profile in ('existing',) or profile in loaded: continue
    if profile == OFFICER:
        visual = unreal.load_asset('/Game/MigrationProof/Visual_'+profile)
        mesh, idle = visual.skeletal_mesh, visual.idle_animation
    else:
        receipt = installed(profile)
        mesh = unreal.load_asset(receipt['meshes'][0]['path'])
        idle = unreal.load_asset(next(a['path'] for a in receipt['animations'] if a['sourceClipName']=='idle'))
    if not isinstance(mesh, unreal.SkeletalMesh) or not isinstance(idle, unreal.AnimSequence):
        raise RuntimeError('Required complex character/idle is missing: '+profile)
    loaded[profile] = (mesh,idle)

placed = []
for row in records():
    if row['profile']=='existing': continue
    x,y = row['z']*100,row['x']*100
    floor = ground_positions[row['id']]
    actor_class = unreal.WarCityNpc if hasattr(unreal,'WarCityNpc') else unreal.SkeletalMeshActor
    actor = actors.spawn_actor_from_class(actor_class, unreal.Vector(x,y,floor), unreal.Rotator(yaw=row['yaw']-90))
    if hasattr(unreal,'WarCityNpc'):
        actor.set_editor_property('npc_id',row['id'])
        actor.set_editor_property('display_name',row['name'])
        actor.set_editor_property('city_role',row['role'])
        actor.set_editor_property('character_profile',row['profile'])
    actor.set_actor_label(row['name']+' - '+row['role'])
    actor.set_folder_path('Population/'+row['district'])
    actor.tags=['WarCityPopulation','WarNpcId_'+row['id'],'WarNpcRole_'+row['role']]
    component=actor.skeletal_mesh_component
    mesh,idle=loaded[row['profile']]
    component.set_skeletal_mesh_asset(mesh)
    component.override_animation_data(idle,True,True,0,1)
    component.set_collision_profile_name('NoCollision')
    unreal.WarImportLibrary.prepare_preview_frame(component)
    origin,extent,_=unreal.SystemLibrary.get_component_bounds(component)
    if not 100 < extent.z*2 < 240: raise RuntimeError('Unexpected character height '+row['id']+': '+str(extent))
    offset=floor-(origin.z-extent.z)
    actor.set_actor_location(unreal.Vector(x,y,floor+offset),False,True)
    placed.append({**row,'position':[x,y,floor+offset],'feetZ':floor,'mesh':mesh.get_path_name(),'idle':idle.get_path_name()})

# Small service landmarks use the already imported purchased kit, never proxy geometry.
for kind, district, x, z, yaw in [
    ('SM_Crate','gateward',14,-115,0),('SM_Barrel','gateward',16,-114,0),
    ('SM_Crate','cinderbank',-67,-43,30),('SM_Barrel','cinderbank',-68,-43,0),
    ('SM_Crate','lantern_quays',110,-37,0),('SM_Crate','lantern_quays',111,-37,15),
    ('SM_Barrel','lantern_quays',110,-35,0),('SM_Bench','bellfound',-34,56,90)]:
    mesh=unreal.load_asset('/Game/LicensedKits/Crownward/'+kind)
    if not isinstance(mesh,unreal.StaticMesh): raise RuntimeError('Required district furnishing missing: '+kind)
    floor=height(x,z)*100
    prop=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(z*100,x*100,floor),unreal.Rotator(yaw=yaw))
    prop.set_actor_label(district+' service '+kind)
    prop.set_folder_path('Population/'+district+'/Furnishings')
    prop.tags=['WarCityPopulation','WarPopulationFurnishing']
    prop.static_mesh_component.set_static_mesh(mesh)
    prop.static_mesh_component.set_collision_profile_name('BlockAll')
    origin,extent=prop.get_actor_bounds(False)
    prop.set_actor_location(unreal.Vector(z*100,x*100,floor-(origin.z-extent.z-floor)),False,True)

world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not unreal.EditorLoadingAndSavingUtils.save_map(world, POPULATION_MAP): raise RuntimeError('Could not save population layer')
if hashlib.sha256(city_file.read_bytes()).hexdigest()!=city_hash: raise RuntimeError('City changed concurrently; do not overwrite it')
receipt_file.write_text(json.dumps({'map':POPULATION_MAP,'city':official_map(),'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
    'cityUnchanged':True,'existingMara':1,'newActors':len(placed),'actors':placed,'visualVerified':False,
    'nativeServiceActors':hasattr(unreal,'WarCityNpc'),'servicesRuntimeVerified':False},indent=2))
unreal.log('WAR_POPULATION_BUILT='+str(len(placed)))
