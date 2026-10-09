"""Fresh first-pair native terrain/road candidates, rebasing retained complete assemblies."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0,str(Path(__file__).parent))
from t1_battlefield import Surface,rebase_inventory,rebase_population,rebase_homes
from t1_material_clone import inventory,clone
from t1_population_native import population_actor,spawn_population,GroundReview
from t1_materials import protected_saved,verify_protected,sha,same_state
from world_build_assets import WorldAssets

BASE = ROOT/'artifacts/unreal/t1-redesign'; CONTENT = ROOT/'unreal/AegisWar/Content'
read = lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
bundle = read(BASE/'battlefield-source-latest.json'); directory = ROOT/bundle['directory']
parent = read(BASE/'relief-latest.json'); walkthrough = read(ROOT/bundle['parentWalkthroughFile'])
if bundle['parentRelief'] != parent['signature'] or bundle['parentWalkthrough'] != walkthrough['signature']:
    raise RuntimeError('Battlefield parent revision changed')
files = {**bundle['inputs'],**bundle['files'],**walkthrough['sourceFileHashes']}
packages = {**walkthrough['sourcePackageHashes'],**walkthrough['packageHashes']}
def verify_sources():
    for p,h in files.items():
        if sha(ROOT/p) != h: raise RuntimeError('Preserve changed battlefield source: '+p)
    for p,h in packages.items():
        if sha(CONTENT/(p.removeprefix('/Game/')+'.umap')) != h: raise RuntimeError('Preserve changed native parent: '+p)
verify_sources(); protected = protected_saved(ROOT)
tools = ['scripts/unreal/build-t1-battlefield.py','scripts/unreal/t1_battlefield.py','scripts/unreal/t1_material_clone.py',
         'scripts/unreal/t1_population_native.py','scripts/unreal/world_build_assets.py','unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll']
inputs = dict(sourceSignature=bundle['signature'],createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              tools={p:sha(ROOT/p) for p in tools},sourceHashes=files,parentPackages=packages,protectedHashes=protected,
              dependencyHashes=parent['inputs']['dependencyHashes'])
signature = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
assets = WorldAssets(ROOT,'T1Redesign_Atmosphere_'+signature[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f')); levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); zones=[]; saved=[]
try:
    for definition in parent['zones']:
        identity = definition['id']; source = read(directory/(identity+'.json')); previous = read(BASE/(identity+'.json'))
        if not levels.load_level(definition['map']): raise RuntimeError('Cannot load retained parent')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        if not same_state(inventory(actors),definition['actorInventory']): raise RuntimeError('Parent inventory changed')
        for row in definition['population']:
            actor = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == row['id'])
            if not same_state(population_actor(actor),row['savedState']): raise RuntimeError('Parent population changed')
        old_surface = Surface(previous,read(BASE/(identity+'_terrain.json'))); surface = Surface(source,read(directory/(identity+'_terrain.json')))
        states,rebase = rebase_inventory(definition['actorInventory'],previous,source,old_surface,surface)
        population = rebase_population(definition['population'],old_surface,surface)
        for role in ('terrain','roads'):
            state = states[identity+'_'+role]
            mesh = assets.mesh(identity+'_'+role,read(directory/(identity+'_'+role+'.json')),unreal.load_asset(state['materials'][0]),role=='terrain')
            state['mesh'] = mesh.get_path_name()
        destination = assets.folder+'/'+identity
        if not levels.new_level(destination+'/Review'): raise RuntimeError('Cannot create fresh battlefield routing')
        anchor = actors.spawn_actor_from_class(unreal.WarZoneAnchor,unreal.Vector())
        anchor.set_editor_property('zone_id',identity); anchor.set_editor_property('zone_origin',unreal.Vector())
        b=source['spatial']['bounds']; anchor.set_editor_property('use_spatial_bounds',True)
        anchor.set_editor_property('content_min',unreal.Vector2D(b['minZ']*100,b['minX']*100))
        anchor.set_editor_property('content_max',unreal.Vector2D(b['maxZ']*100,b['maxX']*100))
        anchor.set_editor_property('playable_outline',[unreal.Vector2D(p['z']*100,p['x']*100) for p in source['spatial']['playableOutline']])
        generated = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Generated',False)
        if not generated: raise RuntimeError('Cannot create battlefield generated layer')
        unreal.EditorLevelUtils.make_level_current(generated)
        population_ids={r['id'] for r in population}; clone(actors,{k:v for k,v in states.items() if k not in population_ids},{})
        for row in population:
            actor = spawn_population(actors,row)
            if not same_state(population_actor(actor),row['savedState']): raise RuntimeError('Population rebase changed identity/visual bindings')
        atmosphere = copy.deepcopy(definition['atmosphere'])
        for p in [atmosphere['villageCentre'],*atmosphere['militaryCentres'],*atmosphere['steamSites']]: p[2] = surface.height_cm(p[1]/100,p[0]/100)
        effect=actors.spawn_actor_from_class(unreal.WarRegionalAtmosphere,unreal.Vector())
        effect.set_actor_label(identity+'_regional_atmosphere'); effect.set_editor_property('zone_id',identity)
        effect.set_editor_property('village_centre',unreal.Vector(*atmosphere['villageCentre']))
        for name,key in [('military_centres','militaryCentres'),('steam_sites','steamSites')]: effect.set_editor_property(name,[unreal.Vector(*p) for p in atmosphere[key]])
        effect.set_editor_property('weather_material',unreal.load_asset(atmosphere['material'])); effect.set_editor_property('audio_gain',atmosphere['audioGain'])
        if not same_state(inventory(actors),states): raise RuntimeError('Battlefield clone changed expected bindings')
        if not levels.save_current_level(): raise RuntimeError('Cannot save battlefield generated layer')
        authored=unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded,destination+'/Authored',False)
        if not authored: raise RuntimeError('Cannot reserve a fresh owner layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level(): raise RuntimeError('Cannot save new empty owner layer')
        levels.set_current_level_by_name('Review'); anchor.set_editor_property('content_levels',[destination+'/Generated',destination+'/Authored'])
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        review = GroundReview(world,actors,identity,source['spatial']['playableOutline']); spawn=source['spawnPoint']
        supported=review.center([spawn['z']*100,spawn['x']*100,spawn['y']*100])
        if not supported: raise RuntimeError('Battlefield arrival lacks clear capsule support: '+json.dumps(review.failures))
        ground,centre=supported; anchor.set_actor_location(centre,False,True)
        world.get_world_settings().set_editor_property('default_game_mode',unreal.WarGameMode)
        if not levels.save_current_level(): raise RuntimeError('Cannot save safe battlefield routing')
        saved.extend(destination+'/'+n for n in ('Review','Generated','Authored'))
        zones.append(dict(**{k:v for k,v in definition.items() if k not in ('map','parentMap','actorInventory','population','atmosphere','homes','geometryPreserved')},
            map=destination+'/Review',parentMap=definition['map'],sourceDirectory=bundle['directory'],
            landscapePockets=read(directory/(identity+'_pockets.json')),
            homes=rebase_homes(definition['homes'],rebase['completeAssemblyDeltasCm'],old_surface,surface),
            actorInventory=states,population=population,atmosphere=atmosphere,rebase=rebase,arrivalCm=[centre.x,centre.y,centre.z],
            nativeArrivalClear=True,geometryPreserved=False,appearanceApproved=False,gameplayAccepted=False))
        unreal.log('WAR_T1_BATTLEFIELD_BUILT_ZONE='+identity)
finally:
    verify_sources(); verify_protected(ROOT,protected)
receipt=dict(signature=signature,kind='atmosphere',study='battlefield-landscape',inputs=inputs,sourceSignature=bundle['signature'],zones=zones,
    packageHashes={p:sha(CONTENT/(p.removeprefix('/Game/')+'.umap')) for p in saved},
    assetHashes={p.relative_to(ROOT).as_posix():sha(p) for p in (CONTENT/'WorldRebuild'/assets.collection).rglob('*.uasset')},
    activeCampaignChanged=False,parentCandidatesUnchanged=True,ownerDocumentsPreserved=True,appearanceApproved=False,
    walkDriveAccepted=False,eighteenVersusEighteenAccepted=False,nodeCandidateGeometrySynchronized=True,nodePlaytestAccepted=False)
(BASE/('battlefield-'+signature[:12]+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
(BASE/'battlefield-latest.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
unreal.log('WAR_T1_BATTLEFIELD_BUILT='+signature[:12])
