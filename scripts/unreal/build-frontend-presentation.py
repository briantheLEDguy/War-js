"""Bind frontend cameras to the shared, gameplay-free capital levels.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>. Source maps are
read, never saved. Generated packages stay under the ignored native Content tree.
"""
import json
import struct
import zlib
import sys
from pathlib import Path
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frontend_sources import digest, package_file, source_plan

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
plan = source_plan(ROOT)
sources = {}
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
    sources[package.split('.')[0]] = digest(package_file(ROOT, package))


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
    zone = next(row for row in plan['cities'] if row['id'] == zone_id)
    shared = assets.load_asset(zone['definition'])
    if not isinstance(shared, unreal.WarCityDefinition):
        raise RuntimeError('Shared city definition unavailable: ' + zone_id)
    for package in [zone['definition'], *zone['sceneryLevels']]:
        fingerprint(package)
    city = unreal.WarFrontendCity()
    city.set_editor_property('zone_id', zone_id)
    city.set_editor_property('label', label)
    city.set_editor_property('city_definition', shared)
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
    counts.append({'zone': zone_id, 'definition': zone['definition'], 'revision': zone['revision'], 'levels': zone['sceneryLevels']})

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
        raise RuntimeError('Source package changed during frontend binding: ' + package)
if source_plan(ROOT) != plan:
    raise RuntimeError('Capital routing changed during frontend binding; retry the refresh.')
outputs = {package: digest(package_file(ROOT, package)) for package in assets.list_assets(FOLDER, recursive=True)
           if assets.get_metadata_tag(assets.load_asset(package), 'WarFrontendOwner') == OWNER}
# Normalize object paths so freshness checks use package identities consistently.
outputs = {package.split('.')[0]: value for package, value in outputs.items()}
(OUTPUT / 'build.json').write_text(json.dumps({'schemaVersion': 3, 'asset': definition.get_path_name(),
    'sourcePlan': plan, 'outputPackages': outputs,
    'cities': counts, 'sourcePackages': sources, 'sourceMapsModified': False, 'visualApproved': False,
    'licenseApprovalChanged': False}, indent=2) + '\n')
unreal.log('WAR_FRONTEND_BUILT ' + json.dumps(counts))
