"""Cold-load retained population, verify exact bindings/access and render player-height views."""
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from t1_population_native import population_actor, GroundReview
from t1_material_clone import inventory
from t1_materials import protected_saved, verify_protected, sha, same_state

DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
receipt = json.loads((DIRECTORY/'population-latest.json').read_text(encoding='utf-8'))
parent = json.loads((DIRECTORY/'ceilings-latest.json').read_text(encoding='utf-8'))
if receipt.get('study') != 'retained-population' or receipt['inputs']['parentCeilingSignature'] != parent['signature']:
    raise RuntimeError('Population review requires its frozen ceiling parent')
if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower(): raise RuntimeError('Population pictures require rendering')
protected = protected_saved(ROOT); verify_protected(ROOT,receipt['inputs']['protectedHashes'])
for file,digest in {**receipt['inputs']['sourceHashes'],**receipt['inputs']['tools'],**receipt['inputs']['parentAssetHashes'],**receipt['assetHashes']}.items():
    if sha(ROOT/file)!=digest: raise RuntimeError('Population input, binary or asset changed')
for package,digest in receipt['inputs']['dependencyHashes'].items():
    if sha(ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.uasset'))!=digest: raise RuntimeError('Retained native dependency changed')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
output = DIRECTORY/'population-views'/receipt['signature'][:12]; output.mkdir(parents=True,exist_ok=True)
checks=[]; pictures=[]
try:
    for zone in receipt['zones']:
        if not levels.load_level(zone['map']): raise RuntimeError('Population saved candidate unavailable')
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        states=inventory(actors)
        if not same_state(states,zone['actorInventory']): raise RuntimeError('Saved population static inventory changed')
        parent_zone=next(z for z in parent['zones'] if z['id']==zone['id'])
        ids={r['id'] for r in zone['population']}
        if not same_state({k:v for k,v in states.items() if k not in ids},parent_zone['actorInventory']):
            raise RuntimeError('Population changed a parent house, scenery, light or room')
        population=[a for a in actors.get_all_level_actors() if 'WarT1CandidatePopulation' in map(str,a.tags)]
        if {a.get_actor_label() for a in population}!=ids: raise RuntimeError('Saved population identity inventory changed')
        source=json.loads((DIRECTORY/(zone['id']+'.json')).read_text(encoding='utf-8'))
        ground=GroundReview(world,actors,zone['id'],source['spatial']['playableOutline'])
        cameras={}
        for row in zone['population']:
            actor=next(a for a in population if a.get_actor_label()==row['id'])
            actual=population_actor(actor)
            if not same_state(actual,row['savedState']): raise RuntimeError('Retained native NPC/resource binding changed: '+row['id'])
            if row['kind']=='npc':
                identity=actual['identity']; component=actor.get_component_by_class(unreal.SkeletalMeshComponent)
                if unreal.WarNpcEquipmentLibrary.apply(component,identity['character_profile'],identity['npc_id'],identity['city_role'])!='':
                    raise RuntimeError('Cold-loaded retained NPC equipment failed')
                if not same_state(population_actor(actor)['weapons'],row['source']['weapons']): raise RuntimeError('Equipment restore duplicates or mismatches')
            else: component=actor.static_mesh_component
            g=ground.ground(row['ground']); centre,extent,_=unreal.SystemLibrary.get_component_bounds(component)
            if g is None or abs(centre.z-extent.z-g[2]-2)>.1: raise RuntimeError('Retained actor lost measured ground support')
            approach=[]
            # Re-sample every authored leg with normal capsule geometry; no
            # scenery is ignored by either foot support or capsule sweeps.
            for a,b in zip(row['approach'],row['approach'][1:]):
                leg=ground.approach(a,b)
                if not leg: raise RuntimeError('Cold-loaded population approach is blocked: '+row['id'])
                approach.extend(leg if not approach else leg[1:])
            if not approach: raise RuntimeError('Population has no connected approach')
            checks.append(dict(zone=zone['id'],id=row['id'],kind=row['kind'],rulesUnchanged=True,exactNativeBinding=True,
                terrainOnlyGround=True,boundsGroundGapCm=centre.z-extent.z-g[2],approachSamples=len(approach),capsuleClear=True,
                capsuleRadiusCm=42,capsuleHalfHeightCm=96,connectedRoad=row['connectedRoad'],adjustmentCm=row['adjustmentCm'],gameplayAccepted=False))
            target=unreal.Vector(g[0],g[1],g[2]+(112 if row['kind']=='npc' else 35))
            eye=None
            for point in reversed(approach[:-1]):
                delta=unreal.Vector(point[0]-g[0],point[1]-g[1],0)
                if delta.length()<300: continue
                candidate=unreal.Vector(point[0],point[1],point[2]+160)
                hit=unreal.SystemLibrary.line_trace_single(world,target,candidate,unreal.TraceTypeQuery.ECC_VISIBILITY,
                    True,[actor],unreal.DrawDebugTrace.NONE,True)
                parts=hit.to_tuple() if hit else None
                if not parts or not parts[0]: eye=candidate; break
            if eye is None: raise RuntimeError('No clear player-height population camera')
            cameras[row['id']]=(eye,target)
            # Nameplates are supplied at BeginPlay; hide their editor default
            # text for these transient close-ups. Live pictures retain them.
            if row['kind']=='npc': actor.get_component_by_class(unreal.TextRenderComponent).set_visibility(False)
        capture=actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector()); component=capture.capture_component2d
        component.texture_target=unreal.RenderingLibrary.create_render_target2d(world,1280,800,unreal.TextureRenderTargetFormat.RTF_RGBA8)
        component.capture_source=unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
        component.capture_every_frame=False; component.capture_on_movement=False; component.always_persist_rendering_state=True
        component.fov_angle=60; component.post_process_blend_weight=0
        for phase,seconds in [('dawn',150),('day',1200),('dusk',2250),('night',2700)]:
            if not unreal.WarZoneLightingSubsystem.preview_environment(world,zone['id'],unreal.Vector(),seconds,0):
                raise RuntimeError('Population regional clock preview unavailable')
            for row in zone['population']:
                eye,target=cameras[row['id']]
                capture.set_actor_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,target),False,True)
                for _ in range(64): unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
                file=output/(row['id']+'_'+phase+'.png')
                unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(output),file.name)
                pictures.append(dict(file=file.relative_to(ROOT).as_posix(),zone=zone['id'],id=row['id'],kind=row['kind'],phase=phase,
                    eye=[eye.x,eye.y,eye.z],target=[target.x,target.y,target.z],nameplateHidden=row['kind']=='npc',inspectionLighting=False,visualApproved=False))
        actors.destroy_actor(capture); unreal.WarZoneLightingSubsystem.preview_world(world,'aegis_capital',unreal.Vector())
finally: verify_protected(ROOT,protected)
for package,digest in {**receipt['inputs']['parentPackages'],**receipt['packageHashes']}.items():
    if sha(ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap'))!=digest: raise RuntimeError('Population review changed a saved map')
result=dict(signature=receipt['signature'],checks=checks,pictures=pictures,pictureDirectory=output.relative_to(ROOT).as_posix(),
    sourceRulesUnchanged=True,exactBindingsVerified=len(checks)==sum(len(z['population']) for z in receipt['zones']),capsuleClear=all(c['capsuleClear'] for c in checks),
    savedCandidatesUnchanged=True,parentActorsUnchanged=True,visualApproved=False,gameplayAccepted=False,
    npcServicesVerified=False,nativeResourceTransactionsVerified=False,nodeGeometrySynchronized=False,walkDriveAccepted=False)
(DIRECTORY/'population-review.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
unreal.log('WAR_T1_POPULATION_REVIEWED='+str(len(checks)))
