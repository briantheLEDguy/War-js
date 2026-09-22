"""Fresh saved-scene and player-height visual evidence for the native raider placements."""
import hashlib
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_actor_state import snapshot

directory = ROOT/'artifacts/unreal/world-portals'
build = json.loads((directory/'build.json').read_text())
placement = json.loads((directory/'enemy-placement.json').read_text())
manifest = json.loads((directory/'zone-manifest.json').read_text())
package = ROOT/'unreal/AegisWar/Content'/(placement['package'].removeprefix('/Game/')+'.umap')
before = hashlib.sha256(package.read_bytes()).hexdigest()
if before != manifest['packageHashes'][placement['package']]: raise RuntimeError('Owner changed the saved zone')
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(build['map']): raise RuntimeError('Main map unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
anchor = next(a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarZoneAnchor)
              and str(a.get_editor_property('zone_id'))=='sunmeadow_march')
if not unreal.WarZoneLightingSubsystem.preview_world(world,'sunmeadow_march',anchor.get_editor_property('zone_origin')):
    raise RuntimeError('Zone lighting unavailable')
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector())
component = capture.capture_component2d
component.texture_target = unreal.RenderingLibrary.create_render_target2d(world,1280,800,unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
component.capture_every_frame = False; component.capture_on_movement = False
component.always_persist_rendering_state = True; component.fov_angle = 65; component.post_process_blend_weight = 0
results = []
for record in placement['actors']:
    matches = [a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarEnemy) and str(a.get_editor_property('enemy_id'))==record['id']]
    if len(matches)!=1: raise RuntimeError('Missing or duplicate enemy')
    actor = matches[0]
    current = snapshot(actor)
    current.update(zone=str(actor.get_editor_property('zone_id')),enemy=str(actor.get_editor_property('enemy_id')),
                   visual=actor.get_editor_property('visual').get_path_name())
    if current!=record['state']: raise RuntimeError('Enemy placement changed')
    mesh = actor.get_component_by_class(unreal.SkeletalMeshComponent)
    unreal.WarImportLibrary.prepare_preview_frame(mesh)
    center,extent,_ = unreal.SystemLibrary.get_component_bounds(mesh)
    feet = center-unreal.Vector(0,0,extent.z)
    hit = unreal.SystemLibrary.line_trace_single(world,feet+unreal.Vector(0,0,30),feet-unreal.Vector(0,0,30),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[actor],unreal.DrawDebugTrace.NONE,True)
    if not hit or not hit.to_tuple()[0] or abs(feet.z-hit.to_tuple()[5].z)>10: raise RuntimeError('Enemy feet are not grounded')
    camera = feet+unreal.Vector(450,-360,170)
    capture.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,center),False,True)
    for _ in range(8):
        unreal.WarImportLibrary.prepare_world_preview_frame(world); component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(directory),record['id']+'.png')
    results.append(record['id'])
if hashlib.sha256(package.read_bytes()).hexdigest()!=before: raise RuntimeError('Rendering changed saved zone')
(directory/'enemy-render-verification.json').write_text(json.dumps({'enemies':results,'zonePackageSha256':before,
    'grounded':True,'visualApproved':False},indent=2)+'\n')
unreal.log('WAR_ENEMY_RENDER_VERIFIED='+str(len(results)))
