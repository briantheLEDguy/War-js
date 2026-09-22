"""Assemble the campaign as a sublevel, then attach explicitly with attach-world.py."""
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_population import official_map, POPULATION_MAP
from world_build_assets import WorldAssets, ground

directory = ROOT/'artifacts/unreal/world-portals'
plan = json.loads((directory/'plan.json').read_text())
static = json.loads((directory/'static/plan.json').read_text())
if plan['schemaVersion'] != 2 or not plan['developmentOnly']: raise RuntimeError('Invalid world plan')
def fingerprint(file): return hashlib.sha256(file.read_bytes()).hexdigest()
if static['planSha256'] != fingerprint(directory/'plan.json'): raise RuntimeError('Stale static plan')
if static['registrySha256'] != fingerprint(ROOT/'public/assets/models/asset-index.json'): raise RuntimeError('Source registry changed')
for zone,digest in plan['sourceHashes'].items():
    if fingerprint(ROOT/'public/assets/maps'/(zone+'.json')) != digest: raise RuntimeError('Source map changed: '+zone)
for key,digest in plan['terrainHashes'].items():
    if fingerprint(directory/(key+'.json')) != digest: raise RuntimeError('Terrain input changed: '+key)
if not hasattr(unreal,'WarZoneAnchor'): raise RuntimeError('Build the native zone classes first')

stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
collection = 'Campaign_'+stamp
target = '/Game/WorldRebuild/'+collection+'/CampaignTravel'
assets = WorldAssets(ROOT,collection)
source_map = official_map()
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not level.new_level(target): raise RuntimeError('Could not create campaign layer')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
capital = unreal.EditorLevelUtils.add_level_to_world(world,source_map,unreal.LevelStreamingAlwaysLoaded)
if not capital: raise RuntimeError('Capital unavailable')
unreal.GameplayStatics.flush_level_streaming(world)
capital_starts = [a.get_actor_location() for a in actors.get_all_level_actors() if isinstance(a,unreal.PlayerStart)]
if not capital_starts: raise RuntimeError('Existing capital arrival missing')
if not level.set_current_level_by_name('CampaignTravel'): raise RuntimeError('Could not select campaign layer')
zones = {zone['id']:zone for zone in plan['zones']}
def texture(name):
    path = ROOT/'public/assets/textures/sunmeadow_terrain'/name
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':fingerprint(path)}
road_material = assets.material('Road',{'color':[0.55,0.47,0.34,1],'roughness':0.96,'textures':{
    'color':texture('8cbd5ce392c2233e6ded.png'),'normal':texture('8db1dbe8154305c7df4c.png')},'alphaMode':'OPAQUE'})
def place(mesh,label,position,collision=True,rotation=0,scale=None,tags=None):
    actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*position),unreal.Rotator(yaw=rotation))
    actor.set_actor_label(label)
    actor.tags=['WarCampaignWorld']+(tags or [])
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    if scale: actor.set_actor_scale3d(unreal.Vector(*scale))
    return actor

for zone in plan['zones']:
    if zone['status'] != 'source-terrain': continue
    hex_color=zone['palette'][0].lstrip('#')
    rgb=[int(hex_color[i:i+2],16)/255 for i in (0,2,4)]
    material=assets.material(zone['id'],{'color':[min(1,c*1.5) for c in rgb]+[1], 'roughness':0.96,
        'textures':{'color':texture('e5820d107e9ae59f365f.png'),'normal':texture('b77e82f05403e58f2d83.png')},'alphaMode':'OPAQUE'})
    for suffix,mat,collision in [('',material,True),('_roads',road_material,False)]:
        key=zone['id']+suffix
        if key not in plan['terrainHashes']: continue
        data=json.loads((directory/(key+'.json')).read_text())
        mesh=assets.mesh(key,data,mat,collision)
        place(mesh,key,zone['origin'],collision)
unreal.WarImportLibrary.prepare_preview_frame(None)

# Resolve all terrain-relative positions before placing scenery so roofs/trees never become the terrain sampler.
positions={}
gameplay_positions={}
sources={zone['id']:json.loads((ROOT/'public/assets/maps'/(zone['id']+'.json')).read_text()) for zone in plan['zones']}
for row in static['placements']:
    p=row['source']; origin=zones[row['zone']]['origin']
    point=unreal.Vector(origin[0]+p['z']*100,origin[1]+p['x']*100,origin[2]+p.get('y',0)*100)
    if p.get('heightMode') != 'absolute' and row['zone'] != 'riftspire_capital':
        point.z=ground(world,point).z+p.get('y',0)*100
    positions[row['zone']+':'+row['id']]=[point.x,point.y,point.z]
for zone,source in sources.items():
    if zone in ('aegis_capital','riftspire_capital'): continue
    origin=zones[zone]['origin']
    for row in source.get('npcs',[])+source.get('craftingStations',[]):
        point=unreal.Vector(origin[0]+row['z']*100,origin[1]+row['x']*100,origin[2]+row.get('y',0)*100)
        if row.get('heightMode') != 'absolute': point.z=ground(world,point).z+row.get('y',0)*100
        gameplay_positions[zone+':'+row['id']]=point

meshes={}
for model,definition in static['models'].items():
    if 'error' in definition: continue
    file=directory/'static'/definition['file']
    if fingerprint(file) != definition['sha256']: raise RuntimeError('Static input changed: '+model)
    data=json.loads(file.read_text())
    if fingerprint(ROOT/'public/assets/models'/model) != data['sourceSha256']: raise RuntimeError('Model source changed: '+model)
    surfaces=[]
    for part in data['parts']:
        key=Path(model).stem+'_'+str(part['index'])
        material_key=hashlib.sha256(json.dumps(part['material'],sort_keys=True).encode()).hexdigest()[:20]
        mat=assets.material(material_key,part['material'])
        surfaces.append(assets.mesh(key,part,mat,True))
    meshes[model]=surfaces
    unreal.log('WAR_WORLD_MODEL='+model)

placed=[]
for row in static['placements']:
    p=row['source']; value=p.get('scale',1)
    scale=[value,value,value] if isinstance(value,(int,float)) else [value.get('z',1),value.get('x',1),value.get('y',1)]
    collision=bool(p.get('colliders') or p.get('walkableSurfaces') or row['zone']=='riftspire_capital')
    for index,mesh in enumerate(meshes[row['model']]):
        place(mesh,row['zone']+' '+row['id']+' '+str(index),positions[row['zone']+':'+row['id']],collision,
            p.get('rotY',0)*180/math.pi,scale,['WarWorldObject_'+row['zone']+'_'+row['id']+'_'+str(index),'WarCampaignScenery'])
    placed.append({'zone':row['zone'],'id':row['id'],'parts':len(meshes[row['model']])})
unreal.WarImportLibrary.prepare_preview_frame(None)

gameplay, pending_gameplay = [], []
admitted={row['profileKey'] for row in json.loads((ROOT/'unreal/AegisWar/Content/Migration/visual-imports.json').read_text())['entries']}
station_models={'salvage':'frontier_siege_repair_bench_lod0.glb','apothecary':'frontier_field_apothecary_lod0.glb'}
for zone,source in sources.items():
    if zone in ('aegis_capital','riftspire_capital'): continue
    for row in source.get('npcs',[]):
        if row['role'] != 'questgiver':
            pending_gameplay.append({'zone':zone,'id':row['id'],'reason':'native-population-actor-pending'});continue
        profile=row.get('characterProfileKey','')
        visual_path='/Game/MigrationProof/Visual_'+profile
        visual=unreal.load_asset(visual_path) if profile in admitted and unreal.EditorAssetLibrary.does_asset_exist(visual_path) else None
        if not visual or not visual.skeletal_mesh:
            pending_gameplay.append({'zone':zone,'id':row['id'],'reason':'native-character-visual-pending'});continue
        npc=actors.spawn_actor_from_class(unreal.WarQuestNpc,gameplay_positions[zone+':'+row['id']],unreal.Rotator(yaw=row.get('rotY',0)*180/math.pi))
        npc.set_actor_label(row['name']);npc.tags=['WarCampaignWorld']
        npc.set_editor_property('zone_id',zone);npc.set_editor_property('npc_id',row['id']);npc.set_editor_property('visual',visual)
        component=npc.get_editor_property('mesh');component.set_skeletal_mesh_asset(visual.skeletal_mesh)
        component.set_relative_transform(visual.mesh_transform,False,True)
        gameplay.append({'zone':zone,'id':row['id'],'kind':'npc','profile':profile})
    for row in source.get('craftingStations',[]):
        model=station_models.get(row['kind'])
        if model not in meshes:
            pending_gameplay.append({'zone':zone,'id':row['id'],'reason':'station-visual-pending'});continue
        point=gameplay_positions[zone+':'+row['id']]
        for index,mesh in enumerate(meshes[model]):
            station=actors.spawn_actor_from_class(unreal.WarCraftingStation if index==0 else unreal.StaticMeshActor,point)
            station.set_actor_label(row['label']+' '+str(index));station.tags=['WarCampaignWorld']
            station.static_mesh_component.set_static_mesh(mesh)
            station.static_mesh_component.set_collision_profile_name('BlockAll')
            if index==0:
                station.set_editor_property('station_kind',row['kind']);station.set_editor_property('interaction_radius',row['radius']*100)
        gameplay.append({'zone':zone,'id':row['id'],'kind':'crafting'})

anchors=[]
for zone in plan['zones']:
    point=capital_starts[0] if zone['id']=='aegis_capital' else ground(world,unreal.Vector(*zone['spawn']))+unreal.Vector(0,0,101)
    anchor=actors.spawn_actor_from_class(unreal.WarZoneAnchor,point)
    anchor.set_actor_label(zone['name']+' arrival')
    for key,value in {'zone_id':zone['id'],'zone_name':zone['name'],'zone_origin':unreal.Vector(*zone['origin']),'half_size':zone['size']*50}.items():
        anchor.set_editor_property(key,value)
    anchors.append(zone['id'])
for route in plan['routes']:
    point=ground(world,unreal.Vector(*route['position']))+unreal.Vector(0,0,100)
    arrival=ground(world,unreal.Vector(*route['arrival']),5000)
    portal=actors.spawn_actor_from_class(unreal.WarZonePortal,point)
    portal.set_actor_label(route['id'])
    for key,value in {'route_id':route['id'],'destination_route_id':route['reverseId'],'destination_label':route['label'],
        'radius':route['radius'],'destination_built':True,'arrival_location':arrival}.items(): portal.set_editor_property(key,value)
    portal.set_actor_transform(portal.get_actor_transform(),False,True)

# Save only the campaign layer. The main city must not become its own streaming descendant.
if not unreal.EditorLevelUtils.remove_level_from_world(capital.get_loaded_level()): raise RuntimeError('Could not detach source city from layer')
if not level.set_current_level_by_name('CampaignTravel') or not level.save_current_level(): raise RuntimeError('Campaign layer save failed')
receipt={'schemaVersion':2,'layer':target,'map':source_map,'planSha256':fingerprint(directory/'plan.json'),
    'staticPlanSha256':fingerprint(directory/'static/plan.json'),'zones':anchors,'portals':[r['id'] for r in plan['routes']],
    'scenery':placed,'pendingScenery':static['pending'],'gameplay':gameplay,'pendingGameplay':pending_gameplay,
    'attached':False,'runtimeTraversalVerified':False,'visualApproved':False}
(directory/'candidate.json').write_text(json.dumps(receipt,indent=2)+'\n')
unreal.log('WAR_CAMPAIGN_LAYER_BUILT='+target)
