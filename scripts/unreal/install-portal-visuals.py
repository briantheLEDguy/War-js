"""Install authored portal meshes in the current private routing level.

Preserves traversal geometry and route data. The art remains a development
candidate; world placement does not grant reference-fidelity/release approval.
"""
import datetime
import hashlib
import json
import math
import shutil
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/unreal/portal-models'
WORLD = ROOT/'artifacts/unreal/world-portals'
TAG = 'WarPortalVisual'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(portal):
    return {key: str(portal.get_editor_property(key)) for key in
            ('route_id', 'destination_route_id', 'arrival_location', 'radius', 'destination_built')}


def main():
    build = json.loads((WORLD/'build.json').read_text())
    plan = json.loads((WORLD/'plan.json').read_text())
    native = json.loads((OUT/'baked/native-candidates.json').read_text())
    models = {}
    for row in native:
        if sha(OUT/'baked'/(row['name']+'.glb')) != row['sourceSha256']:
            raise RuntimeError('Changed model export: '+row['name'])
        models[row['name']] = {part: unreal.load_asset(value['asset']) for part, value in row['parts'].items()}
        if set(models[row['name']]) != {'Structure', 'Effects'} or not all(models[row['name']].values()):
            raise RuntimeError('Missing authored portal meshes')
    if set(models) != {'Aegis', 'Riftbound'}:
        raise RuntimeError('Both portal variants are required')
    # Interchange emission is calibrated for a studio, not the campaign's sun.
    # Derive separate world materials so the editable import remains untouched.
    world_materials = {}
    library = unreal.EditorAssetLibrary
    graph = unreal.MaterialEditingLibrary
    for variant, parts in models.items():
        mesh = parts['Effects']
        bindings = []
        for slot in mesh.static_materials:
            source = slot.material_interface
            path = '/Game/PortalCandidates/WorldGlow_v1/'+variant+'_'+source.get_name()
            material = unreal.load_asset(path)
            if not material:
                material = library.duplicate_asset(source.get_path_name(), path)
                if not material: raise RuntimeError('Cannot derive portal glow')
                original = graph.get_material_property_input_node(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
                output = graph.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
                gain = graph.create_material_expression(material, unreal.MaterialExpressionMultiply)
                gain.set_editor_property('const_b', 1200.)
                if not original or not graph.connect_material_expressions(original, output, gain, 'A'):
                    raise RuntimeError('Missing source portal emission')
                if not graph.connect_material_property(gain, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR):
                    raise RuntimeError('Cannot bind world emission')
                if graph.recompile_material(material): raise RuntimeError('World glow shader failed')
                if not library.save_loaded_asset(material, False): raise RuntimeError('Cannot save world glow')
            bindings.append(material)
        world_materials[variant] = bindings
    package = build['layer']
    if not package.startswith('/Game/WorldRebuild/'):
        raise RuntimeError('Unowned routing package')
    file = ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')
    original_hash = sha(file)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not levels.load_level(build['map']):
        raise RuntimeError('Current campaign is unavailable')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    unreal.WarImportLibrary.prepare_world_preview_frame(world)
    portals = {str(a.get_editor_property('route_id')): a for a in actors.get_all_level_actors()
               if isinstance(a, unreal.WarZonePortal)}
    if sorted(portals) != sorted(build['portals']) or len(portals) != 70:
        raise RuntimeError('Saved routing coverage differs from the installed campaign')
    anchors = {str(a.get_editor_property('zone_id')): a for a in actors.get_all_level_actors()
               if isinstance(a, unreal.WarZoneAnchor)}
    routes = {r['id']: r for r in plan['routes']}
    before = {key: state(portal) for key, portal in portals.items()}
    placements = []
    # Resolve every variant and position before editing any actor.
    for key, portal in sorted(portals.items()):
        if portal.get_outer().get_path_name().split('.')[0] != package:
            raise RuntimeError('Portal is not in the installed routing level: '+key)
        zone = routes[key]['zoneId']
        source = json.loads((ROOT/'public/assets/maps'/(zone+'.json')).read_text())
        realm = source.get('campaign', {}).get('realm')
        if realm not in ('aegis', 'riftbound'):
            raise RuntimeError('Portal needs an explicit authored realm: '+zone)
        variant = 'Aegis' if realm == 'aegis' else 'Riftbound'
        point = portal.get_actor_location()
        # Routing authoring places every trigger 100 cm above its ground anchor.
        # Keep that anchor rather than accidentally tracing onto overhead scenery.
        feet = point-unreal.Vector(0, 0, 100)
        center = anchors[zone].get_editor_property('zone_origin')
        yaw = math.degrees(math.atan2(center.y-point.y, center.x-point.x))-90
        placements.append(dict(route=key, zone=zone, variant=variant,
                               position=[feet.x, feet.y, feet.z], yaw=yaw))
    if sha(file) != original_hash or json.loads((WORLD/'build.json').read_text())['layer'] != package:
        raise RuntimeError('Campaign changed during preflight; preserve the newer work')
    backup = OUT/('routing-before-visuals-'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.umap')
    shutil.copy2(file, backup)
    if not levels.set_current_level_by_name(package.rsplit('/', 1)[1]):
        raise RuntimeError('Cannot select routing level')
    for actor in actors.get_all_level_actors():
        if TAG in [str(t) for t in actor.tags] and actor.get_outer().get_path_name().split('.')[0] == package:
            actors.destroy_actor(actor)
    for row in placements:
        # TextRender faces local +X; the mesh's front is local +Y. Put the
        # destination above the 1086 cm spire, in the portal's vertical plane.
        label = portals[row['route']].get_component_by_class(unreal.TextRenderComponent)
        if not label: raise RuntimeError('Missing portal destination label')
        label.set_world_location_and_rotation(unreal.Vector(*row['position'])+unreal.Vector(0, 0, 1300),
                                              unreal.Rotator(yaw=row['yaw']+90), False, True)
        label.set_world_size(48.)
        for part, mesh in models[row['variant']].items():
            actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*row['position']),
                                                 unreal.Rotator(yaw=row['yaw']))
            actor.set_actor_label(row['route']+' '+part)
            actor.tags = [TAG, 'WarPortalRoute_'+row['route'], 'WarPortalPart_'+part]
            component = actor.static_mesh_component
            component.set_static_mesh(mesh)
            if part == 'Effects':
                for index, material in enumerate(world_materials[row['variant']]):
                    component.set_material(index, material)
            # These are entrance landmarks, reached before the trigger's admission
            # boundary. Do not add collision across the existing safe travel path.
            component.set_collision_profile_name('NoCollision')
            component.set_visibility(True)
            actor.set_actor_hidden_in_game(False)
            row.setdefault('assets', {})[part] = mesh.get_path_name()
        angle = math.radians(row['yaw']+90)
        front = unreal.Vector(math.cos(angle), math.sin(angle), 0)
        side = unreal.Vector(-front.y, front.x, 0)
        for index, offset in enumerate((-420, 420)):
            location = unreal.Vector(*row['position'])+front*750+side*offset+unreal.Vector(0, 0, 650)
            light = actors.spawn_actor_from_class(unreal.PointLight, location)
            light.tags = [TAG, 'WarPortalFill', 'WarPortalRoute_'+row['route']]
            light.set_actor_label(row['route']+' frame light '+str(index))
            component = light.light_component
            component.set_mobility(unreal.ComponentMobility.MOVABLE)
            component.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
            component.set_intensity(2000000.)
            component.set_attenuation_radius(1900.)
            component.set_source_radius(250.)
            component.set_cast_shadows(False)
            component.set_light_color(unreal.LinearColor(1., .9, .78, 1.), False)
    if before != {key: state(portal) for key, portal in portals.items()}:
        raise RuntimeError('Portal traversal data changed')
    if not levels.save_current_level():
        raise RuntimeError('Routing save failed')
    receipt = dict(map=build['map'], layer=package, packageSha256=sha(file), backup=str(backup),
                   placements=placements, worldInstalled=True, artApproved=False, runtimeVerified=False)
    (OUT/'installation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    build['runtimeTraversalVerified'] = False
    build['visualApproved'] = False
    (WORLD/'build.json').write_text(json.dumps(build, indent=2)+'\n')
    if build.get('partitionManifest'):
        path = WORLD/build['partitionManifest']
        manifest = json.loads(path.read_text())
        manifest['packageHashes'][package] = sha(file)
        manifest.pop('traversalEvidence', None)
        path.write_text(json.dumps(manifest, indent=2)+'\n')
    unreal.log('WAR_PORTAL_VISUALS_INSTALLED='+str(len(placements)))


if __name__ == '__main__':
    main()
