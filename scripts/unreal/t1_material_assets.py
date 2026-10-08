"""Native metre-scaled regional surface graphs; no mesh or shared material mutation."""
import unreal


def regional_material(assets, key, recipe):
    material = assets.tools.create_asset('M_'+key, assets.folder+'/Materials', unreal.Material, unreal.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Cannot create regional surface material')
    lib = unreal.MaterialEditingLibrary
    node_count = 0
    def node(kind, **properties):
        nonlocal node_count
        result = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind), node_count%6*220, node_count//6*180)
        node_count += 1
        for name, value in properties.items():
            result.set_editor_property(name, value)
        return result
    def wire(output, pin, target, input_pin):
        # Unreal shortens the single Input pin to an unnamed graph pin.
        if input_pin == 'Input': input_pin = ''
        if not lib.connect_material_expressions(output, pin, target, input_pin):
            raise RuntimeError('Cannot connect regional material graph: '+input_pin)
    def constant(value): return node('Constant', r=value)
    def binary(kind, left, right, left_pin='', right_pin=''):
        result = node(kind); wire(left, left_pin, result, 'A'); wire(right, right_pin, result, 'B'); return result
    world = node('WorldPosition')
    x = node('ComponentMask', r=True, g=False, b=False, a=False); wire(world, '', x, 'Input')
    y = node('ComponentMask', r=False, g=True, b=False, a=False); wire(world, '', y, 'Input')
    negative_x = binary('Multiply', x, constant(-1))
    axes = binary('AppendVector', y, negative_x)
    uv = binary('Divide', axes, constant(recipe['tileMetres']*100))
    samples = {}
    for kind in ('color', 'normal'):
        sample = node('TextureSample', texture=assets.texture(recipe[kind], kind == 'normal'),
            sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind == 'normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        wire(uv, '', sample, 'UVs'); samples[kind] = sample
    tint = node('Constant3Vector', constant=unreal.LinearColor(*recipe['tint'][:3], 1))
    color = binary('Multiply', samples['color'], tint, 'RGB')
    if not recipe['softVerge']:
        waves = []
        for coordinate, metres in zip((x, y), recipe['macroMetres']):
            frequency = binary('Divide', coordinate, constant(metres*100))
            sine = node('Sine'); wire(frequency, '', sine, 'Input'); waves.append(sine)
        summed = binary('Add', waves[0], waves[1])
        minimum = recipe['macroMinimum']
        variation = binary('Add', binary('Multiply', summed, constant((1-minimum)/4)), constant((1+minimum)/2))
        color = binary('Multiply', color, variation)
        normal = node('VertexNormalWS')
        nz = node('ComponentMask', r=False, g=False, b=True, a=False); wire(normal, '', nz, 'Input')
        low, high = recipe['slopeNormalRange']
        slope = binary('Divide', binary('Subtract', constant(high), nz), constant(high-low))
        clamped = node('Clamp', min_default=0, max_default=1); wire(slope, '', clamped, 'Input')
        rock = node('Constant3Vector', constant=unreal.LinearColor(*recipe['rockColor'], 1))
        blend = node('LinearInterpolate'); wire(color, '', blend, 'A'); wire(rock, '', blend, 'B'); wire(clamped, '', blend, 'Alpha')
        color = blend
    else:
        color = binary('Multiply', color, constant(recipe['macroMinimum']))
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('translucency_lighting_mode', unreal.TranslucencyLightingMode.TLM_SURFACE)
        vertex = node('VertexColor')
        alpha = binary('Multiply', vertex, samples['color'], 'A', 'A')
        lib.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY)
    for value, pin, output in [(color, unreal.MaterialProperty.MP_BASE_COLOR, ''),
        (samples['normal'], unreal.MaterialProperty.MP_NORMAL, 'RGB'),
        (constant(recipe['roughness']), unreal.MaterialProperty.MP_ROUGHNESS, ''),
        (constant(recipe['metallic']), unreal.MaterialProperty.MP_METALLIC, '')]:
        if not lib.connect_material_property(value, output, pin):
            raise RuntimeError('Cannot connect regional material property')
    errors = lib.recompile_material(material)
    if errors:
        raise RuntimeError('Regional material compiler errors: '+str(list(errors)))
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Cannot save regional material')
    return material, node_count
