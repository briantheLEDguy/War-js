"""Verify saved dummy identities and capture the six exact models at player height."""
import hashlib
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from world_actor_state import snapshot

directory = ROOT/'artifacts/unreal/capital-dummies'
build = json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
placement = json.loads((directory/'placement.json').read_text())
manifest = json.loads((ROOT/'artifacts/unreal/world-portals/zone-manifest.json').read_text())
packages = {z['levels']['generated'] for z in manifest['zones'] if z['id'] in ('aegis_capital','riftspire_capital')}
files = {p:ROOT/'unreal/AegisWar/Content'/(p.removeprefix('/Game/')+'.umap') for p in packages}
before = {p:hashlib.sha256(f.read_bytes()).hexdigest() for p,f in files.items()}
if any(manifest['packageHashes'][p]!=h for p,h in before.items()): raise RuntimeError('Capital package changed')
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(build['map']): raise RuntimeError('Main map unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = actors.get_all_level_actors()
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
component = capture.capture_component2d
component.texture_target = unreal.RenderingLibrary.create_render_target2d(world,1280,800,unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
component.capture_every_frame = False; component.capture_on_movement = False
component.always_persist_rendering_state = True; component.fov_angle = 65; component.post_process_blend_weight = 0
for row in placement['actors']:
    matches = [a for a in all_actors if isinstance(a,unreal.WarEnemy)
               and str(a.get_editor_property('zone_id'))==row['zone'] and str(a.get_editor_property('enemy_id'))==row['id']]
    if len(matches)!=1 or snapshot(matches[0])!=row['state']: raise RuntimeError('Saved target changed: '+row['id'])
    actor = matches[0]; mesh = actor.get_editor_property('training_mesh')
    center,extent,_ = unreal.SystemLibrary.get_component_bounds(mesh)
    feet = center-unreal.Vector(0,0,extent.z)
    hit = unreal.SystemLibrary.line_trace_single(world,feet+unreal.Vector(0,0,30),feet-unreal.Vector(0,0,30),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[actor],unreal.DrawDebugTrace.NONE,True)
    if not hit or not hit.to_tuple()[0] or abs(feet.z-hit.to_tuple()[5].z)>10: raise RuntimeError('Target is not grounded')
    anchor = next(a for a in all_actors if isinstance(a,unreal.WarZoneAnchor) and str(a.get_editor_property('zone_id'))==row['zone'])
    if not unreal.WarZoneLightingSubsystem.preview_world(world,row['zone'],anchor.get_editor_property('zone_origin')):
        raise RuntimeError('Capital lighting unavailable')
    camera = feet+unreal.Vector(420,-260,170)
    capture.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,center),False,True)
    for _ in range(8):
        unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(directory),row['id']+'.png')
if any(hashlib.sha256(f.read_bytes()).hexdigest()!=before[p] for p,f in files.items()): raise RuntimeError('Capture modified saved world')
(directory/'render-verification.json').write_text(json.dumps({'targets':6,'grounded':True,'packages':before,'visualApproved':False},indent=2)+'\n')
unreal.log('WAR_CAPITAL_DUMMIES_RENDERED=6')
