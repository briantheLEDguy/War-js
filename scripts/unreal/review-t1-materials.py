"""Read-only native material, route-ground and player-height review of fresh T1 studies."""
import json
import math
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_materials import protected_saved, verify_protected, sha, terrain_recipe, same_state
from t1_material_clone import inventory
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
receipt = json.loads((DIRECTORY/'materials-latest.json').read_text())
plan = json.loads((DIRECTORY/'plan.json').read_text())
output = DIRECTORY/'material-views'/receipt['signature'][:12]
output.mkdir(parents=True, exist_ok=True)
protected = protected_saved(ROOT)
verify_protected(ROOT, receipt['inputs']['protectedHashes'])
for file, digest in receipt['assetHashes'].items():
    if sha(ROOT/file) != digest: raise RuntimeError('Preserve edited material assets')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
checks, pictures = [], []
def point(p): return unreal.Vector(p['z']*100, p['x']*100, 0)
try:
    for zone in receipt['zones']:
        identity = zone['id']
        if terrain_recipe(ROOT, identity) != receipt['inputs']['recipes'][identity]: raise RuntimeError('Material provenance changed')
        source_file = DIRECTORY/(identity+'.json')
        if sha(source_file) != plan['candidateHashes'][identity]: raise RuntimeError('Material geometry source changed')
        source = json.loads(source_file.read_text())
        if not levels.load_level(zone['map']): raise RuntimeError('Material candidate unavailable')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world)
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        if not same_state(inventory(actors), zone['actorInventory']): raise RuntimeError('Saved material clone differs from frozen geometry/rooms/lights')
        scenery = [a for a in actors.get_all_level_actors() if 'WarT1PrototypeScenery' in map(str, a.tags)]
        def floor(p):
            hit = unreal.SystemLibrary.line_trace_single(world, p+unreal.Vector(0, 0, 20000), p-unreal.Vector(0, 0, 20000),
                unreal.TraceTypeQuery.ECC_VISIBILITY, True, scenery, unreal.DrawDebugTrace.NONE, True)
            if not hit or not hit.to_tuple()[0]: raise RuntimeError('Missing native ground')
            return hit.to_tuple()[5]
        samples, grade = 0, 0
        for path in source['paths']:
            for a, b in zip(path['points'], path['points'][1:]):
                start, end = point(a), point(b); delta = end-start; distance = delta.length()
                normal = unreal.Vector(-delta.y, delta.x, 0)/max(distance, 1)
                for side in (-path['width']*50, 0, path['width']*50):
                    previous = None; count = max(1, math.ceil(distance/200))
                    for i in range(count+1):
                        p = floor(start+delta*(i/count)+normal*side); samples += 1
                        if previous is not None: grade = max(grade, abs(p.z-previous.z)/max(math.hypot(p.x-previous.x, p.y-previous.y), 1))
                        previous = p
        if grade > .22: raise RuntimeError('Material study changed route ground support')
        capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
        component = capture.capture_component2d
        component.texture_target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 800, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
        component.capture_every_frame = False; component.capture_on_movement = False
        component.always_persist_rendering_state = True; component.fov_angle = 75; component.post_process_blend_weight = 0
        main = source['paths'][0]['points']; village = source['spawnPoint']
        modules = json.loads((DIRECTORY/(identity+'_modules.json')).read_text())
        closest = min(modules['modules'], key=lambda p: math.hypot(p['entry']['x']-village['x'], p['entry']['z']-village['z']))
        views = [('advance', main[1], main[5]), ('village', dict(x=village['x'], z=village['z']-12), closest['entry']),
                 ('ridge', source['paths'][1]['points'][2], main[4]),
                 ('road_detail', main[1], dict(x=main[1]['x']+2, z=main[1]['z']+2))]
        scenes = json.loads((DIRECTORY/(identity+'_scenes.json')).read_text())
        for label, scene in zip(('working_outskirts', 'regional_cover'), scenes[:2]):
            placements = scene['placements']
            if not placements: continue
            target = dict(x=sum(p['x'] for p in placements)/len(placements), z=sum(p['z'] for p in placements)/len(placements))
            for index in range(16):
                candidate = dict(x=target['x']+math.cos(index*math.pi/8)*48, z=target['z']+math.sin(index*math.pi/8)*48)
                if all(math.hypot(candidate['x']-p['x'], candidate['z']-p['z']) > math.hypot(p['reservation']['width'], p['reservation']['depth'])/2+2 for p in placements):
                    views.append((label, candidate, target)); break
            else: raise RuntimeError('No clear scenery camera')
        statistics = {}
        for role, row in zone['materials'].items():
            material = unreal.load_asset(row['asset'])
            errors = unreal.MaterialEditingLibrary.recompile_material(material)
            if errors: raise RuntimeError('Material shader failed: '+str(list(errors)))
            stats = unreal.MaterialEditingLibrary.get_statistics(material)
            statistics[role] = {p: stats.get_editor_property(p) for p in ('num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers', 'num_pixel_texture_samples')}
            if statistics[role]['num_pixel_shader_instructions'] <= 0 or statistics[role]['num_samplers'] < 2:
                raise RuntimeError('Missing compiled native texture shader: '+role)
        for phase, seconds in [('day', 1200), ('dusk', 2250), ('night', 2700)]:
            if not unreal.WarZoneLightingSubsystem.preview_environment(world, identity, unreal.Vector(), seconds, 0): raise RuntimeError('Regional material atmosphere failed')
            for _ in range(64): unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
            def picture(label, eye, target):
                capture.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, target), False, True)
                for _ in range(12): unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
                name = identity+'_'+label+'_'+phase+'.png'
                unreal.RenderingLibrary.export_render_target(world, component.texture_target, str(output), name)
                file = output/name
                if not file.exists() or file.stat().st_size < 10000: raise RuntimeError('Fresh native material capture absent')
                pictures.append(dict(zone=identity, view=label, phase=phase, file=file.relative_to(ROOT).as_posix(), sha256=sha(file), visualApproved=False))
            for label, location, target in views:
                eye = floor(point(location))+unreal.Vector(0, 0, 170)
                look = floor(point(target))+unreal.Vector(0, 0, 35 if label == 'road_detail' else 170)
                picture(label, eye, look)
            if phase != 'dusk':
                for home in zone['homes']:
                    for view in ('exterior', 'interior'):
                        picture(home['id'].removeprefix(identity+'_')+'_'+view, unreal.Vector(*home[view+'Eye']), unreal.Vector(*home[view+'Target']))
        actors.destroy_actor(capture)
        if not unreal.WarZoneLightingSubsystem.preview_world(world, 'aegis_capital', unreal.Vector()): raise RuntimeError('Capital restoration failed')
        checks.append(dict(zone=identity, fullWidthGroundSamples=samples, maximumSampledGrade=grade, geometryPreserved=True,
            roomLightingPreserved=True, shaderStatistics=statistics, visualApproved=False, walkDriveAccepted=False))
finally:
    verify_protected(ROOT, protected)
result = dict(signature=receipt['signature'], zones=checks, pictures=pictures,
    pictureDirectory=output.relative_to(ROOT).as_posix(), savedCandidatesUnchanged=True, visualApproved=False,
    performanceAccepted=False, drivingAccepted=False, cameraAccepted=False, gameplayAccepted=False)
(DIRECTORY/'material-review.json').write_text(json.dumps(result, indent=2)+'\n')
unreal.log('WAR_T1_MATERIALS_REVIEWED='+str(len(pictures)))
