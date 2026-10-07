"""Opt-in private albedo studies; no geometry or renderer acceptance."""
import copy
import hashlib
import json
import math
import re
from pathlib import Path

SURFACE_SWITCH = 'WAR_CITADEL_SURFACE_STUDY'
MOUNTAIN_SWITCH = 'WAR_CITADEL_RETAINED_MOUNTAIN_STUDY'
SURFACE_MODE = 'cool_masonry_weathered_sculpture_v1'
MOUNTAIN_MODE = 'existing_alpine_color_v2_preserve_uv'
PALETTE = dict(stone=[.19, .23, .29], limestone=[.28, .32, .39],
               flagstone=[.40, .45, .52], paving_inlay=[.23, .29, .37])
SCULPTURE_COLOR = [.065, .080, .100]
SCULPTURE_IDS = ('court_oath', 'west_guard', 'east_guard', 'west_terrace_guard', 'east_terrace_guard')
LUMINANCE_SHADER = '''
float luminance = dot(Raw, float3(.2126, .7152, .0722));
return luminance * Palette;
'''
ROOT_PROPERTIES = ('MP_BASE_COLOR', 'MP_NORMAL', 'MP_ROUGHNESS', 'MP_METALLIC',
                   'MP_SPECULAR', 'MP_AMBIENT_OCCLUSION', 'MP_EMISSIVE_COLOR',
                   'MP_WORLD_POSITION_OFFSET', 'MP_OPACITY', 'MP_OPACITY_MASK',
                   'MP_MATERIAL_ATTRIBUTES', 'MP_PIXEL_DEPTH_OFFSET', 'MP_DISPLACEMENT',
                   *('MP_CUSTOMIZED_UVS' + str(index) for index in range(8)))
MATERIAL_PROPERTIES = ('material_domain', 'blend_mode', 'shading_model',
                       'two_sided', 'tangent_space_normal', 'use_material_attributes')
NODE_VALUES = {
    'MaterialExpressionConstant': ('r',),
    'MaterialExpressionConstant3Vector': ('constant',),
    'MaterialExpressionConstant4Vector': ('constant',),
    'MaterialExpressionMultiply': ('const_a', 'const_b'),
    'MaterialExpressionNormalize': (),
    'MaterialExpressionTextureObject': ('texture', 'sampler_type'),
    'MaterialExpressionTextureSample': ('texture', 'sampler_type', 'const_coordinate',
        'const_mip_value', 'mip_value_mode', 'sampler_source', 'automatic_view_mip_bias', 'gather_mode'),
    'MaterialExpressionMaterialFunctionCall': ('material_function',),
    'MaterialExpressionCustom': ('code', 'output_type', 'description'),
    'MaterialExpressionWorldPosition': ('world_position_shader_offset',),
    'MaterialExpressionVertexNormalWS': (),
}


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def selected_specs(environment, lighting_mode, root, source_dir, candidate, mountain_inspection=None):
    """An absent switch does not read source artifacts or alter any request."""
    choices = [environment.get(SURFACE_SWITCH, ''), environment.get(MOUNTAIN_SWITCH, '')]
    if choices[0] not in ('', SURFACE_MODE) or choices[1] not in ('', MOUNTAIN_MODE):
        raise ValueError('Unknown private material study selector')
    if not any(choices):
        return None
    if lighting_mode not in ('base', 'lumen_software', 'lumen_hardware'):
        raise ValueError('Private material comparisons require an untreated base or private Lumen mode')
    from aegis_citadel_stone_material import COLOR_SHADER, SPEC as CARVED_SPEC
    from aegis_citadel_mountain_material import MOUNTAIN_SHADER, MOUNTAIN_MATERIAL_SPEC
    root, source_dir = Path(root).resolve(), Path(source_dir).resolve()
    source_dir.relative_to(root)
    if not re.fullmatch('[a-f0-9]{12}', source_dir.name):
        raise ValueError('Explicit historical source revision required')
    assets = json.loads((source_dir / 'assets-source.json').read_text())
    bindings = {}
    for file in [source_dir / name for name in ('assets-source.json', 'blueprint.json', 'candidate.json')]:
        bindings[str(file.relative_to(root)).replace('\\', '/')] = sha(file)
    for name in ('aegis_citadel_stone_material.py', 'aegis_citadel_mountain_material.py',
                 'stage-aegis-citadel.py', 'citadel_stage_contract.py', 'world_actor_state.py'):
        file = root / 'scripts/unreal' / name
        bindings[str(file.relative_to(root)).replace('\\', '/')] = sha(file)
    for name in ('Private/WarImportLibrary.cpp', 'Public/WarImportLibrary.h'):
        file = root / 'unreal/AegisWar/Source/AegisWarEditorTools' / name
        bindings[str(file.relative_to(root)).replace('\\', '/')] = sha(file)
    for role in PALETTE:
        for channel in ('baseColor', 'height', 'normal', 'orm'):
            if channel in assets['materialSpecs'][role]:
                file = (root / assets['materialSpecs'][role][channel]).resolve()
                file.relative_to(root)
                bindings[str(file.relative_to(root)).replace('\\', '/')] = sha(file)
    if candidate != json.loads((source_dir / 'candidate.json').read_text()):
        raise ValueError('Candidate differs from its complete source binding')
    if choices[1]:
        from citadel_retained_mountain_adapter import plan_adapter,checked_instance,checked_graph
        if not isinstance(mountain_inspection,dict):
            raise ValueError('Fresh actual native retained-mountain inspection required')
        plan=plan_adapter(candidate,mountain_inspection,'/Game/WorldRebuild/AegisCitadel_000000000001',MOUNTAIN_SHADER)
        checked_instance(mountain_inspection['instanceReadback'],plan['sourceInstance'],plan['sourceParent'],plan)
        checked_graph(mountain_inspection['parentGraphReadback'],plan)
        for name in ('scripts/unreal/citadel_retained_mountain_bridge.py',
            'scripts/unreal/citadel_retained_mountain_adapter.py',
            'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarMaterialInstanceReadback.cpp',
            'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarVectorParameterReadback.cpp'):
            bindings[name]=sha(root/name)
        face=candidate['terrainCarves'][0]['nativeReadback']['renderedFaces']
        file=(source_dir/face['path']).resolve();file.relative_to(source_dir)
        if sha(file)!=face['sha256']:raise ValueError('Native mountain render face bytes changed')
        bindings[str(file.relative_to(root)).replace('\\','/')]=face['sha256']
    return dict(schemaVersion=1, diagnosticOnly=True, surfaceMode=choices[0] or None,
        mountainMode=choices[1] or None, sourceRevision=source_dir.name, sourceBindings=bindings,
        sourcePackageHashes=copy.deepcopy({**candidate['sourceHashes'], **candidate['packageHashes']}),
        sourceMaterialRoles=list(assets['materialSpecs']),
        requiredSculptures=list(SCULPTURE_IDS) if choices[0] else [],
        masonryPalette=copy.deepcopy(PALETTE) if choices[0] else None,
        sculptureColor=SCULPTURE_COLOR[:] if choices[0] else None,
        luminanceShader=LUMINANCE_SHADER if choices[0] else None,
        sculptureShader=COLOR_SHADER if choices[0] else None,
        sculptureWeathering={key: copy.deepcopy(CARVED_SPEC[key]) for key in
            ('recipeVersion', 'grainPeriodCm', 'streakPeriodCm')} if choices[0] else None,
        sculptureAddsNormalInput=False,
        retainedMountainInspection=copy.deepcopy(mountain_inspection) if choices[1] else None,
        mountainShader=MOUNTAIN_SHADER if choices[1] else None,
        existingAlpineRecipe=copy.deepcopy(MOUNTAIN_MATERIAL_SPEC) if choices[1] else None,
        mountainTextureRepeatApplied=False, originalUvsAndNormalAndOrmPreserved=True,
        geometryChanged=False, collisionChanged=False, fixturesChanged=False,
        exposureChanged=False, canopyChanged=False, rendererStateVerified=False,
        nativeMaterialsCompiled=False, visualApproved=False, releaseAcceptance=False)


def verify_bindings(root, spec):
    root = Path(root).resolve()
    for name, expected in spec['sourceBindings'].items():
        file = (root / name).resolve()
        file.relative_to(root)
        if sha(file) != expected:
            raise ValueError('Material proposal source changed: ' + name)


def _primitive(value):
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('Nonfinite reflected material property')
        return value
    if hasattr(value, 'get_path_name'):
        return value.get_path_name()
    if all(hasattr(value, name) for name in ('r', 'g', 'b', 'a')):
        return [_primitive(getattr(value, name)) for name in ('r', 'g', 'b', 'a')]
    return str(value)


def _pins(unreal, node):
    # These native fields are protected from Python reflection in UE 5.8.
    document = json.loads(unreal.WarImportLibrary.describe_material_expression_pins(node))
    if (document.get('schemaVersion') != 1 or document.get('readOnly') is not True
            or document.get('available') is not True or document.get('expression') != node.get_path_name()
            or not isinstance(document.get('inputs'), list) or not isinstance(document.get('outputs'), list)
            or len(document['inputs']) > 256 or len(document['outputs']) > 1024):
        raise RuntimeError('Unavailable or wrong native material pin readback')
    mask_keys = ('mask', 'mask_r', 'mask_g', 'mask_b', 'mask_a')
    for index, row in enumerate(document['inputs']):
        if (set(row) != {'inputIndex', 'input_name', 'node', 'output_index', *mask_keys}
                or type(row['inputIndex']) is not int or row['inputIndex'] != index
                or not isinstance(row['input_name'], str)
                or not (row['node'] is None or isinstance(row['node'], str) and row['node'])
                or type(row['output_index']) is not int or row['output_index'] < (-1 if row['node'] is None else 0)):
            raise RuntimeError('Incomplete or reordered native material input: ' + node.get_path_name() + ' ' + json.dumps(row))
    for row in document['outputs']:
        if set(row) != {'output_name', *mask_keys} or not isinstance(row['output_name'], str):
            raise RuntimeError('Incomplete native material output')
    for row in [*document['inputs'], *document['outputs']]:
        if any(type(row[key]) is not int or row[key] not in (0, 1) for key in mask_keys):
            raise RuntimeError('Invalid native material channel mask')
    return document


def graph_readback(unreal, material):
    """Read native edge indices/masks, including disconnected inputs; no inferred wiring."""
    lib = unreal.MaterialEditingLibrary
    nodes = {}
    for node in lib.get_material_expressions(material):
        klass, name = node.get_class().get_name(), node.get_name()
        if (klass not in NODE_VALUES and klass!='MaterialExpressionVectorParameter') or name in nodes:
            raise RuntimeError('Unknown or duplicate material graph node: ' + klass)
        native = _pins(unreal, node)
        pins = {str(row['inputIndex']): {key: value for key, value in row.items() if key != 'inputIndex'}
                for row in native['inputs']}
        if klass=='MaterialExpressionVectorParameter':
            from citadel_retained_mountain_bridge import vector_readback
            values=vector_readback(unreal,node)
        else:
            values={key:_primitive(node.get_editor_property(key)) for key in NODE_VALUES[klass]}
            if klass=='MaterialExpressionCustom':
                if node.get_editor_property('output_type')!=unreal.CustomMaterialOutputType.CMOT_FLOAT3:
                    raise RuntimeError('Unsupported Custom material output type')
                values['output_type']='CMOT_FLOAT3'
        nodes[name] = dict(klass=klass, values=values, pins=pins,
            inputNames=[row['input_name'] for row in native['inputs']],
            upstream=[row['node'] for row in native['inputs']], outputs=native['outputs'])
    document = json.loads(unreal.WarImportLibrary.describe_material_roots(material))
    if (document.get('schemaVersion') != 1 or document.get('readOnly') is not True
            or document.get('available') is not True or document.get('material') != material.get_path_name()
            or not isinstance(document.get('roots'), dict) or set(document['roots']) != set(ROOT_PROPERTIES)):
        raise RuntimeError('Unavailable or incomplete native material roots')
    roots = document['roots']
    mask_keys = ('mask', 'mask_r', 'mask_g', 'mask_b', 'mask_a')
    for row in roots.values():
        if (set(row) != {'node', 'output_index', *mask_keys}
                or not (row['node'] is None or isinstance(row['node'], str) and row['node'])
                or type(row['output_index']) is not int or row['output_index'] < (-1 if row['node'] is None else 0)
                or any(type(row[key]) is not int or row[key] not in (0, 1) for key in mask_keys)):
            raise RuntimeError('Invalid native material root channel/index')
    return dict(nodes=nodes, roots=roots, materialProperties={key: _primitive(material.get_editor_property(key))
                                                           for key in MATERIAL_PROPERTIES},
        materialProfile=dict(name='retained_mountain_material_properties_v1',complete=True,keys=list(MATERIAL_PROPERTIES)))


def source_nodes(unreal, material, role, source_spec, revision):
    """Require the actual original texture-times-tint or untextured sculpture graph."""
    lib = unreal.MaterialEditingLibrary
    before = graph_readback(unreal, material)
    if any(before['roots'][key]['node'] for key in
           ('MP_WORLD_POSITION_OFFSET', 'MP_PIXEL_DEPTH_OFFSET', 'MP_MATERIAL_ATTRIBUTES', 'MP_DISPLACEMENT')):
        raise RuntimeError('Preserve independently changed displacement/attributes')
    base = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    for channel, prop in [('roughness', 'MP_ROUGHNESS'), ('metallic', 'MP_METALLIC')]:
        scalar = lib.get_material_property_input_node(material, getattr(unreal.MaterialProperty, prop))
        if (not isinstance(scalar, unreal.MaterialExpressionConstant)
                or abs(scalar.get_editor_property('r') - source_spec[channel]) > 1e-6):
            raise RuntimeError('Original scalar material policy changed: ' + channel)
    if role == 'carved_stone':
        if not isinstance(base, unreal.MaterialExpressionConstant3Vector):
            raise RuntimeError('Sculpture requires its original untextured constant color')
        wanted = source_spec['tint'] + [1]
        from citadel_stage_contract import lighting_readback
        lighting_readback(base.get_editor_property('constant'), dict(kind='linear_color', value=wanted))
        if before['roots']['MP_NORMAL']['node'] is not None:
            raise RuntimeError('Original sculpture acquired another normal graph')
        return before, base
    if not isinstance(base, unreal.MaterialExpressionMultiply):
        raise RuntimeError('Masonry requires the exact texture-times-tint graph')
    inputs = list(lib.get_inputs_for_material_expression(material, base))
    if (len(inputs) != 2 or not isinstance(inputs[0], unreal.MaterialExpressionTextureSample)
            or not isinstance(inputs[1], unreal.MaterialExpressionConstant3Vector)):
        raise RuntimeError('Original masonry A/B pins changed')
    texture, tint = inputs
    expected = '/Game/WorldRebuild/AegisCitadel_' + revision + '/Textures/T_' + Path(source_spec['baseColor']).stem + '_baseColor'
    if texture.texture.get_path_name().split('.')[0] != expected:
        raise RuntimeError('Masonry albedo differs from its source texture')
    from citadel_stage_contract import lighting_readback
    lighting_readback(tint.constant, dict(kind='linear_color', value=source_spec['tint'] + [1]))
    edge = _pins(unreal, base)['inputs'][0]
    if [edge[k] for k in ('output_index', 'mask_r', 'mask_g', 'mask_b', 'mask_a')] != [0, 1, 1, 1, 0]:
        raise RuntimeError('Masonry must consume the original RGB texture output')
    if any(n is not None for n in lib.get_inputs_for_material_expression(material, texture)):
        raise RuntimeError('Preserve independently changed original texture coordinates')
    return before, texture


def checked_graph_change(before, after, additions, color_name):
    expected = copy.deepcopy(before)
    for name, row in additions.items():
        if name in expected['nodes']:
            raise RuntimeError('New material node overwrote source graph')
        expected['nodes'][name] = copy.deepcopy(row)
    expected['roots']['MP_BASE_COLOR'] = dict(node=color_name, output_index=0,
        mask=0, mask_r=0, mask_g=0, mask_b=0, mask_a=0)
    if after != expected:
        raise RuntimeError('Material treatment changed an unsigned graph edge, UV, normal, ORM or property')


def _new_shader(unreal, material, description, code, sources):
    lib = unreal.MaterialEditingLibrary
    shader = lib.create_material_expression(material, unreal.MaterialExpressionCustom)
    shader.set_editor_property('description', description)
    shader.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for name in sources:
        row = unreal.CustomInput()
        row.set_editor_property('input_name', name)
        inputs.append(row)
    shader.set_editor_property('inputs', inputs)
    shader.set_editor_property('code', code)
    for name, (node, output) in sources.items():
        if not lib.connect_material_expressions(node, output, shader, name):
            raise RuntimeError('Cannot connect exact private albedo pin: ' + name)
    if not lib.connect_material_property(shader, '', unreal.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Cannot connect exact private base color root')
    if (shader.get_editor_property('code') != code
            or shader.get_editor_property('output_type') != unreal.CustomMaterialOutputType.CMOT_FLOAT3):
        raise RuntimeError('Private shader source/output readback differs')
    rows = shader.get_editor_property('inputs')
    if [str(row.get_editor_property('input_name')) for row in rows] != list(sources):
        raise RuntimeError('Private shader pin names/order differ')
    native = _pins(unreal, shader)
    if [row['input_name'] for row in native['inputs']] != list(sources):
        raise RuntimeError('Native private shader pin names/order differ')
    for edge in native['inputs']:
        name = edge['input_name']
        source, output = sources[name]
        outputs = _pins(unreal, source)['outputs']
        index = edge['output_index']
        if edge['node'] != source.get_name() or type(index) is not int or not 0 <= index < len(outputs):
            raise RuntimeError('Private shader has a disconnected/wrong source')
        keys = ('mask', 'mask_r', 'mask_g', 'mask_b', 'mask_a')
        expected_mask = [outputs[0][key] for key in keys]
        if output == 'RGB' and expected_mask != [1, 1, 1, 1, 0]:
            raise RuntimeError('Private albedo requires the actual RGB source output')
        if index != 0 or [edge[k] for k in keys] != expected_mask:
            raise RuntimeError('Private shader has a changed source output/mask')
    return shader


def _compile_save(unreal, material, before, added_nodes, shader):
    after = graph_readback(unreal, material)
    additions = {node.get_name(): after['nodes'][node.get_name()] for node in added_nodes}
    checked_graph_change(before, after, additions, shader.get_name())
    errors = unreal.MaterialEditingLibrary.recompile_material(material)
    if errors:
        raise RuntimeError('Private material shader compilation failed: ' + str(errors))
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Cannot save fresh owned private material')
    saved = graph_readback(unreal, unreal.load_asset(material.get_path_name()))
    if saved != after:
        raise RuntimeError('Saved material graph readback differs')
    return dict(material=material.get_path_name(), beforeGraph=before, afterGraph=saved,
        compileErrors=list(errors or []), editorGraphReadbackMatches=True,
        coldProcessVerified=False, rendererStateVerified=False, visualApproved=False)


def create_surfaces(unreal, destination, revision, specs, spec, duplicate):
    if not re.fullmatch('/Game/WorldRebuild/AegisCitadel_[a-f0-9]{12}', destination):
        raise RuntimeError('Only an exact fresh private study root is allowed')
    materials, audits = {}, {}
    if not spec['surfaceMode']:
        return materials, audits
    lib = unreal.MaterialEditingLibrary
    for role in (*PALETTE, 'carved_stone'):
        source = '/Game/WorldRebuild/AegisCitadel_' + revision + '/Materials/M_' + role
        if source not in spec['sourcePackageHashes']:
            raise RuntimeError('Material is outside the signed protected source closure')
        target = destination + '/Materials/M_PrivateSurface_' + role
        duplicate(source, target)
        material = unreal.load_asset(target)
        before, original = source_nodes(unreal, material, role, specs[role], revision)
        color = SCULPTURE_COLOR if role == 'carved_stone' else PALETTE[role]
        palette = lib.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
        palette.constant = unreal.LinearColor(*color, 1)
        from citadel_stage_contract import lighting_readback
        lighting_readback(palette.constant, dict(kind='linear_color', value=color + [1]))
        nodes = [palette]
        if role == 'carved_stone':
            position = lib.create_material_expression(material, unreal.MaterialExpressionWorldPosition)
            nodes.append(position)
            code, inputs = spec['sculptureShader'], dict(P=(position, ''), Base=(palette, ''))
        else:
            code, inputs = LUMINANCE_SHADER, dict(Raw=(original, 'RGB'), Palette=(palette, ''))
        shader = _new_shader(unreal, material, 'Bastion private albedo study ' + role, code, inputs)
        audits[role] = _compile_save(unreal, material, before, [*nodes, shader], shader)
        materials[source] = material
    return materials, audits


def create_mountain(unreal, destination, source_dir, candidate, spec, duplicate):
    from citadel_retained_mountain_bridge import create_mountain as create_retained_mountain
    return create_retained_mountain(unreal,destination,source_dir,candidate,spec,duplicate)


def actor_binding_readback(before, after, replacements):
    expected = copy.deepcopy(before)
    bindings = []
    for row in expected['components']:
        if 'materials' not in row:
            continue
        for slot, source in enumerate(row['materials']):
            package = source.split('.')[0] if source else None
            if package in replacements:
                row['materials'][slot] = replacements[package]
                bindings.append(dict(component=row['name'], slot=slot, source=source,
                                     actualMaterial=replacements[package]))
    if after != expected:
        raise RuntimeError('Private material binding changed actor/mesh/transform/collision/visibility')
    return bindings


def verify_role_coverage(readbacks, material_paths):
    counts = {path: 0 for path in material_paths}
    for row in readbacks:
        for binding in row['bindings']:
            if binding['actualMaterial'] in counts:
                counts[binding['actualMaterial']] += 1
    if any(count == 0 for count in counts.values()):
        raise RuntimeError('Private material study is missing an actual component role binding')
    return counts


def checked_sculpture_faces(document, mesh_path, slot):
    if (document.get('schemaVersion') != 1 or document.get('readOnly') is not True
            or document.get('available') is not True or document.get('valid') is not True
            or type(document.get('invalidValues')) is not int or document['invalidValues'] != 0
            or document.get('mesh') != mesh_path or type(document.get('lod')) is not int or document['lod'] != 0
            or document.get('policy') != 'actual_render_index_order_oriented_triangle_corners'):
        raise RuntimeError('Actual saved sculpture render-face readback is unavailable')
    faces = document.get('triangles')
    if not isinstance(faces, list) or not faces or len(faces) > 200000:
        raise RuntimeError('Sculpture render-face readback is empty or unbounded')
    if any(type(face.get('materialIndex')) is not int or face['materialIndex'] < 0 for face in faces):
        raise RuntimeError('Sculpture render material indices are unavailable')
    count = sum(face['materialIndex'] == slot for face in faces)
    if count == 0:
        raise RuntimeError('Sculpture material override has no actual rendered triangles')
    return count


def sculpture_binding_readbacks(unreal, loaded_actors, spec, material):
    """Unused material slots must not masquerade as coverage of the five figures."""
    result = []
    slot = spec['sourceMaterialRoles'].index('carved_stone')
    for identity in spec['requiredSculptures']:
        label = 'Bastion reference furnishing_' + identity
        matches = [actor for actor in loaded_actors if actor.get_actor_label() == label]
        if len(matches) != 1 or not isinstance(matches[0], unreal.StaticMeshActor):
            raise RuntimeError('Exactly one retained sculpture is required: ' + identity)
        actor = matches[0]
        component, mesh = actor.static_mesh_component, actor.static_mesh_component.static_mesh
        wanted_mesh = '/Game/WorldRebuild/AegisCitadel_' + spec['sourceRevision'] + '/Meshes/SM_furnishing_' + identity
        if (not mesh or mesh.get_path_name().split('.')[0] != wanted_mesh
                or wanted_mesh not in spec['sourcePackageHashes'] or component.get_material(slot) != material):
            raise RuntimeError('Retained sculpture mesh/material binding differs: ' + identity)
        visibility = dict(actorHidden=actor.get_editor_property('hidden'),
            componentVisible=component.get_editor_property('visible'),
            componentHiddenInGame=component.get_editor_property('hidden_in_game'))
        if any(type(value) is not bool for value in visibility.values()) or visibility != dict(
                actorHidden=False, componentVisible=True, componentHiddenInGame=False):
            raise RuntimeError('Retained sculpture native visibility differs: ' + identity)
        raw = unreal.WarImportLibrary.describe_static_mesh_rendered_faces(mesh, 0)
        if not isinstance(raw, str) or len(raw) > 128 * 1024 * 1024:
            raise RuntimeError('Sculpture native render-face readback is unbounded')
        document = json.loads(raw)
        count = checked_sculpture_faces(document, mesh.get_path_name(), slot)
        result.append(dict(id=identity, actor=actor.get_path_name(), component=component.get_path_name(),
            mesh=mesh.get_path_name(), materialSlot=slot, actualMaterial=component.get_material(slot).get_path_name(),
            visibility=visibility, lod0MaterialTriangles=count, renderedFacesSha256=hashlib.sha256(raw.encode()).hexdigest(),
            editorBindingVerified=True, gameFrameVisibilityVerified=False, visualApproved=False))
    return result
