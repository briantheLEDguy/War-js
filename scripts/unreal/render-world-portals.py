"""Inspect saved portal labels and capture the main campaign without saving changes."""
import json
import math
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT / 'artifacts/unreal/world-portals'
receipt = json.loads((directory / 'build.json').read_text())
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt['map']):
    raise RuntimeError('Main campaign map is missing')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
unreal.WarImportLibrary.prepare_world_preview_frame(world)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
anchors={str(a.get_editor_property('zone_id')):a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarZoneAnchor)}


def atmosphere(zone):
    if not unreal.WarZoneLightingSubsystem.preview_world(world,zone,anchors[zone].get_editor_property('zone_origin')):
        raise RuntimeError('Zone lighting unavailable: '+zone)

portals = {str(actor.get_editor_property('route_id')): actor for actor in actors.get_all_level_actors() if isinstance(actor, unreal.WarZonePortal)}
for key in receipt['portals']:
    actor = portals[key]
    label = actor.get_component_by_class(unreal.TextRenderComponent)
    expected = str(actor.get_editor_property('destination_label'))
    if expected not in str(label.get_editor_property('text')):
        raise RuntimeError('Saved portal label is stale: ' + key)
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
component = capture.capture_component2d
component.texture_target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 800, unreal.TextureRenderTargetFormat.RTF_RGBA8)
component.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
component.capture_every_frame = False
component.capture_on_movement = False
component.always_persist_rendering_state = True
component.fov_angle = 65
component.post_process_blend_weight = 0
plan = json.loads((directory / 'plan.json').read_text())
for zone in ['brightfen_approach', 'sunmeadow_march', 'cinderfen_outskirts', 'riftspire_capital']:
    definition = next((row for row in plan['zones'] if row['id'] == zone), None)
    if not definition:
        continue
    anchor = next(actor for actor in actors.get_all_level_actors() if isinstance(actor, unreal.WarZoneAnchor) and str(actor.get_editor_property('zone_id')) == zone)
    atmosphere(zone)
    center = anchor.get_actor_location()
    camera = center + unreal.Vector(8500, 6000, 6000)
    capture.set_actor_location_and_rotation(camera, unreal.MathLibrary.find_look_at_rotation(camera, center), False, True)
    for _ in range(5):
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, component.texture_target, str(directory), zone + '.png')
unreal.log('WAR_PORTAL_LABELS_VERIFIED=' + str(len(portals)))
npcs=[]
for actor in actors.get_all_level_actors():
    if 'WarCampaignNpc' not in [str(tag) for tag in actor.tags]: continue
    mesh=actor.get_component_by_class(unreal.SkeletalMeshComponent)
    if not mesh or not mesh.get_skeletal_mesh_asset(): raise RuntimeError('Missing campaign character mesh')
    unreal.WarImportLibrary.prepare_preview_frame(mesh)
    center,extent,_=unreal.SystemLibrary.get_component_bounds(mesh)
    if not 100<extent.z*2<240: raise RuntimeError('Invalid saved character height')
    npc_id=str(actor.get_editor_property('npc_id'))
    placement=next(row for row in receipt['gameplay'] if row['id']==npc_id)
    atmosphere(placement['zone'])
    source=json.loads((ROOT/'public/assets/maps'/(placement['zone']+'.json')).read_text())
    source_npc=next(row for row in source['npcs'] if row['id']==npc_id)
    if isinstance(actor,unreal.WarCityNpc):
        delta=(actor.get_actor_rotation().yaw-(source_npc.get('rotY',0)*180/math.pi-90)+180)%360-180
        if abs(delta)>0.1: raise RuntimeError('Source NPC facing changed: '+npc_id)
    feet=unreal.Vector(center.x,center.y,center.z-extent.z)
    hit=unreal.SystemLibrary.line_trace_single(world,feet+unreal.Vector(0,0,50),feet-unreal.Vector(0,0,50),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[actor],unreal.DrawDebugTrace.NONE,True)
    if not hit or abs(hit.to_tuple()[5].z-feet.z)>5: raise RuntimeError('NPC feet are not grounded: '+npc_id)
    camera=center+unreal.Vector(450,450,130)
    capture.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,center),False,True)
    for _ in range(5):
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(directory),npc_id+'.png')
    npcs.append(npc_id)
if sorted(npcs)!=sorted(row['id'] for row in receipt['gameplay'] if row['kind']=='npc'):
    raise RuntimeError('Saved NPC population does not match receipt')
resources=[]
for actor in actors.get_all_level_actors():
    if not isinstance(actor,unreal.WarResourceNode) or str(actor.get_editor_property('zone_id')) not in ('sunmeadow_march','cinderfen_outskirts'): continue
    identity=str(actor.get_editor_property('node_id'))
    placement=next(row for row in receipt['resources'] if row['id']==identity)
    atmosphere(placement['zone'])
    mesh=actor.static_mesh_component
    if mesh.static_mesh.get_path_name()!=placement['mesh'] or str(mesh.get_collision_profile_name())!='NoCollision':
        raise RuntimeError('Saved herb visual or collision changed: '+identity)
    center,extent,_=unreal.SystemLibrary.get_component_bounds(mesh)
    feet=unreal.Vector(center.x,center.y,center.z-extent.z)
    hit=unreal.SystemLibrary.line_trace_single(world,feet+unreal.Vector(0,0,150),feet-unreal.Vector(0,0,150),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[actor],unreal.DrawDebugTrace.NONE,True)
    if not hit or not hit.to_tuple()[0] or abs(hit.to_tuple()[5].z-feet.z)>5:
        raise RuntimeError('Saved herb roots are not grounded: '+identity)
    camera=None
    for angle in (45,135,225,315,0,90,180,270):
        candidate=center+unreal.Vector(495*math.cos(math.radians(angle)),495*math.sin(math.radians(angle)),170)
        obstruction=unreal.SystemLibrary.line_trace_single(world,candidate,center,
            unreal.TraceTypeQuery.ECC_VISIBILITY,True,[actor],unreal.DrawDebugTrace.NONE,True)
        if not obstruction or not obstruction.to_tuple()[0]: camera=candidate;break
    if camera is None: raise RuntimeError('No unobstructed player-height resource view: '+identity)
    capture.set_actor_location_and_rotation(camera,unreal.MathLibrary.find_look_at_rotation(camera,center),False,True)
    for _ in range(5):
        unreal.WarImportLibrary.prepare_world_preview_frame(world);component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world,component.texture_target,str(directory),identity+'.png')
    resources.append({'id':identity,'materials':mesh.get_num_materials(),'grounded':True})
if len(resources)!=6: raise RuntimeError('Expected all six saved frontier herb patches')
(directory / 'render-verification.json').write_text(json.dumps({'map': receipt['map'], 'layer': receipt['layer'], 'portalLabels': len(portals), 'npcs':npcs, 'resources':resources, 'visualApproved': False}, indent=2))
