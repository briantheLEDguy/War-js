"""Attach a fully assembled campaign layer to the owner's main city, preserving unrelated sublevels."""
import datetime
import hashlib
import json
import shutil
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
directory=ROOT/'artifacts/unreal/world-portals'
receipt=json.loads((directory/'candidate.json').read_text())
old=json.loads((directory/'build.json').read_text()) if (directory/'build.json').exists() else {}
if old.get('partitionManifest'):
    raise RuntimeError('The campaign is partitioned. Use zone-specific updates; attaching a combined layer would discard zone work.')
# Preserve later population receipts when reattaching the same generated package.
if old.get('attached') and old.get('layer')==receipt['layer'] and old.get('planSha256')==receipt['planSha256']:
    receipt=old
if receipt['planSha256'] != hashlib.sha256((directory/'plan.json').read_bytes()).hexdigest(): raise RuntimeError('Stale campaign candidate')
if receipt['staticPlanSha256'] != hashlib.sha256((directory/'static/plan.json').read_bytes()).hexdigest(): raise RuntimeError('Stale scenery candidate')
plan=json.loads((directory/'plan.json').read_text())
if set(receipt['zones']) != {row['id'] for row in plan['zones']} or set(receipt['portals']) != {row['id'] for row in plan['routes']}:
    raise RuntimeError('Incomplete campaign candidate')
main_file=ROOT/'unreal/AegisWar/Content'/(receipt['map'].removeprefix('/Game/')+'.umap')
before=hashlib.sha256(main_file.read_bytes()).hexdigest()
shutil.copy2(main_file,directory/('main-before-world-'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.umap'))
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level(receipt['map']): raise RuntimeError('Main city unavailable')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
previous=old.get('layer')
if previous and previous != receipt['layer']:
    if not previous.startswith('/Game/WorldRebuild/'): raise RuntimeError('Refusing to detach unowned layer')
    streaming=unreal.GameplayStatics.get_streaming_level(world,previous)
    if streaming and not unreal.EditorLevelUtils.remove_level_from_world(streaming.get_loaded_level()): raise RuntimeError('Could not detach previous campaign layer')
if not unreal.GameplayStatics.get_streaming_level(world,receipt['layer']):
    if not unreal.EditorLevelUtils.add_level_to_world(world,receipt['layer'],unreal.LevelStreamingAlwaysLoaded): raise RuntimeError('Could not attach campaign')
unreal.GameplayStatics.flush_level_streaming(world)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
routes=[str(actor.get_editor_property('route_id')) for actor in actors if isinstance(actor,unreal.WarZonePortal)]
zones=[str(actor.get_editor_property('zone_id')) for actor in actors if isinstance(actor,unreal.WarZoneAnchor)]
if sorted(routes) != sorted(receipt['portals']) or sorted(zones) != sorted(receipt['zones']):
    raise RuntimeError('Loaded campaign actors do not match the candidate; main map has not been saved')
if not level.set_current_level_by_name(main_file.stem) or not level.save_current_level(): raise RuntimeError('Could not save main city attachment')
receipt.update(attached=True,runtimeTraversalVerified=False,capitalSha256Before=before,capitalSha256After=hashlib.sha256(main_file.read_bytes()).hexdigest())
(directory/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
unreal.log('WAR_CAMPAIGN_ATTACHED='+receipt['map'])
