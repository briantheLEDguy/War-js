"""Native metre-scaled regional surface graphs; no mesh or shared material mutation."""
import math
import unreal
from t1_surface_variation import validate_variation, validate_substrate, validate_shorelines


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
    def texture(kind, coordinates, channels=None):
        sample = node('TextureSample', texture=assets.texture((channels or recipe)[kind], kind == 'normal'),
            sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind == 'normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        wire(coordinates, '', sample, 'UVs')
        return sample
    def lerp(a, b, alpha, a_pin='', b_pin=''):
        result = node('LinearInterpolate'); wire(a, a_pin, result, 'A'); wire(b, b_pin, result, 'B'); wire(alpha, '', result, 'Alpha'); return result
    def clamp(value):
        result = node('Clamp', min_default=0, max_default=1); wire(value, '', result, 'Input'); return result
    samples = {}
    for kind in ('color', 'normal'):
        samples[kind] = texture(kind, uv)
    tint = node('Constant3Vector', constant=unreal.LinearColor(*recipe['tint'][:3], 1))
    color = binary('Multiply', samples['color'], tint, 'RGB')
    normal_detail, normal_pin = samples['normal'], 'RGB'
    variation_recipe = recipe.get('surfaceVariation')
    if variation_recipe:
        validate_variation(variation_recipe)
        angle = variation_recipe['secondaryAngle']
        # Different physical scales/rotations share the admitted channels; world coordinates prevent tile seams.
        rotated_u = binary('Subtract', binary('Multiply', y, constant(math.cos(angle))), binary('Multiply', negative_x, constant(math.sin(angle))))
        rotated_v = binary('Add', binary('Multiply', y, constant(math.sin(angle))), binary('Multiply', negative_x, constant(math.cos(angle))))
        secondary_uv = binary('Divide', binary('AppendVector', rotated_u, rotated_v), constant(recipe['tileMetres']*variation_recipe['secondaryScale']*100))
        mask_sample = texture('color', binary('Divide', axes, constant(variation_recipe['maskMetres']*100)))
        def channel_mask(sample):
            low,high=variation_recipe['channelRange']
            weight=clamp(binary('Divide',binary('Subtract',sample,constant(low),'R'),constant(high-low)))
            return binary('Multiply',binary('Multiply',weight,weight),binary('Subtract',constant(3),binary('Multiply',weight,constant(2))))
        mask = binary('Add', constant(variation_recipe['minimumMix']), binary('Multiply', channel_mask(mask_sample),
            constant(variation_recipe['maximumMix']-variation_recipe['minimumMix'])))
        color = binary('Multiply', lerp(samples['color'], texture('color', secondary_uv), mask, 'RGB', 'RGB'), tint)
        normal_detail = node('Normalize'); wire(lerp(samples['normal'], texture('normal', secondary_uv), mask, 'RGB', 'RGB'), '', normal_detail, 'VectorInput')
        normal_pin = ''
    substrate = recipe.get('substrate')
    if substrate:
        if recipe['softVerge'] or not variation_recipe: raise ValueError('Substrate requires a varied opaque terrain')
        validate_substrate(substrate)
        soil_uv = binary('Divide', axes, constant(substrate['tileMetres']*100))
        soil_color = texture('color', soil_uv, substrate)
        soil_tint = node('Constant3Vector', constant=unreal.LinearColor(*substrate['tint'], 1))
        soil_color = binary('Multiply', soil_color, soil_tint, 'RGB')
        patch_uv = binary('Divide', axes, constant(substrate['patchMetres']*100))
        secondary_patch_uv = binary('Divide', binary('AppendVector', rotated_u, rotated_v), constant(substrate['patchMetres']*1.73*100))
        patch = lerp(texture('color', patch_uv), texture('color', secondary_patch_uv), constant(.4), 'R', 'R')
        low, high = substrate['maskRange']
        patch = clamp(binary('Divide', binary('Subtract', patch, constant(low)), constant(high-low)))
        patch = binary('Multiply', binary('Multiply', patch, patch), binary('Subtract', constant(3), binary('Multiply', patch, constant(2))))
        normal = node('VertexNormalWS')
        nz = node('ComponentMask', r=False, g=False, b=True, a=False); wire(normal, '', nz, 'Input')
        slope = clamp(binary('Divide', binary('Subtract', constant(.98), nz), constant(.18)))
        coating = clamp(binary('Add', binary('Multiply', patch, constant(substrate['patchStrength'])), binary('Multiply', slope, constant(substrate['slopeStrength']))))
        color = lerp(color, soil_color, coating)
        mixed_normal = lerp(normal_detail, texture('normal', soil_uv, substrate), coating, normal_pin, 'RGB')
        normal_detail = node('Normalize'); wire(mixed_normal, '', normal_detail, 'VectorInput'); normal_pin = ''
    shores=recipe.get('shorelines')
    if shores:
        validate_shorelines(shores)
        if not substrate:raise ValueError('Shore transitions need the admitted regional substrate')
        world_height=node('ComponentMask',r=False,g=False,b=True,a=False);wire(world,'',world_height,'Input')
        wet=constant(0)
        for shore in shores:
            centre=node('Constant3Vector',constant=unreal.LinearColor(shore['z']*100,shore['x']*100,shore['waterY']*100,1))
            distance=binary('Distance',world,centre)
            radial=clamp(binary('Divide',binary('Subtract',constant(shore['radius']*100),distance),constant(1200)))
            delta=node('Abs');wire(binary('Subtract',world_height,constant(shore['waterY']*100)),'',delta,'Input')
            band=clamp(binary('Subtract',constant(1),binary('Divide',delta,constant(80))))
            band=binary('Multiply',binary('Multiply',band,band),binary('Subtract',constant(3),binary('Multiply',band,constant(2))))
            wet=binary('Max',wet,binary('Multiply',radial,band))
        color=lerp(color,binary('Multiply',soil_color,constant(.72)),binary('Multiply',wet,constant(.65)))
    if not recipe['softVerge']:

        if variation_recipe:
            macro_sample = texture('color', binary('Divide', axes, constant(variation_recipe['macroMetres']*100)))
            minimum = variation_recipe['macroMinimum']
            variation = binary('Add', constant(minimum), binary('Multiply', channel_mask(macro_sample), constant(1-minimum)))
        else:
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
        rock_layer = recipe.get('rockLayer')
        if rock_layer:
            z = node('ComponentMask', r=False, g=False, b=True, a=False); wire(world, '', z, 'Input')
            coordinates = [binary('AppendVector', y, z), binary('AppendVector', negative_x, z), axes]
            weights=[]; values=[]
            for axis, coordinates_for_axis in enumerate(coordinates):
                n = node('ComponentMask', r=axis==0, g=axis==1, b=axis==2, a=False); wire(normal, '', n, 'Input')
                squared=binary('Multiply',n,n); weights.append(binary('Multiply',squared,squared))
                stone=texture('color',binary('Divide',coordinates_for_axis,constant(rock_layer['tileMetres']*100)),rock_layer)
                values.append(binary('Multiply',stone,weights[-1],'RGB'))
            # Blend projections over face directions, so steep slopes do not stretch into flat colour bands.
            rock=binary('Divide',binary('Add',binary('Add',values[0],values[1]),values[2]),binary('Add',binary('Add',weights[0],weights[1]),weights[2]))
            rock_tint=node('Constant3Vector',constant=unreal.LinearColor(*rock_layer['tint'],1)); rock=binary('Multiply',rock,rock_tint)
            rock_uv=binary('Divide',axes,constant(rock_layer['tileMetres']*100))
            mixed_normal=lerp(normal_detail,texture('normal',rock_uv,rock_layer),clamped,normal_pin,'RGB')
            normal_detail=node('Normalize');wire(mixed_normal,'',normal_detail,'VectorInput');normal_pin=''
        elif variation_recipe:
            grain = binary('Add', constant(.8), binary('Multiply', samples['color'], constant(.4), 'R'))
            rock = binary('Multiply', rock, grain)
        blend = node('LinearInterpolate'); wire(color, '', blend, 'A'); wire(rock, '', blend, 'B'); wire(clamped, '', blend, 'Alpha')
        color = blend
    else:
        color = binary('Multiply', color, constant(recipe['macroMinimum']))
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('translucency_lighting_mode', unreal.TranslucencyLightingMode.TLM_SURFACE)
        vertex = node('VertexColor')
        verge = binary('Multiply', vertex, constant(1), 'A')
        if variation_recipe:
            noise = texture('color', binary('Divide', axes, constant(variation_recipe['vergeMetres']*100)))
            perturbation = binary('Multiply', binary('Subtract', noise, constant(.5), 'R'),
                binary('Multiply', verge, binary('Subtract', constant(1), verge)))
            verge = clamp(binary('Add', verge, binary('Multiply', perturbation, constant(1.6))))
        alpha = binary('Multiply', verge, samples['color'], '', 'A')
        lib.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY)
    for value, pin, output in [(color, unreal.MaterialProperty.MP_BASE_COLOR, ''),
        (normal_detail, unreal.MaterialProperty.MP_NORMAL, normal_pin),
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
