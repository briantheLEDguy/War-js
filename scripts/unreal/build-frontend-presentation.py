"""Snapshot existing capital visuals into private, gameplay-free frontend content.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>. Source maps are
read, never saved. Generated packages stay under the ignored native Content tree.
"""
import hashlib
import json
import struct
import zlib
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / 'unreal/AegisWar/Content'
OUTPUT = ROOT / 'artifacts/unreal/frontend'
OUTPUT.mkdir(parents=True, exist_ok=True)
FOLDER = '/Game/UI/Frontend'
OWNER = 'cinematic-frontend-v1'
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
manifest = json.loads((ROOT / 'artifacts/unreal/world-portals/zone-manifest.json').read_text())
build = json.loads((ROOT / 'artifacts/unreal/world-portals/build.json').read_text())
sources = {}
material_copies = {}


def instance_material(source):
    """Private adaptations gain the instancing shader permutation; originals stay untouched."""
    path = source.get_path_name()
    if path in material_copies:
        return material_copies[path]
    if path.startswith('/Game/'):
        fingerprint(path)
    revision = sources.get(path.split('.')[0], '')
    destination = FOLDER + '/Materials/M_' + hashlib.sha256((path + revision).encode()).hexdigest()[:20]
    copy = assets.load_asset(destination) if assets.does_asset_exist(destination) else None
    if copy and assets.get_metadata_tag(copy, 'WarFrontendOwner') != OWNER:
        raise RuntimeError('Refusing to replace unowned material: ' + destination)
    if not copy:
        copy = assets.duplicate_asset(path, destination)
        if not copy:
            raise RuntimeError('Material adaptation failed: ' + path)
        assets.set_metadata_tag(copy, 'WarFrontendOwner', OWNER)
    material_copies[path] = copy
    if isinstance(copy, unreal.MaterialInstanceConstant):
        unreal.MaterialEditingLibrary.set_material_instance_parent(copy, instance_material(source.get_editor_property('parent')))
        unreal.MaterialEditingLibrary.update_material_instance(copy)
    elif isinstance(copy, unreal.Material):
        unreal.MaterialEditingLibrary.set_base_material_usage(copy, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        unreal.MaterialEditingLibrary.recompile_material(copy)
    else:
        raise RuntimeError('Unsupported source material: ' + path)
    assets.save_loaded_asset(copy, only_if_is_dirty=False)
    return copy


def owned(name, cls, factory):
    path = FOLDER + '/' + name
    value = assets.load_asset(path) if assets.does_asset_exist(path) else None
    if value:
        if assets.get_metadata_tag(value, 'WarFrontendOwner') != OWNER:
            raise RuntimeError('Refusing to replace unowned asset: ' + path)
        return value
    value = tools.create_asset(name, FOLDER, cls, factory)
    if not value:
        raise RuntimeError('Asset creation failed: ' + path)
    assets.set_metadata_tag(value, 'WarFrontendOwner', OWNER)
    return value


def fingerprint(package):
    relative = package.split('.')[0].removeprefix('/Game/')
    for suffix in ('.umap', '.uasset'):
        file = CONTENT / (relative + suffix)
        if file.is_file():
            sources[package.split('.')[0]] = hashlib.sha256(file.read_bytes()).hexdigest()
            return
    raise RuntimeError('Missing native package: ' + package)


def placements(zone, maps):
    groups, seen = {}, set()
    origin = unreal.Vector(*zone['origin'])
    skipped = []
    for map_path in maps:
        fingerprint(map_path)
        if not levels.load_level(map_path):
            raise RuntimeError('Cannot load city source: ' + map_path)
        for actor in actors.get_all_level_actors():
            # Streaming dependencies can contain another capital or duplicate this layer.
            if actor.get_outer().get_outer().get_path_name().split('.')[0] != map_path:
                continue
            for component in actor.get_components_by_class(unreal.StaticMeshComponent):
                mesh = component.static_mesh
                if not mesh or not component.is_visible() or component.get_editor_property('hidden_in_game'):
                    continue
                mesh_path = mesh.get_path_name()
                if not mesh_path.startswith('/Game/') or '/BasicShapes/' in mesh_path:
                    skipped.append(mesh_path)
                    continue
                materials = [component.get_material(index) for index in range(component.get_num_materials())]
                if any(material is None for material in materials):
                    raise RuntimeError('Missing city material: ' + mesh_path)
                if isinstance(component, unreal.InstancedStaticMeshComponent):
                    transforms = [component.get_instance_transform(index, world_space=True)
                                  for index in range(component.get_instance_count())]
                else:
                    transforms = [component.get_world_transform()]
                key = (mesh_path, tuple(material.get_path_name() for material in materials))
                if key not in groups:
                    groups[key] = {'mesh': mesh, 'materials': [instance_material(material) for material in materials], 'instances': []}
                    fingerprint(mesh_path)
                    for material in materials:
                        if material.get_path_name().startswith('/Game/'):
                            fingerprint(material.get_path_name())
                for transform in transforms:
                    transform.translation = transform.translation - origin
                    t, r, s = transform.translation, transform.rotation, transform.scale3d
                    identity = (key, tuple(round(v, 4) for v in (t.x, t.y, t.z, r.x, r.y, r.z, r.w, s.x, s.y, s.z)))
                    if identity in seen:
                        continue
                    seen.add(identity)
                    groups[key]['instances'].append(transform)
    rows = []
    for row in groups.values():
        if not row['instances']:
            continue
        entry = unreal.WarFrontendPlacement()
        for name, value in row.items():
            entry.set_editor_property(name, value)
        rows.append(entry)
    if not rows:
        raise RuntimeError('Capital contains no usable native scenery: ' + zone['id'])
    return rows, sorted(set(skipped))


def shot(eye, end, target, fov=55):
    value = unreal.WarFrontendShot()
    for name, item in [('eye', unreal.Vector(*eye)), ('end_eye', unreal.Vector(*end)),
                       ('target', unreal.Vector(*target)), ('field_of_view', fov)]:
        value.set_editor_property(name, item)
    return value


def character_material():
    # SceneColor HDR carries inverse opacity. Composite without a rectangular backdrop.
    name = 'T_CharacterDefault'
    texture = assets.load_asset(FOLDER + '/' + name) if assets.does_asset_exist(FOLDER + '/' + name) else None
    if not texture:
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 4, 4, 8, 6, 0, 0, 0))
        png += chunk(b'IDAT', zlib.compress((b'\0' + b'\xff' * 16) * 4)) + chunk(b'IEND', b'')
        file = OUTPUT / 'character-default.png'
        file.write_bytes(png)
        task = unreal.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = str(file), FOLDER, name
        task.automated, task.save = True, True
        tools.import_asset_tasks([task])
        texture = task.get_objects()[0]
        texture.set_editor_property('srgb', False)
        assets.set_metadata_tag(texture, 'WarFrontendOwner', OWNER)
        assets.save_loaded_asset(texture)
    material = owned('M_CharacterComposite', unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary
    lib.delete_all_material_expressions(material)
    material.set_editor_property('material_domain', unreal.MaterialDomain.MD_UI)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    sample = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
    sample.set_editor_property('parameter_name', 'CharacterTexture')
    sample.set_editor_property('texture', texture)
    sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    inverse = lib.create_material_expression(material, unreal.MaterialExpressionOneMinus)
    if not lib.connect_material_expressions(sample, 'A', inverse, ''):
        raise RuntimeError('Cannot connect character inverse opacity')
    if not lib.connect_material_property(inverse, '', unreal.MaterialProperty.MP_OPACITY):
        raise RuntimeError('Cannot connect character opacity output')
    # Bounded exposure for the isolated studio light, keeping metallic highlights intact.
    add = lib.create_material_expression(material, unreal.MaterialExpressionAdd)
    add.set_editor_property('const_b', 1.0)
    divide = lib.create_material_expression(material, unreal.MaterialExpressionDivide)
    for source, pin, target, input_pin in [(sample, 'RGB', add, 'A'), (sample, 'RGB', divide, 'A'), (add, '', divide, 'B')]:
        if not lib.connect_material_expressions(source, pin, target, input_pin):
            raise RuntimeError('Cannot connect character color graph')
    if not lib.connect_material_property(divide, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Cannot connect character color output')
    lib.recompile_material(material)
    assets.save_loaded_asset(material)
    return material


cities, counts = [], []
for zone_id, label in [('aegis_capital', 'Bastion of Aegis'), ('riftspire_capital', 'Riftspire Citadel')]:
    zone = next(row for row in manifest['zones'] if row['id'] == zone_id)
    maps = ([build['map']] if zone_id == 'aegis_capital' else []) + [zone['levels'][key] for key in ('generated', 'authored')]
    rows, skipped = placements(zone, maps)
    city = unreal.WarFrontendCity()
    city.set_editor_property('zone_id', zone_id)
    city.set_editor_property('label', label)
    city.set_editor_property('placements', rows)
    if zone_id == 'aegis_capital':
        city.set_editor_property('shots', [
            shot((-18000, -12500, 4200), (-16300, -11900, 4250), (16500, 2000, 3500)),
            shot((11000, -8000, 10600), (12000, -7500, 10400), (17800, 0, 5100), 60)])
    else:
        city.set_editor_property('shots', [
            shot((-38000, -34000, 28000), (-35000, -33000, 27000), (0, 0, 2500), 60),
            shot((31000, -27000, 21000), (29000, -25000, 20000), (0, 0, 4000), 60)])
        city.set_editor_property('sun_direction', unreal.Rotator(pitch=-29, yaw=148))
        city.set_editor_property('sun_color', unreal.LinearColor(1, .72, .52, 1))
        city.set_editor_property('fog_color', unreal.LinearColor(.16, .13, .22, 1))
    cities.append(city)
    counts.append({'zone': zone_id, 'groups': len(rows), 'instances': sum(len(row.get_editor_property('instances')) for row in rows), 'excludedNonProjectMeshes': skipped})

factory = unreal.DataAssetFactory()
factory.set_editor_property('data_asset_class', unreal.WarFrontendPresentationDefinition)
definition = owned('CapitalPresentation', unreal.WarFrontendPresentationDefinition, factory)
definition.set_editor_property('cities', cities)
definition.set_editor_property('character_composite', character_material())
definition.set_editor_property('hold_seconds', 18)
definition.set_editor_property('fade_seconds', 3)
assets.save_loaded_asset(definition, only_if_is_dirty=False)
for package, expected in sources.items():
    fingerprint(package)
    if sources[package] != expected:
        raise RuntimeError('Source package changed during snapshot: ' + package)
(OUTPUT / 'build.json').write_text(json.dumps({'schemaVersion': 1, 'asset': definition.get_path_name(),
    'cities': counts, 'sourcePackages': sources, 'sourceMapsModified': False, 'visualApproved': False,
    'licenseApprovalChanged': False}, indent=2) + '\n')
unreal.log('WAR_FRONTEND_BUILT ' + json.dumps(counts))
