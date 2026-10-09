"""Bake both retained agents only in new private T1 routing copies; preserve all scenery/owner layers."""
import datetime,hashlib,json,math,sys
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from t1_navigation import navigation_map,route_inventory,validate_probe,probe_profiles
from t1_materials import protected_saved,verify_protected,same_state
from t1_material_clone import inventory
from t1_battlefield import Surface
from world_actor_state import snapshot

BASE=ROOT/'artifacts/unreal/t1-redesign';CONTENT=ROOT/'unreal/AegisWar/Content'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent=read(BASE/'battlefield-scenes-latest.json');views=read(BASE/'battlefield-scenes-review.json');walk=read(BASE/'battlefield-scenes-traversal-headless-latest.json')
if parent.get('study')!='battlefield-landscape' or any(r['signature']!=parent['signature'] or not r['savedCandidatesUnchanged'] for r in (views,walk)) or not views.get('materialShaderCompilationPassed'):
    raise RuntimeError('Navigation needs its exact rendered and walked landscape parent')
files={**parent['inputs']['sourceHashes'],**parent['inputs']['tools'],**parent['assetHashes']}
packages={**parent['inputs']['parentPackages'],**parent['packageHashes']}
files.update({'unreal/AegisWar/Content/'+p.removeprefix('/Game/')+'.uasset':h for p,h in parent['inputs']['dependencyHashes'].items()})
files.update(read(BASE/'plan.json')['privateMapHashes'])
protected=protected_saved(ROOT)
tools=['scripts/unreal/build-t1-navigation.py','scripts/unreal/t1_navigation.py','scripts/unreal/t1_material_clone.py',
    'scripts/unreal/t1_materials.py','scripts/unreal/t1_battlefield.py','scripts/unreal/world_actor_state.py',
    'unreal/AegisWar/Config/DefaultEngine.ini','unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll',
    'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWarEditorTools.dll',
    'unreal/AegisWar/Source/AegisWarEditorTools/Public/WarT1NavigationAuthoringLibrary.h',
    'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarT1NavigationAuthoringLibrary.cpp',
    'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarT1NavigationFootprint.cpp',
    'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarT1NavigationPrismBuilder.h']
files.update({p:sha(ROOT/p) for p in tools})
def verify():
    for p,h in files.items():
        if sha(ROOT/p)!=h:raise RuntimeError('Preserve changed T1 source binding: '+p)
    for p,h in packages.items():
        if sha(CONTENT/(p.removeprefix('/Game/')+'.umap'))!=h:raise RuntimeError('Preserve changed parent map: '+p)
    verify_protected(ROOT,protected)
verify()
diagnostic='-wart1navigationdiagnostic' in unreal.SystemLibrary.get_command_line().lower()
inputs=dict(diagnostic=diagnostic,createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),parentSignature=parent['signature'],
    sourceHashes=files,parentPackages=packages,dependencyHashes=parent['inputs']['dependencyHashes'],protectedHashes=protected,
    tools={p:sha(ROOT/p) for p in tools})
signature=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
zones=[];saved={}
def description(world):
    data=json.loads(unreal.WarSiegeAuthoringLibrary.describe_baked_navigation(world))
    rows=data['actors']
    if len(rows)!=2 or {r['profile'] for r in rows}!={'Default','SiegeConvoy'}:
        raise RuntimeError('Both distinct retained native agents must be baked')
    for r in rows:
        if not r['registered'] or r['needsRebuild'] or r['activeTiles']<=0 or r['activeTiles']>16384 or not r['tileSnapshot']:
            raise RuntimeError('Native tile inventory is missing, unregistered, dirty or unbounded')
    return data

def probes(world,identity,routes):
    result=[];failures=[]
    for route in routes:
        for convoy in probe_profiles(route):
            probe=json.loads(unreal.WarT1NavigationAuthoringLibrary.probe_route(world,identity,convoy,[unreal.Vector(*p) for p in route['points']]))
            result.append(dict(id=route['id'],kind=route['kind'],convoy=convoy,probe=probe))
            try:validate_probe(probe,route,convoy)
            except ValueError:
                (BASE/('navigation-failure-'+signature[:12]+'.json')).write_text(json.dumps(dict(zone=identity,map=world.get_path_name(),routes=result),indent=2)+'\n')
                failure=identity+' / '+route['id']+' / '+('convoy' if convoy else 'pedestrian')
                failures.append(failure)
                unreal.log_warning('WAR_T1_NAV_ROUTE_FAILED='+failure)
                if not diagnostic:raise RuntimeError('Native navigation route failed: '+failure)
    return result,failures

all_failures=[]
try:
    for original in parent['zones']:
        identity=original['id'];target=navigation_map(signature,identity)
        if unreal.EditorAssetLibrary.does_asset_exist(target):raise RuntimeError('Preserve existing navigation candidate')
        if not unreal.EditorAssetLibrary.duplicate_asset(original['map'],target):raise RuntimeError('Cannot create isolated navigation routing')
        if not levels.load_level(target):raise RuntimeError('Cannot load isolated navigation routing')
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world);unreal.WarImportLibrary.prepare_world_preview_frame(world)
        if not levels.set_current_level_by_name('Review'):raise RuntimeError('Cannot select private persistent routing')
        if not same_state(inventory(actors),original['actorInventory']):raise RuntimeError('Parent scenery inventory changed')
        before={a.get_path_name():snapshot(a) for a in actors.get_all_level_actors()}
        source=read(ROOT/original['sourceDirectory']/(identity+'.json'))
        surface=Surface(source,read(ROOT/original['sourceDirectory']/(identity+'_terrain.json')))
        routes=route_inventory(source,surface.height_cm)
        anchors=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarZoneAnchor)]
        if len(anchors)!=1:raise RuntimeError('Exactly one regional anchor required')
        attachments=list(map(str,anchors[0].get_editor_property('content_levels')))
        vertical=[]
        for a in actors.get_all_level_actors():
            if isinstance(a,unreal.StaticMeshActor) and str(a.static_mesh_component.get_collision_profile_name())!='NoCollision':
                origin,extent=a.get_actor_bounds(True);vertical.extend((origin.z-extent.z,origin.z+extent.z))
        if not vertical:raise RuntimeError('Native collision height envelope is missing')
        minimum=math.floor(min(vertical)-1000);maximum=math.ceil(max(vertical)+1000)
        unreal.log('WAR_T1_NAV_BUILD_START='+identity)
        build=json.loads(unreal.WarT1NavigationAuthoringLibrary.build_navigation(world,identity,attachments,minimum,maximum))
        if not build.get('passed'):raise RuntimeError('Navigation authoring rejected: '+json.dumps(build))
        if {a.get_path_name():snapshot(a) for a in actors.get_all_level_actors() if a.get_path_name() in before}!=before:
            raise RuntimeError('Navigation authoring changed an existing actor/component')
        baked=description(world);before_probes,failures=probes(world,identity,routes);all_failures.extend(failures)
        if not levels.save_current_level():raise RuntimeError('Cannot save isolated baked navigation')
        saved[target]=sha(CONTENT/(target.removeprefix('/Game/')+'.umap'))
        # Reload the saved map and compare native tile payloads, not just editor geometry.
        unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
        if not levels.load_level(target):raise RuntimeError('Cannot reload saved navigation')
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world);unreal.WarImportLibrary.prepare_world_preview_frame(world)
        reloaded=description(world)
        if reloaded!=baked:raise RuntimeError('Saved native navigation payloads differ after reload')
        after_probes,reload_failures=probes(world,identity,routes)
        if reload_failures!=failures:raise RuntimeError('Navigation probe failures changed across reload')
        if not same_state(inventory(actors),original['actorInventory']):raise RuntimeError('Reloaded scenery changed')
        if sha(CONTENT/(target.removeprefix('/Game/')+'.umap'))!=saved[target]:raise RuntimeError('Read-only reload changed navigation map bytes')
        zones.append(dict(**{k:v for k,v in original.items() if k not in ('map','parentMap')},map=target,parentMap=original['map'],
            navigation=dict(build=build,reloaded=reloaded,beforeSave=before_probes,afterReload=after_probes,
                verticalBoundsCm=[minimum,maximum],routeInventory=routes,failures=failures,saveReloadVerified=True,drivingAccepted=False)))
        unreal.log('WAR_T1_NAV_'+('DIAGNOSTIC' if diagnostic else 'VERIFIED')+'='+identity+' routes='+str(len(routes))+' failures='+str(len(failures)))
finally:verify()
receipt=dict(schemaVersion=1,signature=signature,parentSignature=parent['signature'],kind='atmosphere',study='battlefield-navigation',
    sourceSignature=parent['sourceSignature'],inputs=inputs,zones=zones,packageHashes=saved,assetHashes=parent['assetHashes'],
    navigationVerified=not all_failures,diagnostic=diagnostic,failures=all_failures,parentCandidatesUnchanged=True,ownerDocumentsPreserved=True,activeCampaignChanged=False,
    appearanceApproved=False,walkDriveAccepted=False,drivingAccepted=False,eighteenVersusEighteenAccepted=False,releaseAccepted=False)
if diagnostic:
    file=BASE/('navigation-diagnostic-'+signature[:12]+'.json')
    file.write_text(json.dumps(receipt,indent=2)+'\n')
    unreal.log('WAR_T1_NAV_DIAGNOSTIC_SAVED='+signature[:12]+' failures='+str(len(all_failures)))
else:
    if all_failures:raise RuntimeError('Incomplete navigation must never be admitted')
    (BASE/('battlefield-navigation-'+signature[:12]+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    (BASE/'battlefield-navigation-latest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    unreal.log('WAR_T1_NAVIGATION_BUILT='+signature[:12])
