"""Measure native furnished-home collision and capture unchanged private studies."""
import hashlib
import json
import math
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
receipt = json.loads((DIRECTORY/'homes-latest.json').read_text())
output = DIRECTORY/'home-views'/receipt['signature'][:12]
output.mkdir(parents=True, exist_ok=True)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
checks = []
for zone in receipt['zones']:
    if not levels.load_level(zone['map']):
        raise RuntimeError('Saved home study unavailable')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    unreal.WarImportLibrary.prepare_world_preview_frame(world)
    homes = [a for a in actors.get_all_level_actors() if 'WarT1FurnishedHomeStudy' in map(str, a.tags)]
    if len(homes) != 2:
        raise RuntimeError('Saved furnished-home inventory differs')
    capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
    component = capture.capture_component2d
    component.texture_target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 800, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    component.capture_every_frame = False
    component.capture_on_movement = False
    component.always_persist_rendering_state = True
    component.fov_angle = 75
    component.post_process_blend_weight = 0
    for home in zone['homes']:
        samples, blockers, floors, steps = 0, [], [], 0
        scenery = [a for a in actors.get_all_level_actors() if 'WarT1PrototypeScenery' in map(str, a.tags)]
        for segment, (a, b) in enumerate(zip(home['route'], home['route'][1:])):
            delta = [b[i]-a[i] for i in range(3)]
            count = max(1, math.ceil(math.hypot(delta[0], delta[1])/50))
            previous = None
            for i in range(count+1):
                expected = unreal.Vector(*(a[k]+delta[k]*i/count for k in range(3)))
                # Limit the trace to the expected floor, so roofs/furniture never
                # masquerade as an accessible ground floor.
                community_path = segment < home['approachPoints']-1
                hit = unreal.SystemLibrary.line_trace_single(world,
                    expected+unreal.Vector(0, 0, 20000 if community_path else 40),
                    expected-unreal.Vector(0, 0, 20000 if community_path else 150),
                    unreal.TraceTypeQuery.ECC_VISIBILITY, True, scenery if community_path else [], unreal.DrawDebugTrace.NONE, True)
                parts = hit.to_tuple() if hit else None
                if not parts or not parts[0] or parts[7].z < .71:
                    blockers.append(dict(reason='missing_or_unwalkable_floor', point=[expected.x, expected.y, expected.z]))
                    previous = None
                    continue
                ground, normal = parts[5], parts[7]
                # A centreline ray misses a porch edge under the rounded foot.
                # Sweep the native 42 cm foot sphere to find its supported centre.
                foot = unreal.SystemLibrary.capsule_trace_single(world, ground+unreal.Vector(0, 0, 90), ground-unreal.Vector(0, 0, 45), 42, 42,
                    unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
                samples += 1
                support = foot.to_tuple() if foot else None
                if not support or not support[0] or support[7].z < .71:
                    blockers.append(dict(reason='unsupported_capsule_foot', point=[ground.x, ground.y, ground.z]))
                    previous = None
                    continue
                center = support[4]+unreal.Vector(0, 0, 96-42+3)
                floors.append([ground.x, ground.y, ground.z])
                if previous is None:
                    previous = center
                for direction, start, end in [('forward', previous, center), ('reverse', center, previous)]:
                    obstruction = unreal.SystemLibrary.capsule_trace_single(world, start, end+unreal.Vector(0, 0, .1), 42, 96,
                        unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
                    witness = obstruction.to_tuple() if obstruction else None
                    if witness and witness[0]:
                        step_clear = False
                        for lift in [10, 20, 30, 45]:
                            if abs(end.z-start.z) > 45:
                                break
                            top = max(start.z, end.z)+lift
                            raised_start = unreal.Vector(start.x, start.y, top)
                            raised_end = unreal.Vector(end.x, end.y, top)
                            step_clear = True
                            for p, q in [(start, raised_start), (raised_start, raised_end), (raised_end, end)]:
                                step_hit = unreal.SystemLibrary.capsule_trace_single(world, p, q, 42, 96,
                                    unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
                                samples += 1
                                step_witness = step_hit.to_tuple() if step_hit else None
                                if step_witness and step_witness[0]:
                                    step_clear = False
                                    break
                            if step_clear:
                                steps += 1
                                break
                        if not step_clear:
                            blockers.append(dict(reason='capsule_obstruction', direction=direction,
                                point=[ground.x, ground.y, ground.z], blocker=witness[9].get_actor_label() if witness[9] else 'unknown'))
                    samples += 1
                previous = center
        checks.append(dict(zone=zone['id'], id=home['id'], capsuleSweeps=samples, floorSamples=len(floors),
            blockers=blockers, capsuleClear=not blockers, capsuleRadiusCm=42, capsuleHalfHeightCm=96,
            maxStepHeightCm=45, sweptStepTransitions=steps,
            walkingAccepted=False, cameraAccepted=False, visualApproved=False))
    phase_lights=[]
    for phase, seconds in [('day', 1200), ('dusk', 2250), ('night', 2700)]:
        if not unreal.WarZoneLightingSubsystem.preview_environment(world, zone['id'], unreal.Vector(), seconds, 0):
            raise RuntimeError('Home atmosphere unavailable')
        for _ in range(64):
            unreal.WarImportLibrary.prepare_world_preview_frame(world)
            component.capture_scene()
        phase_lights.append(dict(zone=zone['id'], phase=phase, lights=[dict(label=a.get_actor_label(),
            intensity=a.get_component_by_class(unreal.PointLightComponent).get_editor_property('intensity'),
            visible=a.get_component_by_class(unreal.PointLightComponent).is_visible())
            for a in actors.get_all_level_actors() if isinstance(a, unreal.WarPracticalLight) and 'WarT1InteriorPractical' in map(str,a.tags)]))
        for home in zone['homes']:
            for view in ['exterior', 'interior']:
                eye, target = unreal.Vector(*home[view+'Eye']), unreal.Vector(*home[view+'Target'])
                capture.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, target), False, True)
                for _ in range(12):
                    unreal.WarImportLibrary.prepare_world_preview_frame(world)
                    component.capture_scene()
                unreal.RenderingLibrary.export_render_target(world, component.texture_target, str(output), home['id']+'_'+view+'_'+phase+'.png')
    actors.destroy_actor(capture)
    unreal.WarZoneLightingSubsystem.preview_world(world, 'aegis_capital', unreal.Vector())
    for check in checks:
        if check['zone']==zone['id']:check['phaseLights']=phase_lights
for package, digest in {**receipt['inputs']['parentPackages'], **receipt['packageHashes']}.items():
    file = ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')
    if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Home review changed a saved map')
result = dict(signature=receipt['signature'], parentPlanSha256=receipt['inputs']['parentPlanSha256'], homes=checks,
    pictureDirectory=output.relative_to(ROOT).as_posix(), savedCandidatesUnchanged=True,
    capsuleClear=all(p['capsuleClear'] for p in checks), walkingAccepted=False, furnishedHomesAccepted=0, visualApproved=False)
(DIRECTORY/'home-review.json').write_text(json.dumps(result, indent=2)+'\n')
unreal.log('WAR_T1_HOMES_REVIEWED=4')
if not result['capsuleClear']:
    raise RuntimeError('Home collision review failed; see home-review.json')
unreal.log('WAR_T1_HOME_CAPSULE_CLEAR=4')
