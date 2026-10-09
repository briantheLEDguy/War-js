"""Clone only T1 routing into new safe-entry walkthroughs; leave parent levels and GM drafts intact."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from t1_review import review_map, arrival_point
from t1_navigation import navigation_payload, validate_navigation_parent
from t1_materials import protected_saved, verify_protected
from t1_population_native import GroundReview
from world_actor_state import snapshot

DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
CONTENT = ROOT/'unreal/AegisWar/Content'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
navigation = '-wart1navigation' in unreal.SystemLibrary.get_command_line().lower()
scene_cells = navigation or '-wart1battlefieldscenes' in unreal.SystemLibrary.get_command_line().lower()
landscape = read(DIRECTORY/('battlefield-scenes-latest.json' if scene_cells else 'relief-latest.json'))
parent = read(DIRECTORY/'battlefield-navigation-latest.json') if navigation else landscape
if navigation: validate_navigation_parent(parent,landscape['signature'])
if landscape.get('study') != ('battlefield-landscape' if scene_cells else 'dramatic-relief'): raise RuntimeError('Expected the matching verified first-pair candidates')
if scene_cells:
    views = read(DIRECTORY/'battlefield-scenes-review.json')
    walking = read(DIRECTORY/'battlefield-scenes-traversal-headless-latest.json')
    if views['signature'] != landscape['signature'] or walking['signature'] != landscape['signature'] or not views['savedCandidatesUnchanged'] or not walking['savedCandidatesUnchanged'] or not views.get('materialShaderCompilationPassed'):
        raise RuntimeError('Walkthrough staging needs matching native ground/views and configured walking evidence')
source_packages = {**parent['inputs']['parentPackages'], **parent['packageHashes']}
source_assets = {**parent['inputs'].get('parentAssetHashes',{}), **parent['assetHashes']}
source_assets.update({'unreal/AegisWar/Content/'+p.removeprefix('/Game/')+'.uasset': h
                     for p,h in parent['inputs']['dependencyHashes'].items()})
source_assets.update(parent['inputs']['sourceHashes'])
source_assets['unreal/AegisWar/Config/DefaultEngine.ini'] = sha(ROOT/'unreal/AegisWar/Config/DefaultEngine.ini')
def verify_sources():
    for p,h in source_packages.items():
        if sha(CONTENT/(p.removeprefix('/Game/')+'.umap')) != h: raise RuntimeError('Preserve changed source map: '+p)
    for p,h in source_assets.items():
        if sha(ROOT/p) != h: raise RuntimeError('Preserve changed source binding: '+p)
verify_sources()
protected = protected_saved(ROOT)
inputs = dict(parent=parent['signature'], createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              tools={p:sha(ROOT/p) for p in ('scripts/unreal/stage-t1-review.py','scripts/unreal/t1_review.py','scripts/unreal/t1_navigation.py',
                    'scripts/unreal/t1_population_native.py','scripts/unreal/world_actor_state.py',
                    'unreal/AegisWar/Source/AegisWar/Public/WarWorldEditMap.h',
                    'unreal/AegisWar/Source/AegisWar/Private/WarT1ReviewProof.cpp',
                    'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll')})
signature = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rows = []; packages = {}
try:
    for zone in parent['zones']:
        identity = zone['id']; target = review_map(signature,identity)
        if unreal.EditorAssetLibrary.does_asset_exist(target): raise RuntimeError('Preserve existing review wrapper')
        if not unreal.EditorAssetLibrary.duplicate_asset(zone['map'],target): raise RuntimeError('Cannot copy private routing')
        if not levels.load_level(target): raise RuntimeError('Cannot load private walkthrough')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world)
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        anchors = [a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarZoneAnchor)]
        if len(anchors) != 1 or str(anchors[0].get_editor_property('zone_id')) != identity:
            raise RuntimeError('Walkthrough requires its unique regional anchor')
        anchor = anchors[0]
        if anchor.get_outer().get_path_name().split('.')[0] != target: raise RuntimeError('Anchor belongs to a parent layer')
        if navigation:
            copied_navigation = navigation_payload(json.loads(unreal.WarSiegeAuthoringLibrary.describe_baked_navigation(world)))
            if copied_navigation != navigation_payload(zone['navigation']['reloaded']): raise RuntimeError('Routing copy changed baked navigation')
        before = {a.get_path_name():snapshot(a) for a in actors.get_all_level_actors() if a != anchor}
        source = read(ROOT/zone['sourceDirectory']/(identity+'.json')) if scene_cells else read(DIRECTORY/(identity+'.json'))
        reviewer = GroundReview(world,actors,identity,source['spatial']['playableOutline'])
        support = reviewer.center(arrival_point(source))
        if not support: raise RuntimeError('Authored arrival is obstructed: '+json.dumps(reviewer.failures))
        ground, centre = support
        old = [anchor.get_actor_location().x,anchor.get_actor_location().y,anchor.get_actor_location().z]
        anchor.set_actor_location(centre,False,True)
        anchor.set_actor_rotation(unreal.Rotator(yaw=90 if identity=='sunmeadow_march' else -90),False)
        world.get_world_settings().set_editor_property('default_game_mode',unreal.WarGameMode)
        after = {a.get_path_name():snapshot(a) for a in actors.get_all_level_actors() if a != anchor}
        if after != before: raise RuntimeError('Walkthrough changed unrelated actor/component state')
        if not levels.set_current_level_by_name('Walkthrough') or not levels.save_current_level():
            raise RuntimeError('Cannot save private routing arrival')
        packages[target] = sha(CONTENT/(target.removeprefix('/Game/')+'.umap'))
        if navigation:
            unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
            if not levels.load_level(target): raise RuntimeError('Cannot reload safe navigation walkthrough')
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
            if navigation_payload(json.loads(unreal.WarSiegeAuthoringLibrary.describe_baked_navigation(world))) != copied_navigation:
                raise RuntimeError('Saved safe walkthrough changed baked navigation')
            if packages[target] != sha(CONTENT/(target.removeprefix('/Game/')+'.umap')): raise RuntimeError('Reload changed saved walkthrough bytes')
        rows.append(dict(id=identity,map=target,parentMap=zone['map'],arrivalCm=[centre.x,centre.y,centre.z],
                    terrainGroundCm=ground,navigationSaveReloadVerified=navigation,previousUnsafeAnchorCm=old,nativeArrivalClear=True,parentContentUnchanged=True,
                    streamingDeclarations=list(unreal.WarImportLibrary.get_streaming_level_package_names(world))))
finally:
    verify_sources(); verify_protected(ROOT,protected)
receipt = dict(schemaVersion=1,signature=signature,inputs=inputs,parentSignature=parent['signature'],zones=rows,
               packageHashes=packages,sourcePackageHashes=source_packages,sourceFileHashes=source_assets,
               sourcePackagesUnchanged=True,requiresDevelopmentGM=True,published=False,visualApproved=False,
               gameplayApproved=False,ownerDocumentsPreserved=True)
(DIRECTORY/('review-'+signature[:12]+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
(DIRECTORY/'review-latest.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
unreal.log('WAR_T1_REVIEW_STAGED='+signature[:12])
