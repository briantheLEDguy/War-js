"""Private alpine material study; retain the measured mountain and its collision."""
import hashlib
import json
import math
import re

MOUNTAIN_MATERIAL_SOURCE = '/Game/Capitals/crownward/MountainGranite'
MOUNTAIN_TEXTURES = {
    'baseColor': '/Game/Capitals/crownward/Textures/MountainBaseColor.MountainBaseColor',
    'normal': '/Game/Capitals/crownward/Textures/MountainNormal.MountainNormal',
}
MOUNTAIN_MATERIAL_SPEC = dict(snowStartCm=17000, snowFullCm=29000,
    snowEarliestNoiseShiftCm=15200, heightNoiseSpanCm=3600,
    snowMinimumNormalZ=.28, snowFullNormalZ=.8, textureRepeat=6,
    retainedRenderNormalZSign=-1,
    rockTint=[.13, .19, .28], snowColor=[.52, .61, .72],
    geometryDisplacement=False, collisionChanged=False, originalTexturesPreserved=True)

MOUNTAIN_SHADER = r'''
struct AlpineNoise {
    float Hash(float3 p) {
        p = frac(p * .1031);
        p += dot(p, p.yzx + 33.33);
        return frac((p.x + p.y) * p.z);
    }
    float Value(float3 p) {
        float3 i = floor(p), f = frac(p);
        f = f * f * (3 - 2 * f);
        return lerp(lerp(lerp(Hash(i), Hash(i+float3(1,0,0)), f.x),
                         lerp(Hash(i+float3(0,1,0)), Hash(i+float3(1,1,0)), f.x), f.y),
                    lerp(lerp(Hash(i+float3(0,0,1)), Hash(i+float3(1,0,1)), f.x),
                         lerp(Hash(i+float3(0,1,1)), Hash(i+float3(1,1,1)), f.x), f.y), f.z);
    }
};
AlpineNoise noise;
float broad = noise.Value(P / 3200);
float fine = noise.Value(P / 850);
float heightMask = saturate((P.z - 17000 + (broad-.5)*3600) / 12000);
// The retained native render buffer has downward highland vertex normals.
// Its measured convention is bound before authoring this private material.
float shelter = saturate((-N.z - .28) / .52);
float snow = saturate(heightMask * (shelter * 2.4 + (fine-.5)*.18));
float3 rock = Rock * float3(.13,.19,.28) * lerp(.76,1.14,broad);
float3 frost = float3(.52,.61,.72) * lerp(.85,1.04,fine);
return lerp(rock, frost, snow);
'''


def mountain_render_normal_convention(run, candidate):
    """Bind the slope mask to actual saved render buffers, not source normals."""
    rows = candidate.get('terrainCarves', [])
    if len(rows) != 1:
        raise ValueError('One measured mountain carve is required')
    row = rows[0]
    if row.get('actorTransform') != dict(translationCm=[25000, 0, 0],
            rotationQuaternion=[0, 0, 0, 1], scale=[1, 1, 1]):
        raise ValueError('Mountain normal convention requires its measured unrotated transform')
    components = [c for c in row.get('actualActorState', {}).get('components', [])
                  if c.get('name') == 'StaticMeshComponent0']
    if (len(components) != 1 or components[0].get('mesh') != row.get('mesh')
            or components[0].get('transform') != [25000, 0, 0, 0, 0, 0, 1, 1, 1, 1]):
        raise ValueError('Actual mountain component must retain the measured world transform')
    native_policy = row.get('nativeReadback', {}).get('actualPolicy', {})
    if (type(native_policy.get('sourceLods')) is not int or native_policy['sourceLods'] != 1
            or native_policy.get('mesh', {}).get('nanite_settings', {}).get('bEnabled') is not False):
        raise ValueError('Slope convention is bound only to the actual single-LOD non-Nanite render buffer')
    binding = row.get('nativeReadback', {}).get('renderedFaces', {})
    if (binding.get('path') != 'terrain-carves/hall-carve-rendered-faces.json'
            or not re.fullmatch('[a-f0-9]{64}', str(binding.get('sha256')))):
        raise ValueError('Exact native mountain render binding is required')
    file = (run / binding['path']).resolve()
    file.relative_to(run.resolve())
    if file.stat().st_size > 128*1024*1024:
        raise ValueError('Native mountain render document is unbounded')
    raw = file.read_bytes()
    if hashlib.sha256(raw).hexdigest() != binding['sha256']:
        raise ValueError('Native mountain render bytes changed')
    document = json.loads(raw)
    if (document.get('readOnly') is not True or document.get('available') is not True
            or document.get('valid') is not True or document.get('invalidValues') != 0
            or document.get('policy') != 'actual_render_index_order_oriented_triangle_corners'
            or document.get('mesh') != row.get('mesh') or document.get('lod') != 0):
        raise ValueError('Actual saved native mountain render buffers are required')
    normals = []
    for face in document.get('triangles', []):
        positions, basis = face.get('positions'), face.get('normals')
        if (not isinstance(positions, list) or not isinstance(basis, list)
                or len(positions) != 3 or len(basis) != 3
                or any(not isinstance(v, list) or len(v) != 3
                    or any(type(c) not in (int, float) or not math.isfinite(c) for c in v)
                    for v in [*positions, *basis])):
            raise ValueError('Native mountain render corners are incomplete')
        normals.extend(n[2] for p, n in zip(positions, basis)
                       if p[2] > MOUNTAIN_MATERIAL_SPEC['snowEarliestNoiseShiftCm'])
    if not normals or any(n >= 0 or n < -1.001 for n in normals) or not any(n < -.28 for n in normals):
        raise ValueError('Retained highland render normals no longer follow the measured downward convention')
    return dict(version=1, source='actual_saved_native_rendered_faces',
        renderedFaces=binding, highlandCorners=len(normals),
        minimumValidatedHeightCm=MOUNTAIN_MATERIAL_SPEC['snowEarliestNoiseShiftCm'],
        actualComponentTransform=components[0]['transform'],sourceLods=1,naniteEnabled=False,
        renderNormalZRange=[min(normals), max(normals)], slopeMaskNormalZSign=-1,
        geometryChanged=False, collisionChanged=False)


def alpine_material(unreal, destination, duplicate, normal_convention):
    """Duplicate the exact reviewed PBR graph; never save source assets."""
    target = destination + '/Materials/M_AlpineGranite'
    duplicate(MOUNTAIN_MATERIAL_SOURCE, target)
    material = unreal.load_asset(target)
    lib = unreal.MaterialEditingLibrary
    color = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    normal = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_NORMAL)
    for role, node in [('baseColor', color), ('normal', normal)]:
        if not isinstance(node, unreal.MaterialExpressionTextureSample) or node.texture.get_path_name() != MOUNTAIN_TEXTURES[role]:
            raise RuntimeError('Preserve an independently changed original granite PBR graph: ' + role)
    uv = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate)
    uv.set_editor_property('u_tiling', MOUNTAIN_MATERIAL_SPEC['textureRepeat'])
    uv.set_editor_property('v_tiling', MOUNTAIN_MATERIAL_SPEC['textureRepeat'])
    for node in (color, normal):
        if not lib.connect_material_expressions(uv, '', node, 'UVs'):
            raise RuntimeError('Cannot bind copied mountain texture coordinates')
    position = lib.create_material_expression(material, unreal.MaterialExpressionWorldPosition)
    vertex_normal = lib.create_material_expression(material, unreal.MaterialExpressionVertexNormalWS)
    shader = lib.create_material_expression(material, unreal.MaterialExpressionCustom)
    shader.set_editor_property('description', 'Bastion alpine rock and sheltered snow study')
    shader.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs=[]
    for name in ('P','N','Rock'):
        entry=unreal.CustomInput()
        entry.set_editor_property('input_name',name)
        inputs.append(entry)
    shader.set_editor_property('inputs',inputs)
    shader.set_editor_property('code', MOUNTAIN_SHADER)
    for node, output, name in [(position, '', 'P'), (vertex_normal, '', 'N'), (color, 'RGB', 'Rock')]:
        if not lib.connect_material_expressions(node, output, shader, name):
            raise RuntimeError('Cannot bind exact copied alpine shader input: ' + name)
    if not lib.connect_material_property(shader, '', unreal.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Cannot bind copied alpine base color')
    if lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_NORMAL) != normal:
        raise RuntimeError('Original granite normal graph was lost')
    if shader.get_editor_property('code') != MOUNTAIN_SHADER:
        raise RuntimeError('Owned alpine shader code readback differs from the signed study')
    errors = lib.recompile_material(material)
    if errors:
        raise RuntimeError('Owned alpine shader compilation failed: ' + str(errors))
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Cannot save the owned alpine study material')
    return material, dict(spec=MOUNTAIN_MATERIAL_SPEC, originalTextures=MOUNTAIN_TEXTURES,
        nativeRenderNormalConvention=normal_convention,
        material=material.get_path_name(), originalNormalTextureAndConnectionPreserved=True,
        shaderCodeReadbackMatches=shader.get_editor_property('code') == MOUNTAIN_SHADER)
