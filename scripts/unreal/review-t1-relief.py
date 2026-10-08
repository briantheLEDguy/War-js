"""Compare player-height parent/relief vistas and native full-width route ground."""
import json
import math
from pathlib import Path
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(Path(__file__).resolve().parent))
from t1_materials import protected_saved,verify_protected,sha,same_state
from t1_material_clone import inventory
from t1_population_native import population_actor
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'; CONTENT=ROOT/'unreal/AegisWar/Content'
receipt=json.loads((DIRECTORY/'relief-latest.json').read_text(encoding='utf-8'))
parent=json.loads((DIRECTORY/'population-latest.json').read_text(encoding='utf-8'))
if receipt.get('study')!='dramatic-relief' or receipt['inputs']['parentPopulationSignature']!=parent['signature']:
    raise RuntimeError('Relief review requires its frozen population parent')
if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower(): raise RuntimeError('Relief comparison needs rendering')
protected=protected_saved(ROOT); verify_protected(ROOT,receipt['inputs']['protectedHashes'])
for file,digest in {**receipt['inputs']['tools'],**receipt['inputs']['sourceHashes'],**receipt['inputs']['parentAssetHashes'],**receipt['assetHashes']}.items():
    if sha(ROOT/file)!=digest: raise RuntimeError('Relief input, binary or asset changed')
for package,digest in receipt['inputs']['dependencyHashes'].items():
    if sha(CONTENT/(package.removeprefix('/Game/')+'.uasset'))!=digest: raise RuntimeError('Retained relief dependency changed')
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
output=DIRECTORY/'relief-views'/receipt['signature'][:12]; output.mkdir(parents=True,exist_ok=True)
pictures=[]; checks=[]
try:
    for zone in receipt['zones']:
        source=json.loads((DIRECTORY/(zone['id']+'.json')).read_text(encoding='utf-8')); parent_zone=next(z for z in parent['zones'] if z['id']==zone['id'])
        witness_sets={}; frozen_cameras={}
        for version,definition in [('before',parent_zone),('after',zone)]:
            if not levels.load_level(definition['map']): raise RuntimeError('Relief comparison map unavailable')
            world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
            if not same_state(inventory(actors),definition['actorInventory']): raise RuntimeError('Relief static inventory changed')
            terrain=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==zone['id']+'_terrain')
            ignored=[a for a in actors.get_all_level_actors() if a!=terrain]
            def floor(x,z):
                hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(z*100,x*100,30000),unreal.Vector(z*100,x*100,-20000),
                    unreal.TraceTypeQuery.ECC_VISIBILITY,True,ignored,unreal.DrawDebugTrace.NONE,True)
                parts=hit.to_tuple() if hit else None
                if not parts or not parts[0] or parts[9]!=terrain: raise RuntimeError('Relief ground missing')
                return parts[5]
            witnesses=[]; grade=0
            for path in source['paths']:
                for a,b in zip(path['points'],path['points'][1:]):
                    dx,dz=b['x']-a['x'],b['z']-a['z']; length=math.hypot(dx,dz); count=max(1,math.ceil(length/2))
                    for side in (-path['width']/2,0,path['width']/2):
                        previous=None
                        for i in range(count+1):
                            p=floor(a['x']+dx*i/count-dz/max(length,1)*side,a['z']+dz*i/count+dx/max(length,1)*side)
                            witnesses.append(p.z)
                            if previous: grade=max(grade,abs(p.z-previous.z)/max(math.hypot(p.x-previous.x,p.y-previous.y),1))
                            previous=p
            witness_sets[version]=witnesses
            if grade>.22: raise RuntimeError('Relief changed full-width route grade')
            for row in zone['population']:
                actor=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==row['id'])
                if not same_state(population_actor(actor),row['savedState']): raise RuntimeError('Relief changed population bindings')
                for p in row['approach']:
                    actual=floor(p[1]/100,p[0]/100)
                    if abs(actual.z-p[2])>.1: raise RuntimeError('Relief changed population approach floor')
            capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector()); component=capture.capture_component2d
            component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1280,800,unreal.TextureRenderTargetFormat.RTF_RGBA8)
            component.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR; component.capture_every_frame=False
            component.capture_on_movement=False; component.always_persist_rendering_state=True; component.fov_angle=75; component.post_process_blend_weight=0
            if version=='before':
                main=source['paths'][0]['points']; ridge=source['paths'][1]['points'][2]; village=source['spawnPoint']
                views=[('advance',main[1],main[5]),('enclosing_ridge',main[4],dict(x=main[4]['x'],z=470)),
                    ('ridge_counterroute',ridge,dict(x=ridge['x']+400,z=ridge['z']+40)),
                    ('village_backdrop',dict(x=village['x'],z=village['z']-12),dict(x=village['x']+170,z=village['z']+400))]
                for label,p,target in views:
                    eye=floor(p['x'],p['z'])+unreal.Vector(0,0,170)
                    frozen_cameras[label]=(eye,unreal.Vector(target['z']*100,target['x']*100,eye.z))
            for phase,seconds in [('day',1200),('dusk',2250),('night',2700)]:
                if not unreal.WarZoneLightingSubsystem.preview_environment(world,zone['id'],unreal.Vector(),seconds,0): raise RuntimeError('Relief lighting unavailable')
                for label,(eye,target) in frozen_cameras.items():
                    capture.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,target),False,True)
                    for _ in range(48): unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
                    file=output/(zone['id']+'_'+label+'_'+version+'_'+phase+'.png')
                    unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(output),file.name)
                    pictures.append(dict(file=file.relative_to(ROOT).as_posix(),zone=zone['id'],view=label,version=version,phase=phase,
                        eye=[eye.x,eye.y,eye.z],target=[target.x,target.y,target.z],inspectionLighting=False,visualApproved=False))
            actors.destroy_actor(capture); unreal.WarZoneLightingSubsystem.preview_world(world,'aegis_capital',unreal.Vector())
        if len(witness_sets['before'])!=len(witness_sets['after']): raise RuntimeError('Route ground witness inventory changed')
        maximum=max(abs(a-b) for a,b in zip(witness_sets['before'],witness_sets['after']))
        if maximum>.1: raise RuntimeError('Relief changed retained route ground')
        checks.append(dict(zone=zone['id'],fullWidthRouteSamples=len(witness_sets['after']),maximumRouteGroundDifferenceCm=maximum,
            relief=zone['relief'],parentNonTerrainBindingsUnchanged=True,offRouteTraversalAccepted=False,visualApproved=False))
finally: verify_protected(ROOT,protected)
for package,digest in {**receipt['inputs']['parentPackages'],**receipt['packageHashes']}.items():
    if sha(CONTENT/(package.removeprefix('/Game/')+'.umap'))!=digest: raise RuntimeError('Relief review changed a saved map')
result=dict(signature=receipt['signature'],checks=checks,pictures=pictures,pictureDirectory=output.relative_to(ROOT).as_posix(),
    savedCandidatesUnchanged=True,routeGroundPreserved=True,playerHeightCamerasMatched=True,visualApproved=False,
    offRouteTraversalAccepted=False,walkDriveAccepted=False,gameplayAccepted=False,nodeGeometrySynchronized=False)
(DIRECTORY/'relief-review.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
unreal.log('WAR_T1_RELIEF_REVIEWED='+str(len(pictures)))
