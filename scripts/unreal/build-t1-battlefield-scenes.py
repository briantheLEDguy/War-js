"""Small regional camera-review cells in fresh native copies, with reviewed source-channel adaptations."""
import copy
import datetime
import hashlib
import json
import math
import struct
from pathlib import Path
import sys
import unreal
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(Path(__file__).parent))
from t1_battlefield import Surface
from t1_materials import protected_saved,verify_protected,sha,same_state,terrain_recipe
from t1_material_clone import inventory,clone
from t1_material_assets import regional_material
from t1_population_native import spawn_population,population_actor,GroundReview
from t1_surface_variation import surface_variation
from t1_habitat_surface import habitat_recipe
from t1_rock_surface import rock_surface
from t1_stone_material import stone_material
from t1_landscape_ecology import admitted_cover,cover_layout,pocket_water
from t1_ecology_clusters import clustered_cover
from t1_nature_canopy_native import nature_sources,adapt_nature_canopies
from t1_woodland_clusters_native import add_woodland_canopies
from t1_ecology_native import ground_cover,water_material,cover_inventory
from t1_water_surface import water_surface
from t1_understorey_native import spawn_understorey
from t1_focal_planting_native import spawn_focal_plants
from t1_rock_clusters_native import adapt_rock_clusters,verify_rock_surfaces
from t1_rock_clusters import core_rock_parents
from t1_forest_floor_native import forest_floor_sources,forest_floor_material
from t1_pocket_dressing import pocket_dressing
from t1_bedded_outcrops import bedded_outcrops,outcrop_footing
from t1_placement_axes import source_scale_to_native
from t1_rock_shelters import rock_shelter
from t1_landscape_walks import landscape_walks
from world_build_assets import WorldAssets

BASE=ROOT/'artifacts/unreal/t1-redesign'; CONTENT=ROOT/'unreal/AegisWar/Content'; read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
parent=read(BASE/'battlefield-latest.json'); recipe=read(BASE/'battlefield-scenes-source-latest.json')
if recipe['parent']!=parent['signature']: raise RuntimeError('Scene cells require their exact battlefield parent')
files={**parent['inputs']['sourceHashes'],**parent['inputs']['tools'],**parent['assetHashes'],**recipe['inputs']}
packages={**parent['inputs']['parentPackages'],**parent['packageHashes']}
def verify_sources():
    for p,h in files.items():
        if sha(ROOT/p)!=h: raise RuntimeError('Changed scene source: '+p)
    for p,h in packages.items():
        if sha(CONTENT/(p.removeprefix('/Game/')+'.umap'))!=h: raise RuntimeError('Preserve changed parent scene: '+p)
verify_sources(); protected=protected_saved(ROOT)
recipes={z['id']:terrain_recipe(ROOT,z['id']) for z in parent['zones']}
for identity,r in recipes.items():
    r['layers']['terrain']['tint']=[.62,.98,.72,1] if identity=='sunmeadow_march' else [.8,1.04,.87,1]
    r['layers']['terrain']['rockColor']=[.3,.29,.26] if identity=='sunmeadow_march' else [.13,.135,.14]
    r['layers']['terrain']['macroMinimum']=.75
    r['layers']['terrain']['slopeNormalRange']=[.6,.86] if identity=='sunmeadow_march' else [.64,.9]
    for layer in r['layers'].values():
        layer['surfaceVariation']=surface_variation()
        if identity=='cinderfen_outskirts':layer['surfaceVariation']['channelRange']=[.008,.075]
    r['layers']['terrain']['habitat']=habitat_recipe(identity)
    r['layers']['terrain']['rockLayer']=rock_surface(ROOT,identity)
    if identity=='cinderfen_outskirts': r['layers']['terrain']['rockLayer']['tint']=[.48,.56,.64]
    r['waterSurface']=dict(**water_surface(identity),phaseChannel=r['layers']['terrain']['color'])
    r['layers']['terrain']['shorelines']=[dict(x=p['x'],z=p['z'],waterY=p['waterY'],radius=p['radius']+60) for p in next(z for z in parent['zones'] if z['id']==identity)['landscapePockets'] if p['cosmeticWater']]
    r['layers']['terrain']['substrate']=dict(color=r['layers']['roads']['color'],normal=r['layers']['roads']['normal'],
        tint=[.5,.65,.5] if identity=='sunmeadow_march' else [.68,.6,.48],tileMetres=2.8,patchMetres=43 if identity=='sunmeadow_march' else 37,
        patchStrength=.34,slopeStrength=.24,maskRange=[.025,.18] if identity=='sunmeadow_march' else [.01,.09])
for r in recipes.values():
    rock=r['layers']['terrain']['rockLayer']; files.update(rock['reviewInputs'])
    for channel in ('color','normal'): files[rock[channel]['path']]=rock[channel]['sha256']
cover_sources={}
for z in parent['zones']:
    data,cover_inputs=admitted_cover(ROOT,z['id']); cover_sources[z['id']]=data; files.update(cover_inputs)
canopies,canopy_inputs=nature_sources(ROOT);files.update(canopy_inputs)
forest_textures,forest_inputs=forest_floor_sources(ROOT);files.update(forest_inputs)
verify_sources()

tools=['scripts/unreal/build-t1-battlefield-scenes.py','scripts/unreal/t1_material_assets.py','scripts/unreal/t1_surface_variation.py','scripts/unreal/t1_habitat_surface.py','scripts/unreal/t1_materials.py',
       'scripts/unreal/t1_landscape_ecology.py','scripts/unreal/t1_ecology_clusters.py','scripts/unreal/t1_canopy.py','scripts/unreal/t1_canopy_native.py','scripts/unreal/t1_nature_kit.py','scripts/unreal/t1_nature_canopy.py','scripts/unreal/t1_nature_canopy_native.py','scripts/unreal/t1_woodland_clusters.py','scripts/unreal/t1_woodland_clusters_native.py','scripts/unreal/t1_rock_clusters.py','scripts/unreal/t1_rock_contact.py','scripts/unreal/t1_rock_clusters_native.py','scripts/unreal/t1_focal_planting.py','scripts/unreal/t1_focal_planting_native.py','scripts/unreal/t1_forest_floor.py','scripts/unreal/t1_forest_floor_native.py','scripts/unreal/t1_understorey.py','scripts/unreal/t1_understorey_native.py','scripts/unreal/t1_foliage_recipe.py','scripts/unreal/t1_foliage_native.py','scripts/unreal/t1_water_surface.py','scripts/unreal/t1_pocket_dressing.py','scripts/unreal/t1_bedded_outcrops.py','scripts/unreal/t1_placement_axes.py','scripts/unreal/t1_rock_shelters.py','scripts/unreal/t1_landscape_walks.py','scripts/unreal/t1_ecology_native.py','scripts/unreal/world_static.py','scripts/unreal/world_build_assets.py',
       'scripts/unreal/t1_rock_surface.py','scripts/unreal/t1_stone_material.py','scripts/unreal/t1_strata_surface.py','scripts/unreal/t1_geology_surface.py','scripts/unreal/t1_battlefield.py','scripts/unreal/t1_material_clone.py','scripts/unreal/t1_population_native.py',
       'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll']
inputs=dict(createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceSignature=recipe['signature'],
    sourceHashes=files,parentPackages=packages,tools={p:sha(ROOT/p) for p in tools},protectedHashes=protected,
    dependencyHashes=parent['inputs']['dependencyHashes'],recipes=recipes)
signature=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
assets=WorldAssets(ROOT,'T1Redesign_Atmosphere_'+signature[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f'))
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
saved=[]; zones=[]
try:
    for original in parent['zones']:
        identity=original['id']; source=read(ROOT/original['sourceDirectory']/(identity+'.json'))
        surface=Surface(source,read(ROOT/original['sourceDirectory']/(identity+'_terrain.json')))
        if not levels.load_level(original['map']): raise RuntimeError('Cannot load battlefield scene parent')
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        if not same_state(inventory(actors),original['actorInventory']): raise RuntimeError('Scene parent inventory changed')
        states=copy.deepcopy(original['actorInventory']); materials={}
        for role,r in recipes[identity]['layers'].items():
            material,expressions=regional_material(assets,identity+'_'+role,r)
            states[identity+'_'+role]['materials']=[material.get_path_name()]
            materials[role]=dict(asset=material.get_path_name(),expressions=expressions,sourceChannelsVerified=True,appearanceApproved=False)
        cells=next(z['scenes'] for z in recipe['zones'] if z['id']==identity)
        occupied=[p for c in cells for p in c['placements']]
        shelter_source=original['actorInventory'][identity+('_barrow_ridge_8' if identity=='sunmeadow_march' else '_basalt_shelf_1')]['mesh']
        committed=json.loads(unreal.WarImportLibrary.describe_static_mesh_source_data(unreal.load_asset(shelter_source),0))
        if not committed.get('valid'):raise RuntimeError('Shelter lacks admitted committed source geometry')
        positions=committed['data']['positions'];bounds=[[fn(p[i] for p in positions) for i in range(3)] for fn in (min,max)]
        shelter=rock_shelter(source,surface.height_cm,original['landscapePockets'],occupied,bounds)
        dressing=pocket_dressing(source,surface.height_cm,original['landscapePockets'],[*occupied,*shelter['placements']])
        bedding=bedded_outcrops(source,surface.height_cm,[*occupied,*shelter['placements'],*dressing])
        all_cells=[*cells,dict(placements=shelter['placements']),dict(placements=dressing),dict(placements=bedding)]
        for cell in all_cells:
            for p in cell['placements']:
                state=copy.deepcopy(original['actorInventory'][p['sourceLabel']])
                if state['kind']!='mesh': raise RuntimeError('Scene socket requires its admitted static source')
                # Python's Rotator properties are float32; freeze that admitted precision before cloning.
                yaw=struct.unpack('<f',struct.pack('<f',(p['yawDegrees']+180)%360-180))[0]
                f32=lambda value: struct.unpack('<f',struct.pack('<f',value))[0]
                state['scale']=source_scale_to_native(p['scaleAxes']); state['rotation']=[f32(p['tiltDegrees'][0]),yaw,f32(p['tiltDegrees'][1])]
                h=surface.height_cm(p['x'],p['z'])
                if p['grounding']=='embed':
                    # Bury broad rock feet below the lowest surrounding ground instead of levelling the hillside.
                    radius=math.hypot(p['width'],p['depth'])/2
                    h=(outcrop_footing(surface.height_cm,{**p,'yawDegrees':yaw}) if p.get('embedding')=='orientedFootprint' else
                        min(surface.height_cm(p['x']+radius*x/3,p['z']+radius*z/3) for x in range(-3,4) for z in range(-3,4)) - 20)
                state['location']=p.get('authoredLocationCm',[p['z']*100,p['x']*100,h]); state['tags']+=['WarT1BattlefieldSceneCell']
                if p['id'] in states: raise RuntimeError('Duplicate scene actor identity')
                states[p['id']]=state
        if identity=='sunmeadow_march':
            states,materials['canopy']=adapt_nature_canopies(assets,states,canopies)
        rock=recipes[identity]['layers']['terrain']['rockLayer']
        stone=stone_material(assets,identity,rock)
        admitted_mesh=original['actorInventory'][identity+('_barrow_ridge_8' if identity=='sunmeadow_march' else '_basalt_shelf_1')]['mesh']
        for state in states.values():
            if state['kind']=='mesh' and state['mesh']==admitted_mesh:state['materials']=[stone.get_path_name()]
        materials['regionalStone']=dict(asset=stone.get_path_name(),sourceColorChannelVerified=True,sourceGeometryAndCollisionPreserved=True,appearanceApproved=False)
        rock_parents=[p for cell in [*cells,dict(placements=dressing),dict(placements=bedding)] for p in cell['placements'] if p['sourceLabel'].endswith(('_barrow_ridge_8','_basalt_shelf_1'))]
        core_bounds=unreal.load_asset(admitted_mesh).get_bounds()
        core_parents=core_rock_parents(identity,states,admitted_mesh,[core_bounds.origin.x,core_bounds.origin.y,core_bounds.origin.z],[core_bounds.box_extent.x,core_bounds.box_extent.y,core_bounds.box_extent.z])
        states,rock_clusters=adapt_rock_clusters(assets,identity,states,[*rock_parents,*core_parents['placements']],canopies,surface.height_cm)
        rock_clusters['coreParentIds']=[p['id'] for p in core_parents['placements']]
        rock_clusters['unsupportedCoreParentIds']=core_parents['retainedIds']
        if identity=='sunmeadow_march':
            states,materials['woodland']=add_woodland_canopies(assets,source,states,canopies,surface.height_cm)
            floor,materials['forestFloor']=forest_floor_material(assets,unreal.load_asset(states[identity+'_terrain']['materials'][0]),source,states,forest_textures,BASE)
            states[identity+'_terrain']['materials']=[floor.get_path_name()]
        water_surfaces=[]
        wet=[p for p in original['landscapePockets'] if p['cosmeticWater']]
        if wet:
            material=water_material(assets,identity,recipes[identity]['waterSurface']['phaseChannel'])
            for pocket in wet:
                mesh=assets.mesh(pocket['id']+'_water',pocket_water(pocket,surface.height_cm),material,False)
                states[pocket['id']+'_water']=dict(kind='mesh',location=[0,0,0],rotation=[0,0,0],scale=[1,1,1],tags=['WarT1CosmeticShallowWater'],
                    mesh=mesh.get_path_name(),materials=[material.get_path_name()],collision='NoCollision')
                water_surfaces.append(pocket['id'])
        destination=assets.folder+'/'+identity
        if not levels.new_level(destination+'/Review'): raise RuntimeError('Cannot create fresh scene review')
        anchor=actors.spawn_actor_from_class(unreal.WarZoneAnchor,unreal.Vector(*original['arrivalCm']))
        anchor.set_editor_property('zone_id',identity); anchor.set_editor_property('zone_origin',unreal.Vector())
        anchor.set_editor_property('use_spatial_bounds',True); b=source['spatial']['bounds']
        anchor.set_editor_property('content_min',unreal.Vector2D(b['minZ']*100,b['minX']*100)); anchor.set_editor_property('content_max',unreal.Vector2D(b['maxZ']*100,b['maxX']*100))
        anchor.set_editor_property('playable_outline',[unreal.Vector2D(p['z']*100,p['x']*100) for p in source['spatial']['playableOutline']])
        generated=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Generated',False)
        if not generated: raise RuntimeError('Cannot create scene generated layer')
        unreal.EditorLevelUtils.make_level_current(generated)
        population_ids={r['id'] for r in original['population']}; clone(actors,{k:v for k,v in states.items() if k not in population_ids},{})
        unreal.WarImportLibrary.prepare_world_preview_frame(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world())
        rock_clusters['nativeSurfaces']=verify_rock_surfaces(actors,rock_clusters,surface.height_cm)
        cover_rows=clustered_cover(source,surface.height_cm,original['landscapePockets'],cover_layout(source,surface.height_cm,original['landscapePockets']))
        ground_cover(actors,assets,identity,cover_sources[identity],cover_rows)
        understorey=spawn_understorey(actors,identity,source,surface.height_cm,original['landscapePockets'],cover_rows,states,canopies)
        focal=spawn_focal_plants(actors,identity,source,surface.height_cm,original['landscapePockets'],canopies)
        native_cover=cover_inventory(actors)
        for row in original['population']:
            actor=spawn_population(actors,row)
            if not same_state(population_actor(actor),row['savedState']): raise RuntimeError('Scene copy changed population')
        atmosphere=original['atmosphere']; effect=actors.spawn_actor_from_class(unreal.WarRegionalAtmosphere,unreal.Vector())
        effect.set_actor_label(identity+'_regional_atmosphere'); effect.set_editor_property('zone_id',identity)
        effect.set_editor_property('village_centre',unreal.Vector(*atmosphere['villageCentre']))
        for name,key in [('military_centres','militaryCentres'),('steam_sites','steamSites')]: effect.set_editor_property(name,[unreal.Vector(*p) for p in atmosphere[key]])
        effect.set_editor_property('weather_material',unreal.load_asset(atmosphere['material'])); effect.set_editor_property('audio_gain',atmosphere['audioGain'])
        actual=inventory(actors)
        if not same_state(actual,states):
            differences={label:dict(expected=state,actual=actual.get(label)) for label,state in states.items() if not same_state(state,actual.get(label))}
            (BASE/'battlefield-scenes-clone-failure.json').write_text(json.dumps(differences,indent=2)+'\n',encoding='utf-8')
            raise RuntimeError('Scene copy changed expected bindings: '+str(len(differences)))
        if not levels.save_current_level(): raise RuntimeError('Cannot save scene generated layer')
        authored=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Authored',False)
        if not authored: raise RuntimeError('Cannot reserve empty owner scene layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level(): raise RuntimeError('Cannot save owner scene layer')
        levels.set_current_level_by_name('Review'); anchor.set_editor_property('content_levels',[destination+'/Generated',destination+'/Authored'])
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        ground=GroundReview(world,actors,identity,source['spatial']['playableOutline']); spawn=source['spawnPoint']
        support=ground.center([spawn['z']*100,spawn['x']*100,0])
        if not support: raise RuntimeError('Scene copy obstructs village arrival')
        unreal.log('WAR_T1_COUNTER_PLANNING='+identity)
        counters=landscape_walks(source,surface.height_cm,[p for c in all_cells for p in c['placements']],
            lambda x,z:ground.center([z*100,x*100,0]) is not None)
        # Check the retained terrain floor under the roof, including full player capsule support.
        for a,b in zip(shelter['points'],shelter['points'][1:]):
            count=max(1,math.ceil(math.dist(a,b)/100))
            for i in range(count+1):
                point=[a[k]+(b[k]-a[k])*i/count for k in range(3)]
                if not ground.center(point):raise RuntimeError('Shelter blocks normal walking: '+json.dumps(ground.failures))
                camera=unreal.Vector(point[0],point[1],point[2]+420)
                hit=unreal.SystemLibrary.sphere_trace_single(world,camera,camera+unreal.Vector(0,0,.1),42,unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
                if hit and hit.to_tuple()[0]:raise RuntimeError('Shelter blocks its bounded 4.2m camera-height sample')
        shelter['terrainAndCapsuleChecked']=True;shelter['cameraHeightSamplesChecked']=True
        counters.append(dict(id=shelter['id']+'_walk',points=shelter['points'],maximumSourceGrade=.22,terrainAndCapsuleChecked=True,walkingAccepted=False,drivingAccepted=False,appearanceApproved=False))
        unreal.log('WAR_T1_COUNTER_CAPSULE_CHECKED='+identity+' routes='+str(len(counters)))
        _,centre=support; anchor.set_actor_location(centre,False,True)
        world.get_world_settings().set_editor_property('default_game_mode',unreal.WarGameMode)
        if not levels.save_current_level(): raise RuntimeError('Cannot save scene review')
        saved.extend(destination+'/'+n for n in ('Review','Generated','Authored'))
        zones.append({**original,'map':destination+'/Review','parentMap':original['map'],'actorInventory':states,'materials':materials,
                      'sceneCells':cells,'rockShelters':[shelter],'pocketDressing':dressing,'beddedOutcrops':bedding,'landscapeWalks':counters,'groundCover':native_cover,'understorey':understorey,'focalPlanting':focal,'rockClusters':rock_clusters,'waterSurfaces':water_surfaces,'terrainMeshPreserved':True,'sceneScaleAxesVerified':True,'geometryPreserved':False,'appearanceApproved':False,'gameplayAccepted':False})
        unreal.log('WAR_T1_BATTLEFIELD_SCENES_BUILT_ZONE='+identity)
finally: verify_sources(); verify_protected(ROOT,protected)
result=dict(signature=signature,kind='atmosphere',study='battlefield-landscape',inputs=inputs,zones=zones,
    sourceSignature=parent['sourceSignature'],sceneSourceSignature=recipe['signature'],
    packageHashes={p:sha(CONTENT/(p.removeprefix('/Game/')+'.umap')) for p in saved},
    assetHashes={p.relative_to(ROOT).as_posix():sha(p) for p in (CONTENT/'WorldRebuild'/assets.collection).rglob('*.uasset')},
    activeCampaignChanged=False,parentCandidatesUnchanged=True,ownerDocumentsPreserved=True,appearanceApproved=False,
    walkDriveAccepted=False,eighteenVersusEighteenAccepted=False,nodeCandidateGeometrySynchronized=False,nodeTerrainGeometrySynchronized=True,additiveSceneCollisionPending=True,nodePlaytestAccepted=False)
(BASE/('battlefield-scenes-'+signature[:12]+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
(BASE/'battlefield-scenes-latest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
unreal.log('WAR_T1_BATTLEFIELD_SCENES_BUILT='+signature[:12])
