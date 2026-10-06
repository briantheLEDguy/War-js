"""Read installed cloud parameters and exact private study state without edits."""
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_blueprint import sha
from aegis_citadel_lighting import REVIEWED_CLOUD_MATERIAL
from shared_city_sources import package_file

directory = ROOT / 'artifacts/unreal/aegis-citadel/b619391123d3/lighting-study-cb23e4f6b06f'
study = json.loads((directory / 'study.json').read_text())
before = {p: sha(package_file(ROOT, p)) for p in study['createdPackageHashes']}
if before != study['createdPackageHashes']:
    raise RuntimeError('Preserve edited private lighting study')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(study['map']):
    raise RuntimeError('Private study unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()

def read(obj, key):
    try:
        value = obj.get_editor_property(key)
        if value is None or isinstance(value, (str, int, bool, float)):
            return value
        if hasattr(value, 'get_path_name'):
            return value.get_path_name()
        return str(value)
    except Exception as error:
        return dict(unavailable=str(error))

clouds = [dict(path=a.get_path_name(), location=str(a.get_actor_location()), values={key:read(
    a.get_component_by_class(unreal.VolumetricCloudComponent), key) for key in (
    'layer_bottom_altitude','layer_height','planet_radius','tracing_start_max_distance',
    'tracing_max_distance','material','view_sample_count_scale','shadow_view_sample_count_scale')})
    for a in actors if isinstance(a, unreal.VolumetricCloud)]
atmospheres = [dict(path=a.get_path_name(),location=str(a.get_actor_location()), values={key:read(
    a.get_component_by_class(unreal.SkyAtmosphereComponent),key) for key in (
    'transform_mode','bottom_radius','atmosphere_height')}) for a in actors if isinstance(a,unreal.SkyAtmosphere)]
material = unreal.load_asset(REVIEWED_CLOUD_MATERIAL)
parameters = {}
for kind in ('scalar', 'vector', 'texture'):
    try:
        names = getattr(unreal.MaterialEditingLibrary, 'get_' + kind + '_parameter_names')(material)
        parameters[kind] = {str(n): str(getattr(unreal.MaterialEditingLibrary,
            'get_material_instance_' + kind + '_parameter_value')(material,n)) for n in names}
    except Exception as error:
        parameters[kind] = dict(unavailable=str(error))
parent = material.get_editor_property('parent')
while isinstance(parent, unreal.MaterialInstance):
    parent = parent.get_editor_property('parent')
expressions = []
for node in unreal.MaterialEditingLibrary.get_material_expressions(parent):
    if isinstance(node,(unreal.MaterialExpressionScalarParameter,unreal.MaterialExpressionVectorParameter,
                         unreal.MaterialExpressionMaterialFunctionCall)):
        keys = ('parameter_name','default_value') if not isinstance(node,unreal.MaterialExpressionMaterialFunctionCall) else ('material_function',)
        expressions.append(dict(klass=node.get_class().get_name(),values={k:read(node,k) for k in keys}))
after = {p: sha(package_file(ROOT, p)) for p in before}
if before != after:
    raise RuntimeError('Read-only cloud inspection modified a study package')
report = dict(diagnosticOnly=True,clouds=clouds,atmospheres=atmospheres,parameters=parameters,
    parent=parent.get_path_name(),expressions=expressions,packagesUnchanged=True)
(directory / 'cloud-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.log('WAR_CITADEL_CLOUD_INSPECTION=' + str(directory / 'cloud-inspection.json'))
