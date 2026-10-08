"""Original soft weather shader; intentional effect geometry has no collision."""
import unreal


def weather_material(assets):
    material = assets.tools.create_asset('M_LocalWeather', assets.folder+'/Materials', unreal.Material, unreal.MaterialFactoryNew())
    if not material: raise RuntimeError('Cannot create private weather material')
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    lib = unreal.MaterialEditingLibrary
    def node(kind, **properties):
        result = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
        for name, value in properties.items(): result.set_editor_property(name, value)
        return result
    def wire(value, output, target, pin):
        if not lib.connect_material_expressions(value, output, target, pin): raise RuntimeError('Cannot connect weather shader')
    def binary(kind, a, b, output_a='', output_b=''):
        result = node(kind); wire(a, output_a, result, 'A'); wire(b, output_b, result, 'B'); return result
    uv = node('TextureCoordinate')
    centre = node('Constant2Vector', r=.5, g=.5)
    delta = binary('Subtract', uv, centre)
    distance = binary('DotProduct', delta, delta)
    scale = node('Constant', r=4)
    radius = binary('Multiply', distance, scale)
    fade = node('OneMinus'); wire(radius, '', fade, '')
    clamp = node('Clamp', min_default=0, max_default=1); wire(fade, '', clamp, '')
    softness = binary('Multiply', clamp, clamp)
    vertex = node('VertexColor')
    alpha = binary('Multiply', softness, vertex, '', 'A')
    tint = node('Constant3Vector', constant=unreal.LinearColor(.72, .82, .92, 1))
    glow = binary('Multiply', tint, vertex, '', 'R')
    for value, output, pin in [(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                              (alpha, '', unreal.MaterialProperty.MP_OPACITY)]:
        if not lib.connect_material_property(value, output, pin): raise RuntimeError('Cannot bind weather output: '+str(pin))
    errors = lib.recompile_material(material)
    if errors: raise RuntimeError('Weather shader compiler errors: '+str(list(errors)))
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False): raise RuntimeError('Cannot save weather shader')
    return material
