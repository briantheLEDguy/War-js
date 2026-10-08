"""Raise enclosing ridges/basin walls in fresh population copies, protecting retained ground."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from t1_relief import deform_surface
from t1_population_native import population_actor,spawn_population
from t1_material_clone import inventory,clone
from t1_materials import protected_saved,verify_protected,sha,same_state
from world_build_assets import WorldAssets
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'; CONTENT=ROOT/'unreal/AegisWar/Content'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
parent=read(DIRECTORY/'population-latest.json'); review=read(DIRECTORY/'population-review.json')
walking=read(DIRECTORY/'population-traversal-headless-latest.json')
if (parent.get('study')!='retained-population' or review['signature']!=parent['signature'] or not review['capsuleClear']
    or not review['exactBindingsVerified'] or walking['signature']!=parent['signature'] or not walking['savedCandidatesUnchanged']):
    raise RuntimeError('Dramatic relief requires verified retained population/access/walking parents')
for file,digest in {**parent['inputs']['sourceHashes'],**parent['inputs']['tools'],**parent['inputs']['parentAssetHashes'],**parent['assetHashes']}.items():
    if sha(ROOT/file)!=digest: raise RuntimeError('Preserve changed parent inputs, binaries or assets')
for package,digest in {**parent['inputs']['parentPackages'],**parent['packageHashes']}.items():
    if sha(CONTENT/(package.removeprefix('/Game/')+'.umap'))!=digest: raise RuntimeError('Preserve changed parent package')
for package,digest in parent['inputs']['dependencyHashes'].items():
    if sha(CONTENT/(package.removeprefix('/Game/')+'.uasset'))!=digest: raise RuntimeError('Parent dependency changed')
verify_protected(ROOT,parent['inputs']['protectedHashes']); protected=protected_saved(ROOT)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
surfaces={}; boxes={}; reports={}
for zone in parent['zones']:
    if not levels.load_level(zone['map']): raise RuntimeError('Relief parent unavailable')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
    if not same_state(inventory(actors),zone['actorInventory']): raise RuntimeError('Parent static inventory changed')
    reserved=[]
    for actor in actors.get_all_level_actors():
        if isinstance(actor,(unreal.StaticMeshActor,unreal.WarCityNpc)) and actor.get_actor_label() not in (zone['id']+'_terrain',zone['id']+'_roads'):
            c=actor.get_component_by_class(unreal.SkeletalMeshComponent) if isinstance(actor,unreal.WarCityNpc) else actor.static_mesh_component
            centre,extent,_=unreal.SystemLibrary.get_component_bounds(c)
            reserved.append([(centre.y-extent.y)/100,(centre.y+extent.y)/100,(centre.x-extent.x)/100,(centre.x+extent.x)/100])
    boxes[zone['id']]=reserved
    source=read(DIRECTORY/(zone['id']+'.json')); data=read(DIRECTORY/(zone['id']+'_terrain.json'))
    surfaces[zone['id']],reports[zone['id']]=deform_surface(data,source,reserved,zone['population'])
tools=['scripts/unreal/build-t1-relief-studies.py','scripts/unreal/t1_relief.py','scripts/unreal/t1_population_native.py',
       'scripts/unreal/t1_material_clone.py','scripts/unreal/world_build_assets.py','unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll']
source_hashes={**parent['inputs']['sourceHashes'],**{(DIRECTORY/(z['id']+'_terrain.json')).relative_to(ROOT).as_posix():sha(DIRECTORY/(z['id']+'_terrain.json')) for z in parent['zones']}}
inputs=dict(parentPopulationSignature=parent['signature'],parentPlanSha256=parent['inputs']['parentPlanSha256'],
    parentPackages={**parent['inputs']['parentPackages'],**parent['packageHashes']},
    parentAssetHashes={**parent['inputs']['parentAssetHashes'],**parent['assetHashes']},dependencyHashes=parent['inputs']['dependencyHashes'],
    sourceHashes=source_hashes,tools={p:sha(ROOT/p) for p in tools},protectedHashes=protected,protectedSceneryBoxes=boxes,relief=reports)
signature=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
collection='T1Redesign_Atmosphere_'+signature[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f')
assets=WorldAssets(ROOT,collection); zones=[]; packages=[]
try:
    for zone in parent['zones']:
        identity=zone['id']; source=read(DIRECTORY/(identity+'.json')); states=copy.deepcopy(zone['actorInventory'])
        terrain=states[identity+'_terrain']; original_mesh=terrain['mesh']
        mesh=assets.mesh(identity+'_dramatic_terrain',surfaces[identity],unreal.load_asset(terrain['materials'][0]),True)
        terrain['mesh']=mesh.get_path_name()
        destination=assets.folder+'/'+identity
        if not levels.new_level(destination+'/Review'): raise RuntimeError('Cannot create relief review')
        anchor=actors.spawn_actor_from_class(unreal.WarZoneAnchor,unreal.Vector())
        anchor.set_editor_property('zone_id',identity); anchor.set_editor_property('zone_origin',unreal.Vector())
        anchor.set_editor_property('use_spatial_bounds',True); b=source['spatial']['bounds']
        anchor.set_editor_property('content_min',unreal.Vector2D(b['minZ']*100,b['minX']*100))
        anchor.set_editor_property('content_max',unreal.Vector2D(b['maxZ']*100,b['maxX']*100))
        anchor.set_editor_property('playable_outline',[unreal.Vector2D(p['z']*100,p['x']*100) for p in source['spatial']['playableOutline']])
        generated=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Generated',False)
        if not generated: raise RuntimeError('Cannot create relief generated layer')
        unreal.EditorLevelUtils.make_level_current(generated)
        ids={r['id'] for r in zone['population']}; clone(actors,{k:v for k,v in states.items() if k not in ids},{})
        for original in zone['population']:
            row=copy.deepcopy(original); row['point']=row['savedState']['location']
            actor=spawn_population(actors,row)
            if not same_state(population_actor(actor),row['savedState']): raise RuntimeError('Relief clone changed retained population')
        recipe=zone['atmosphere']; effect=actors.spawn_actor_from_class(unreal.WarRegionalAtmosphere,unreal.Vector())
        effect.set_actor_label(identity+'_regional_atmosphere'); effect.set_editor_property('zone_id',identity)
        effect.set_editor_property('village_centre',unreal.Vector(*recipe['villageCentre']))
        for name,key in [('military_centres','militaryCentres'),('steam_sites','steamSites')]: effect.set_editor_property(name,[unreal.Vector(*p) for p in recipe[key]])
        effect.set_editor_property('weather_material',unreal.load_asset(recipe['material'])); effect.set_editor_property('audio_gain',recipe['audioGain'])
        if not same_state(inventory(actors),states): raise RuntimeError('Relief clone changed non-terrain bindings')
        if not levels.save_current_level(): raise RuntimeError('Cannot save relief generated layer')
        authored=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Authored',False)
        if not authored: raise RuntimeError('Cannot reserve relief owner layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level(): raise RuntimeError('Cannot save empty relief owner layer')
        levels.set_current_level_by_name('Review'); anchor.set_editor_property('content_levels',[destination+'/Generated',destination+'/Authored'])
        if not levels.save_current_level(): raise RuntimeError('Cannot save relief review')
        packages.extend(destination+'/'+n for n in ('Review','Generated','Authored'))
        zones.append({**zone,'map':destination+'/Review','parentMap':zone['map'],'actorInventory':states,
            'relief':reports[identity],'parentTerrainMesh':original_mesh,'terrainTriangles':mesh.get_num_triangles(0)})
        unreal.log('WAR_T1_RELIEF_BUILT_ZONE='+identity)
finally: verify_protected(ROOT,protected)
result=dict(signature=signature,kind='atmosphere',study='dramatic-relief',inputs=inputs,zones=zones,
    packageHashes={p:sha(CONTENT/(p.removeprefix('/Game/')+'.umap')) for p in packages},
    assetHashes={p.relative_to(ROOT).as_posix():sha(p) for p in (CONTENT/'WorldRebuild'/collection).rglob('*.uasset')},
    activeCampaignChanged=False,parentCandidatesUnchanged=True,sourceCatalogsUnchanged=True,
    visualApproved=False,offRouteTraversalAccepted=False,walkDriveAccepted=False,nodeGeometrySynchronized=False,gameplayAccepted=False)
target=DIRECTORY/('relief-'+signature[:12]+'.json')
if target.exists(): raise RuntimeError('Preserve existing relief receipt')
target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); (DIRECTORY/'relief-latest.json').write_text(target.read_text(encoding='utf-8'),encoding='utf-8')
unreal.log('WAR_T1_RELIEF_BUILT='+signature[:12])
