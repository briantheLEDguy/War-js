"""Reopen the saved campaign, verify all portal meshes and capture both realms."""
import hashlib
import json
import math
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/unreal/portal-models'
receipt = json.loads((OUT/'installation.json').read_text())
package_file = ROOT/'unreal/AegisWar/Content'/(receipt['layer'].removeprefix('/Game/')+'.umap')
if hashlib.sha256(package_file.read_bytes()).hexdigest() != receipt['packageSha256']:
    raise RuntimeError('Installed routing package changed')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level(receipt['map']):
    raise RuntimeError('Installed campaign unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
unreal.WarImportLibrary.prepare_world_preview_frame(world)
all_actors = actors.get_all_level_actors()
visuals = [a for a in all_actors if isinstance(a, unreal.StaticMeshActor) and 'WarPortalVisual' in [str(t) for t in a.tags]]
lights = [a for a in all_actors if 'WarPortalFill' in [str(t) for t in a.tags]]
portals = {str(a.get_editor_property('route_id')): a for a in all_actors if isinstance(a, unreal.WarZonePortal)}
if len(visuals) != 140 or len(lights) != 140 or len(portals) != 70 or len(receipt['placements']) != 70:
    raise RuntimeError('Incomplete saved portal coverage')
for row in receipt['placements']:
    fills = [a for a in lights if 'WarPortalRoute_'+row['route'] in [str(t) for t in a.tags]]
    if len(fills) != 2 or any(not a.light_component.is_visible() for a in fills):
        raise RuntimeError('Missing portal frame lighting')
    label = portals[row['route']].get_component_by_class(unreal.TextRenderComponent)
    expected_label = unreal.Vector(*row['position'])+unreal.Vector(0, 0, 1300)
    if not label or (label.get_world_location()-expected_label).length() > .1:
        raise RuntimeError('Destination label is not above the portal')
    if abs((label.get_world_rotation().yaw-row['yaw']-90+180)%360-180) > .1:
        raise RuntimeError('Destination label does not face the portal approach')
    matches = [a for a in visuals if 'WarPortalRoute_'+row['route'] in [str(t) for t in a.tags]]
    if len(matches) != 2:
        raise RuntimeError('Missing/duplicate portal parts: '+row['route'])
    for part, path in row['assets'].items():
        match = [a for a in matches if 'WarPortalPart_'+part in [str(t) for t in a.tags]]
        if len(match) != 1:
            raise RuntimeError('Missing portal part: '+row['route']+' '+part)
        actor = match[0]
        mesh = actor.static_mesh_component
        if not mesh.static_mesh or mesh.static_mesh.get_path_name() != path:
            raise RuntimeError('Saved mesh binding changed')
        if actor.get_editor_property('hidden') or not mesh.is_visible() or mesh.get_editor_property('hidden_in_game'):
            raise RuntimeError('Portal is hidden during gameplay')
        if str(mesh.get_collision_profile_name()) != 'NoCollision':
            raise RuntimeError('Visual obstructs existing traversal')
        if (actor.get_actor_location()-unreal.Vector(*row['position'])).length() > .1:
            raise RuntimeError('Visual moved away from its portal')
        if any(not mesh.get_material(i) for i in range(mesh.get_num_materials())):
            raise RuntimeError('Missing portal material')
        if actor.get_outer().get_path_name().split('.')[0] != receipt['layer']:
            raise RuntimeError('Portal visual is not in the always-loaded routing layer')
anchors = {str(a.get_editor_property('zone_id')): a for a in all_actors if isinstance(a, unreal.WarZoneAnchor)}
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector())
camera = capture.capture_component2d
camera.texture_target = unreal.RenderingLibrary.create_render_target2d(world, 1280, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8)
camera.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
camera.capture_every_frame = False
camera.capture_on_movement = False
camera.always_persist_rendering_state = True
camera.fov_angle = 65
camera.post_process_blend_weight = 0
for variant, zone in [('Aegis', 'sunmeadow_march'), ('Riftbound', 'cinderfen_outskirts')]:
    row = next(r for r in receipt['placements'] if r['zone'] == zone)
    anchor = anchors[zone]
    if not unreal.WarZoneLightingSubsystem.preview_world(world, zone, anchor.get_editor_property('zone_origin')):
        raise RuntimeError('Zone lighting unavailable')
    feet = unreal.Vector(*row['position'])
    angle = math.radians(row['yaw']+90)
    facing = unreal.Vector(math.cos(angle), math.sin(angle), 0)
    location = feet+facing*1800+unreal.Vector(0, 0, 220)
    capture.set_actor_location_and_rotation(location, unreal.MathLibrary.find_look_at_rotation(location, feet+unreal.Vector(0, 0, 650)), False, True)
    for _ in range(5):
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        camera.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, camera.texture_target, str(OUT), variant+'-installed.png')
receipt['savedBindingsVerified'] = True
receipt['verifiedPortalCount'] = 70
(OUT/'installation.json').write_text(json.dumps(receipt, indent=2)+'\n')
unreal.log('WAR_PORTAL_VISUALS_VERIFIED=70')
