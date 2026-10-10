"""Private, opt-in rock material adaptation. Mixed atlas coordinates are never retiled."""
import hashlib
import json
import math

ATLAS = '/Game/Medieval_Environment/Medieval_Houses_Vol2/Textures/T_MH_02_Atlas_02_'
CHANNELS = {'Texture_Base_Color': 'BC', 'Texture_Normal': 'N', 'Texture_RMA': 'RMA'}


def rock_scale_recipe(textures, role, scale=2):
    if not isinstance(scale, (int, float)) or isinstance(scale, bool) or not math.isfinite(scale) or not 1 < scale <= 3:
        raise ValueError('Rock detail scale must be finite, greater than one and at most three')
    # Exact channel admission prevents silently scaling an atlas containing timber,
    # thatch, windows or other fixed features. Colour, normal and RMA move together.
    expected = {key: ATLAS + suffix + '.T_MH_02_Atlas_02_' + suffix for key, suffix in CHANNELS.items()}
    if role != 'wall' or any(textures.get(key) != value for key, value in expected.items()):
        return None
    return dict(scale=scale, channels=expected, uvChannel=0, geometryChanged=False, appearanceApproved=False)


def adapt_rock_material(source, destination, scale=2, cache=None):
    import unreal
    if not destination.startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_') or '..' in destination:
        raise ValueError('Rock adaptation requires an isolated T1 study destination')
    cache = {} if cache is None else cache
    visiting = set()
    lib = unreal.MaterialEditingLibrary
    if not isinstance(source, unreal.MaterialInstanceConstant): return source, None
    textures = {str(name): lib.get_material_instance_texture_parameter_value(source, name) for name in lib.get_texture_parameter_names(source)}
    paths = {key: texture.get_path_name() if texture else None for key, texture in textures.items()}
    recipe = rock_scale_recipe(paths, 'wall' if source.get_name().startswith('MI_wall_') else 'original', scale)
    if recipe is None: return source, None
    tools = unreal.AssetToolsHelpers.get_asset_tools()

    def duplicate(node):
        key = (node.get_path_name(), scale)
        if key in cache: return cache[key]
        if key in visiting or len(visiting) >= 8: raise RuntimeError('Cyclic or unbounded material parent chain')
        visiting.add(key)
        name = ('M_' if isinstance(node, unreal.Material) else 'MI_') + 'RockDetail_' + hashlib.sha256((key[0] + str(scale)).encode()).hexdigest()[:16]
        if unreal.EditorAssetLibrary.does_asset_exist(destination + '/' + name): raise RuntimeError('Preserve existing material study')
        copy = tools.duplicate_asset(name, destination, node)
        if not copy: raise RuntimeError('Cannot isolate rock material graph')
        if isinstance(node, unreal.Material):
            roots = json.loads(unreal.WarImportLibrary.describe_material_roots(node))
            if not roots.get('available') or roots['roots']['MP_CUSTOMIZED_UVS0']['node'] is not None:
                raise RuntimeError('Rock parent already customizes UV0; explicit review required')
            samples = [node for node in lib.get_material_expressions(copy) if isinstance(node, unreal.MaterialExpressionTextureSampleParameter2D)
                and str(node.get_editor_property('parameter_name')) in CHANNELS]
            if len(samples) != 3 or {str(node.get_editor_property('parameter_name')) for node in samples} != set(CHANNELS):
                raise RuntimeError('Rock parent does not expose the three admitted texture channels')
            if any(input_node is not None for node in samples for input_node in lib.get_inputs_for_material_expression(copy, node)):
                raise RuntimeError('Preserve independently authored rock texture coordinates')
            original_pins = {node.get_name(): json.loads(unreal.WarImportLibrary.describe_material_expression_pins(node)) for node in lib.get_material_expressions(copy)}
            uv = lib.create_material_expression(copy, unreal.MaterialExpressionTextureCoordinate)
            uv.set_editor_property('coordinate_index', 0);uv.set_editor_property('u_tiling', scale);uv.set_editor_property('v_tiling', scale)
            for node in samples:
                if not lib.connect_material_expressions(uv, '', node, 'UVs'): raise RuntimeError('Cannot bind coherent rock PBR UV scale')
            if [uv.get_editor_property(k) for k in ('coordinate_index', 'u_tiling', 'v_tiling')] != [0, scale, scale]:
                raise RuntimeError('Rock UV scale readback failed')
            for node in lib.get_material_expressions(copy):
                if node.get_name() not in original_pins: continue
                previous = original_pins[node.get_name()];actual = json.loads(unreal.WarImportLibrary.describe_material_expression_pins(node))
                if not previous.get('available') or not actual.get('available'): raise RuntimeError('Rock graph edge readback unavailable')
                if node in samples:
                    # Coordinates are the first native texture input; preserve mip and derivative inputs.
                    if actual['inputs'][0]['node'] != uv.get_name(): raise RuntimeError('Rock texture coordinate edge changed')
                    actual['inputs'][0] = previous['inputs'][0]
                if actual != previous: raise RuntimeError('Rock adaptation changed an unrelated graph edge')
            actual_roots = json.loads(unreal.WarImportLibrary.describe_material_roots(copy))
            if actual_roots.get('roots') != roots['roots']: raise RuntimeError('Rock adaptation changed material roots')
            lib.recompile_material(copy)
        else:
            parent = node.get_editor_property('parent')
            if not parent: raise RuntimeError('Rock instance has no source parent')
            lib.set_material_instance_parent(copy, duplicate(parent))
            previous = json.loads(unreal.WarImportLibrary.describe_material_instance(node))
            actual = json.loads(unreal.WarImportLibrary.describe_material_instance(copy))
            # Native typed readback covers the direct-parent instance. Higher inherited
            # instances retain their duplicated settings and verify effective values below.
            if previous.get('available'):
                if not actual.get('available'): raise RuntimeError('Rock instance lost typed readback')
                for field in ('localOverrides', 'effectiveGlobalParameters', 'instanceProperties', 'hasStaticPermutationResource'):
                    if previous[field] != actual[field]: raise RuntimeError('Rock instance overrides changed')
        if not unreal.EditorAssetLibrary.save_loaded_asset(copy, only_if_is_dirty=False): raise RuntimeError('Cannot save isolated rock graph')
        cache[key] = copy
        visiting.remove(key)
        return copy

    adapted = duplicate(source)
    for name in lib.get_texture_parameter_names(source):
        if lib.get_material_instance_texture_parameter_value(source, name) != lib.get_material_instance_texture_parameter_value(adapted, name):
            raise RuntimeError('Rock adaptation replaced source texture')
    for name in lib.get_vector_parameter_names(source):
        old = lib.get_material_instance_vector_parameter_value(source, name);new = lib.get_material_instance_vector_parameter_value(adapted, name)
        if [getattr(old, k) for k in ('r', 'g', 'b', 'a')] != [getattr(new, k) for k in ('r', 'g', 'b', 'a')]:
            raise RuntimeError('Rock adaptation changed source tint/normal strength')
    for name in lib.get_scalar_parameter_names(source):
        if lib.get_material_instance_scalar_parameter_value(source, name) != lib.get_material_instance_scalar_parameter_value(adapted, name):
            raise RuntimeError('Rock adaptation changed source scalar')
    return adapted, dict(source=source.get_path_name(), adapted=adapted.get_path_name(), **recipe, sourceTexturesAndParametersRetained=True)
