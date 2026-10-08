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
    r['layers']['terrain']['tint']=[.55,.95,1.1,1] if identity=='sunmeadow_march' else [1.65,1.65,1.6,1]
    r['layers']['terrain']['rockColor']=[.3,.29,.26] if identity=='sunmeadow_march' else [.13,.135,.14]
    r['layers']['terrain']['macroMinimum']=.75
    for layer in r['layers'].values(): layer['surfaceVariation']=surface_variation()
tools=['scripts/unreal/build-t1-battlefield-scenes.py','scripts/unreal/t1_material_assets.py','scripts/unreal/t1_surface_variation.py','scripts/unreal/t1_materials.py',
       'scripts/unreal/t1_battlefield.py','scripts/unreal/t1_material_clone.py','scripts/unreal/t1_population_native.py',
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
        for cell in cells:
            for p in cell['placements']:
                state=copy.deepcopy(original['actorInventory'][p['sourceLabel']])
                if state['kind']!='mesh': raise RuntimeError('Scene socket requires its admitted static source')
                # Python's Rotator properties are float32; freeze that admitted precision before cloning.
                yaw=struct.unpack('<f',struct.pack('<f',(p['yawDegrees']+180)%360-180))[0]
                state['scale']=[p['scale']]*3; state['rotation']=[0,yaw,0]
                h=surface.height_cm(p['x'],p['z'])
                if p['grounding']=='embed':
                    # Bury broad rock feet below the lowest surrounding ground instead of levelling the hillside.
                    radius=math.hypot(p['width'],p['depth'])/2
                    h=min(surface.height_cm(p['x']+radius*x/3,p['z']+radius*z/3) for x in range(-3,4) for z in range(-3,4)) - 20
                state['location']=[p['z']*100,p['x']*100,h]; state['tags']+=['WarT1BattlefieldSceneCell']
                if p['id'] in states: raise RuntimeError('Duplicate scene actor identity')
                states[p['id']]=state
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
        _,centre=support; anchor.set_actor_location(centre,False,True)
        world.get_world_settings().set_editor_property('default_game_mode',unreal.WarGameMode)
        if not levels.save_current_level(): raise RuntimeError('Cannot save scene review')
        saved.extend(destination+'/'+n for n in ('Review','Generated','Authored'))
        zones.append({**original,'map':destination+'/Review','parentMap':original['map'],'actorInventory':states,'materials':materials,
                      'sceneCells':cells,'terrainMeshPreserved':True,'geometryPreserved':False,'appearanceApproved':False,'gameplayAccepted':False})
        unreal.log('WAR_T1_BATTLEFIELD_SCENES_BUILT_ZONE='+identity)
finally: verify_sources(); verify_protected(ROOT,protected)
result=dict(signature=signature,kind='atmosphere',study='battlefield-landscape',inputs=inputs,zones=zones,
    sourceSignature=parent['sourceSignature'],sceneSourceSignature=recipe['signature'],
    packageHashes={p:sha(CONTENT/(p.removeprefix('/Game/')+'.umap')) for p in saved},
    assetHashes={p.relative_to(ROOT).as_posix():sha(p) for p in (CONTENT/'WorldRebuild'/assets.collection).rglob('*.uasset')},
    activeCampaignChanged=False,parentCandidatesUnchanged=True,ownerDocumentsPreserved=True,appearanceApproved=False,
    walkDriveAccepted=False,eighteenVersusEighteenAccepted=False,nodeCandidateGeometrySynchronized=True,nodePlaytestAccepted=False)
(BASE/('battlefield-scenes-'+signature[:12]+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
(BASE/'battlefield-scenes-latest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
unreal.log('WAR_T1_BATTLEFIELD_SCENES_BUILT='+signature[:12])
