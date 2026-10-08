"""Read-only native overhead witnesses and player-height ceiling detail captures."""
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from t1_home_ceiling import validate_ceiling_witnesses
from t1_materials import protected_saved, verify_protected, sha, same_state
from t1_material_clone import inventory
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
receipt = json.loads((DIRECTORY/'ceilings-latest.json').read_text())
parent = json.loads((DIRECTORY/'shells-latest.json').read_text())
if receipt.get('study')!='timber-ceilings' or parent['signature']!=receipt['inputs']['parentShellSignature']:
    raise RuntimeError('Ceiling review requires its frozen shell parent')
protected = protected_saved(ROOT)
verify_protected(ROOT,receipt['inputs']['protectedHashes'])
for file,digest in {**receipt['inputs']['sourceHashes'],**receipt['inputs']['tools'],**receipt['inputs']['parentAssetHashes'],**receipt['assetHashes']}.items():
    if sha(ROOT/file)!=digest: raise RuntimeError('Ceiling inputs, binaries or assets changed')
for package,digest in receipt['inputs']['dependencyHashes'].items():
    if sha(ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.uasset'))!=digest: raise RuntimeError('Frozen kit dependency changed')
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
checks=[]; pictures=[]
output=DIRECTORY/'ceiling-views'/receipt['signature'][:12]; output.mkdir(parents=True,exist_ok=True)
try:
    for zone in receipt['zones']:
        if not levels.load_level(zone['map']): raise RuntimeError('Ceiling witness map unavailable')
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        states=inventory(actors)
        if not same_state(states,zone['actorInventory']): raise RuntimeError('Saved ceiling inventory changed')
        parent_zone=next(z for z in parent['zones'] if z['id']==zone['id'])
        if not same_state({k:v for k,v in states.items() if k in parent_zone['actorInventory']},parent_zone['actorInventory']):
            raise RuntimeError('Ceiling candidate changed an existing actor')
        if set(states)-set(parent_zone['actorInventory'])!={h['ceiling'][k] for h in zone['homes'] for k in ('label','fillLabel')}:
            raise RuntimeError('Ceiling candidate has unexpected additions')
        for home in zone['homes']:
            ceiling=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==home['ceiling']['label'])
            house=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==home['id'])
            transform=ceiling.get_actor_transform(); recipe=home['ceiling']['recipe']; rows=[]
            for probe in recipe['probes']:
                hit=unreal.SystemLibrary.line_trace_single(world,transform.transform_location(unreal.Vector(*probe['start'])),
                    transform.transform_location(unreal.Vector(*probe['end'])),unreal.TraceTypeQuery.ECC_VISIBILITY,
                    True,[],unreal.DrawDebugTrace.NONE,True)
                parts=hit.to_tuple() if hit else None
                foreground=parts[9].get_actor_label() if parts and parts[0] and parts[9] else None
                # A chimney/cupboard belongs to the unchanged merged house.
                # Record that foreground hit, then isolate the ceiling behind
                # it. The independent home capsule review ignores no furniture.
                if parts and parts[0] and parts[9]==house:
                    hit=unreal.SystemLibrary.line_trace_single(world,transform.transform_location(unreal.Vector(*probe['start'])),
                        transform.transform_location(unreal.Vector(*probe['end'])),unreal.TraceTypeQuery.ECC_VISIBILITY,
                        True,[house],unreal.DrawDebugTrace.NONE,True)
                    parts=hit.to_tuple() if hit else None
                blocked=bool(parts and parts[0] and parts[9]==ceiling)
                rows.append(dict(probe=probe,blockedByCeiling=blocked,
                    localHeight=transform.inverse_transform_location(parts[5]).z if blocked else None,
                    foregroundBlocker=foreground,houseForegroundIsolated=foreground==home['id'],
                    blocker=parts[9].get_actor_label() if parts and parts[0] and parts[9] else None))
            try:
                validate_ceiling_witnesses(recipe,rows)
            except ValueError:
                (DIRECTORY/'ceiling-failed-witnesses.json').write_text(json.dumps(dict(signature=receipt['signature'],
                    home=home['id'],recipe=recipe,witnesses=rows),indent=2)+'\n')
                raise
            checks.append(dict(zone=zone['id'],home=home['id'],witnesses=rows,
                minimumMeasuredCeilingHeadroomCm=min(r['localHeight'] for r in rows)-recipe['floorTopZ'],
                boundsMinimumHeadroomCm=recipe['minimumHeadroomCm'],overheadClosed=True))
        capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector()); component=capture.capture_component2d
        component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1280,800,unreal.TextureRenderTargetFormat.RTF_RGBA8)
        component.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
        component.capture_every_frame=False; component.capture_on_movement=False; component.always_persist_rendering_state=True
        component.fov_angle=75; component.post_process_blend_weight=0
        for phase,seconds in [('day',1200),('dusk',2250),('night',2700)]:
            if not unreal.WarZoneLightingSubsystem.preview_environment(world,zone['id'],unreal.Vector(),seconds,0):
                raise RuntimeError('Ceiling atmosphere unavailable')
            for home in zone['homes']:
                ceiling=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==home['ceiling']['label'])
                transform=ceiling.get_actor_transform(); recipe=home['ceiling']['recipe']
                eye=transform.transform_location(unreal.Vector(150,-recipe['roomSize'][1]/2+180,recipe['floorTopZ']+160))
                target=transform.transform_location(unreal.Vector(-150,recipe['roomSize'][1]/2-150,recipe['bottomZ']-20))
                capture.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,target),False,True)
                for _ in range(64): unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
                file=output/(home['id']+'_ceiling_'+phase+'.png')
                unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(output),file.name)
                pictures.append(dict(file=file.relative_to(ROOT).as_posix(),zone=zone['id'],home=home['id'],phase=phase,
                    eye=[eye.x,eye.y,eye.z],target=[target.x,target.y,target.z],cameraAccepted=False))
        actors.destroy_actor(capture); unreal.WarZoneLightingSubsystem.preview_world(world,'aegis_capital',unreal.Vector())
finally:
    verify_protected(ROOT,protected)
for package,digest in {**receipt['inputs']['parentPackages'],**receipt['packageHashes']}.items():
    if sha(ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap'))!=digest: raise RuntimeError('Ceiling review changed a saved map')
result=dict(signature=receipt['signature'],checks=checks,pictures=pictures,pictureDirectory=output.relative_to(ROOT).as_posix(),
    overheadClosed=len(checks)==4 and all(c['overheadClosed'] for c in checks),savedCandidatesUnchanged=True,
    parentActorsUnchanged=True,visualApproved=False,ceilingLodAppearanceAccepted=False,cameraAccepted=False,walkDriveAccepted=False)
(DIRECTORY/'ceiling-review.json').write_text(json.dumps(result,indent=2)+'\n')
unreal.log('WAR_T1_CEILINGS_REVIEWED='+str(sum(len(c['witnesses']) for c in checks)))
