"""Read-only native weather views and synthesized audio previews; no appearance approval."""
import io
import json
import math
from pathlib import Path
import struct
import sys
import wave
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_materials import protected_saved, verify_protected, sha, same_state
from t1_material_clone import inventory
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
receipt = json.loads((DIRECTORY/'atmosphere-latest.json').read_text())
output = DIRECTORY/'atmosphere-views'/receipt['signature'][:12]; output.mkdir(parents=True, exist_ok=True)
audio_output = DIRECTORY/'atmosphere-audio'/receipt['signature'][:12]; audio_output.mkdir(parents=True, exist_ok=True)
protected = protected_saved(ROOT)
verify_protected(ROOT, receipt['inputs']['protectedHashes'])
for file, digest in {**receipt['inputs']['tools'], **receipt['inputs']['sourceHashes'], **receipt['inputs']['parentAssetHashes'], **receipt['assetHashes']}.items():
    if sha(ROOT/file) != digest: raise RuntimeError('Atmosphere inputs or compiled actor changed')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
pictures, checks, studies = [], [], []
point = lambda p: unreal.Vector(p['z']*100, p['x']*100, 0)
try:
    for zone in receipt['zones']:
        identity = zone['id']; settings = zone['atmosphere']
        source = json.loads((DIRECTORY/(identity+'.json')).read_text())
        if not levels.load_level(zone['map']): raise RuntimeError('Atmosphere map missing')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        if not same_state(inventory(actors), zone['actorInventory']): raise RuntimeError('Atmosphere changed preserved geometry or rooms')
        effects = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.WarRegionalAtmosphere)]
        if len(effects) != 1: raise RuntimeError('Require exactly one opt-in regional atmosphere')
        effect = effects[0]
        if str(effect.zone_id) != identity or effect.weather_material.get_path_name() != settings['material']:
            raise RuntimeError('Atmosphere binding differs from authored receipt')
        for name, expected in [('village_centre', settings['villageCentre'])]:
            v = effect.get_editor_property(name)
            if not same_state([v.x, v.y, v.z], expected): raise RuntimeError('Atmosphere village placement changed')
        for name, expected in [('military_centres', settings['militaryCentres']), ('steam_sites', settings['steamSites'])]:
            if not same_state([[v.x, v.y, v.z] for v in effect.get_editor_property(name)], expected): raise RuntimeError('Atmosphere regional sites changed')
        material = effect.weather_material
        errors = unreal.MaterialEditingLibrary.recompile_material(material)
        if errors: raise RuntimeError('Weather shader failed: '+str(list(errors)))
        stats = unreal.MaterialEditingLibrary.get_statistics(material)
        statistics = {p: stats.get_editor_property(p) for p in ('num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_samplers')}
        scenery = [a for a in actors.get_all_level_actors() if 'WarT1PrototypeScenery' in map(str, a.tags)]
        def floor(p):
            hit = unreal.SystemLibrary.line_trace_single(world, p+unreal.Vector(0, 0, 20000), p-unreal.Vector(0, 0, 20000),
                unreal.TraceTypeQuery.ECC_VISIBILITY, True, scenery, unreal.DrawDebugTrace.NONE, True)
            if not hit or not hit.to_tuple()[0]: raise RuntimeError('Missing weather camera ground')
            return hit.to_tuple()[5]
        capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
        component = capture.capture_component2d
        component.texture_target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 800, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
        component.capture_every_frame = False; component.capture_on_movement = False
        component.always_persist_rendering_state = True; component.fov_angle = 75; component.post_process_blend_weight = 0
        main = source['paths'][0]['points']; village = source['spawnPoint']
        modules = json.loads((DIRECTORY/(identity+'_modules.json')).read_text())
        closest = min(modules['modules'], key=lambda p: math.hypot(p['entry']['x']-village['x'], p['entry']['z']-village['z']))
        views = [('advance', floor(point(main[1]))+unreal.Vector(0, 0, 170), floor(point(main[5]))+unreal.Vector(0, 0, 170)),
            ('village', floor(point(dict(x=village['x'], z=village['z']-12)))+unreal.Vector(0, 0, 170), floor(point(closest['entry']))+unreal.Vector(0, 0, 170))]
        if identity == 'sunmeadow_march':
            views.append(('ridge', floor(point(source['paths'][1]['points'][2]))+unreal.Vector(0, 0, 170), floor(point(main[4]))+unreal.Vector(0, 0, 170)))
        else:
            for label, xyz in [('basalt_steam', settings['steamSites'][0]), ('mineral_steam', settings['steamSites'][-1])]:
                site = unreal.Vector(*xyz); target = site+unreal.Vector(0, 0, 230); eye = None
                for distance in (1800, 2600, 4000):
                    for angle in range(16):
                        candidate = floor(site+unreal.Vector(math.cos(angle*math.pi/8)*distance,
                            math.sin(angle*math.pi/8)*distance, 0))+unreal.Vector(0, 0, 170)
                        inside_model = False
                        for model in scenery:
                            centre, extent = model.get_actor_bounds(False)
                            if abs(candidate.x-centre.x) < extent.x and abs(candidate.y-centre.y) < extent.y and abs(candidate.z-centre.z) < extent.z:
                                inside_model = True; break
                        if inside_model: continue
                        hit = unreal.SystemLibrary.line_trace_single(world, candidate, target,
                            unreal.TraceTypeQuery.ECC_VISIBILITY, True, scenery, unreal.DrawDebugTrace.NONE, True)
                        if not hit or not hit.to_tuple()[0]: eye = candidate; break
                    if eye is not None: break
                if eye is None: raise RuntimeError('No unobstructed grounded vent camera')
                views.append((label, eye, target))
        def picture(label, eye, target, phase, seconds, strength, inside=False):
            rotation = unreal.MathLibrary.find_look_at_rotation(eye, target)
            capture.set_actor_location_and_rotation(eye, rotation, False, True)
            forward = unreal.MathLibrary.get_forward_vector(rotation)
            for frame in range(16):
                if not effect.preview_frame(eye, forward, seconds+frame/60, strength, inside): raise RuntimeError('Weather editor preview refused')
                unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
            state = json.loads(effect.describe_local_state())
            if state['collisionEnabled'] or state['replicated'] or not 0 <= state['particles'] <= 192 or inside and state['particles'] != 0:
                raise RuntimeError('Cosmetic weather invariants failed')
            name = identity+'_'+label+'_'+phase+'.png'
            unreal.RenderingLibrary.export_render_target(world, component.texture_target, str(output), name)
            file = output/name
            if not file.exists() or file.stat().st_size < 10000: raise RuntimeError('Fresh weather capture absent')
            pictures.append(dict(zone=identity, view=label, phase=phase, seconds=seconds, weatherStrength=strength,
                particles=state['particles'], sheltered=inside, file=file.relative_to(ROOT).as_posix(), sha256=sha(file), visualApproved=False))
        for phase, seconds, strength in [('dawn', 150, .28), ('day', 1200, .06), ('dusk', 2250, .28), ('night', 2700, .28), ('strong_weather', 1200, .8)]:
            if not unreal.WarZoneLightingSubsystem.preview_environment(world, identity, unreal.Vector(), seconds, strength): raise RuntimeError('Weather lighting preview failed')
            for _ in range(48): unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
            for label, eye, target in views: picture(label, eye, target, phase, seconds, strength)
            if phase == 'strong_weather':
                for home in zone['homes']:
                    for view in ('exterior', 'interior'):
                        picture(home['id'].removeprefix(identity+'_')+'_'+view, unreal.Vector(*home[view+'Eye']),
                            unreal.Vector(*home[view+'Target']), phase, seconds, strength, view == 'interior')
        unreal.WarZoneLightingSubsystem.preview_environment(world, identity, unreal.Vector(), 2700, .8)
        picture(*views[1], 'night_strong_weather', 2700, .8)
        for label, village_mix, frontage_mix, day, strength, inside in [('countryside', 0, 0, 1, .06, False),
            ('village_work', 1, 0, 1, .06, False), ('military_frontage', 0, 1, 1, .28, False),
            ('night', 1, 0, 0, .06, False), ('strong_weather', 0, 0, 1, .8, False), ('sheltered_storm', 1, 0, 1, .8, True)]:
            data = bytes(unreal.WarRegionalAtmosphere.audio_study(identity, village_mix, frontage_mix, day, strength, inside))
            with wave.open(io.BytesIO(data), 'rb') as wav:
                if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()) != (1, 2, 24000, 192000):
                    raise RuntimeError('Synthesized WAV format differs')
                samples = struct.unpack('<192000h', wav.readframes(192000))
            peak = max(abs(v) for v in samples)/32768; rms = math.sqrt(sum(v*v for v in samples)/len(samples))/32768
            if not 0 < rms < .2 or peak > .6: raise RuntimeError('Synthesized sound level invalid')
            file = audio_output/(identity+'_'+label+'.wav'); file.write_bytes(data)
            studies.append(dict(zone=identity, study=label, file=file.relative_to(ROOT).as_posix(), sha256=sha(file),
                seconds=8, peak=peak, rms=rms, provenance='original-native-synthesis', hardwarePlaybackVerified=False, audioApproved=False))
        actors.destroy_actor(capture)
        if not unreal.WarZoneLightingSubsystem.preview_world(world, 'aegis_capital', unreal.Vector()): raise RuntimeError('Capital restoration failed')
        checks.append(dict(zone=identity, geometryPreserved=True, shaderStatistics=statistics, steamSites=len(settings['steamSites']),
            collision=False, replicated=False, visualApproved=False, audioApproved=False))
finally:
    verify_protected(ROOT, protected)
result = dict(signature=receipt['signature'], zones=checks, pictures=pictures, audioStudies=studies,
    pictureDirectory=output.relative_to(ROOT).as_posix(), savedCandidatesUnchanged=True,
    visualApproved=False, audioApproved=False, networkSynchronizationAccepted=False, performanceAccepted=False)
(DIRECTORY/'atmosphere-review.json').write_text(json.dumps(result, indent=2)+'\n')
unreal.log('WAR_T1_ATMOSPHERE_REVIEWED='+str(len(pictures))+' AUDIO='+str(len(studies)))
