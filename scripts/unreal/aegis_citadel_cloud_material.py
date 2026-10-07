"""Original private storm-cloud study; actual renderer and visual review remain required."""
from citadel_stage_contract import lighting_readback

SPEC = dict(recipeVersion=3, domain='volume', blend='additive', layerBottomKm=.65, layerHeightKm=1.8,
    albedo=[.68,.73,.82,1], extinctionPerCm=.00013, shapePeriodCm=90000,
    detailPeriodCm=18000, windCmPerSecond=50, coverageThreshold=.43,
    erosionStrength=.12, densityContrast=6, multiScatteringOctaves=1,
    rayMarchVolumeShadow=False, originalShader=True, visualApproved=False)

SHADER = r'''
struct BastionCloudNoise {
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
BastionCloudNoise noise;
float3 advected = P + float3(T * @WIND@, 0, 0);
float3 q = advected / @SHAPE_PERIOD@ + float3(3.7, 8.3, 2.4);
float broad = noise.Value(q) * .60 + noise.Value(q * 2.03 + 5.2) * .30
            + noise.Value(q * 4.17 - 2.8) * .10;
float erosion = noise.Value(advected / @DETAIL_PERIOD@ + float3(6.2, 1.4, 9.1));
// CloudSampleAttribute supplies the actual planet-relative layer fraction.
// Absolute world Z would clip the volume incorrectly after origin changes.
float envelope = smoothstep(0, .06, H) * (1 - smoothstep(.48, 1, H));
float billows = saturate((broad - @COVERAGE@ - erosion * @EROSION@) * @CONTRAST@);
return billows * envelope * @EXTINCTION@;
'''
for token, key in (('WIND','windCmPerSecond'),('SHAPE_PERIOD','shapePeriodCm'),
        ('DETAIL_PERIOD','detailPeriodCm'),('COVERAGE','coverageThreshold'),
        ('EROSION','erosionStrength'),('CONTRAST','densityContrast'),('EXTINCTION','extinctionPerCm')):
    SHADER=SHADER.replace('@'+token+'@',str(SPEC[key]))
if '@' in SHADER:raise ValueError('Original cloud density has an unbound recipe input')


def create_cloud_material(unreal, destination, record):
    lib = unreal.MaterialEditingLibrary
    path = destination + '/Materials/M_BastionStormCloud'
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError('Preserve the existing authored cloud study')
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_BastionStormCloud',
        destination + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Cannot create the owned original storm material')
    record(path)
    requested = dict(material_domain=unreal.MaterialDomain.MD_VOLUME,
        blend_mode=unreal.BlendMode.BLEND_ADDITIVE, used_with_volumetric_cloud=True)
    for name, value in requested.items():
        material.set_editor_property(name, value)
        if material.get_editor_property(name) != value:
            raise RuntimeError('Native storm material policy differs: ' + name)
    albedo = lib.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
    albedo.constant = unreal.LinearColor(r=SPEC['albedo'][0],g=SPEC['albedo'][1],b=SPEC['albedo'][2],a=1)
    lighting_readback(albedo.constant, dict(kind='linear_color',value=SPEC['albedo']))
    if not lib.connect_material_property(albedo, '', unreal.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Storm albedo is disconnected')
    position = lib.create_material_expression(material, unreal.MaterialExpressionWorldPosition)
    height = lib.create_material_expression(material, unreal.MaterialExpressionCloudSampleAttribute)
    time = lib.create_material_expression(material, unreal.MaterialExpressionTime)
    shader = lib.create_material_expression(material, unreal.MaterialExpressionCustom)
    shader.set_editor_property('description', 'Bastion layered storm billows and erosion')
    shader.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    inputs = []
    for name in ('P','H','T'):
        entry = unreal.CustomInput(); entry.set_editor_property('input_name',name); inputs.append(entry)
    shader.set_editor_property('inputs',inputs); shader.set_editor_property('code',SHADER)
    for node, output, name in ((position,'','P'),(height,'NormAltitudeInLayer','H'),(time,'','T')):
        if not lib.connect_material_expressions(node,output,shader,name):
            raise RuntimeError('Storm density input is disconnected: ' + name)
    if (not lib.connect_material_property(shader,'',unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
            or lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_SUBSURFACE_COLOR) != shader
            or shader.get_editor_property('code') != SHADER):
        raise RuntimeError('The actual storm extinction graph differs')
    advanced = lib.create_material_expression(material, unreal.MaterialExpressionVolumetricAdvancedMaterialOutput)
    settings = dict(const_phase_g=.35,const_phase_g2=-.2,const_phase_blend=.7,
        multi_scattering_approximation_octave_count=1,const_multi_scattering_contribution=.65,
        const_multi_scattering_occlusion=.35,const_multi_scattering_eccentricity=.25,
        ray_march_volume_shadow=False)
    readbacks = {}
    for name, value in settings.items():
        advanced.set_editor_property(name,value)
        readbacks[name] = lighting_readback(advanced.get_editor_property(name),value)
    errors = lib.recompile_material(material)
    if errors:
        raise RuntimeError('Authored storm shader compilation failed: ' + str(errors))
    if not unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False):
        raise RuntimeError('Cannot save the owned storm material')
    return material,dict(spec=SPEC,shaderCode=SHADER,shaderCodeReadbackMatches=True,
        material=material.get_path_name(),advancedReadbacks=readbacks,
        altitudeInput='CloudSampleAttribute.NormAltitudeInLayer',
        renderResourceVerified=False,visibleCloudPixelsVerified=False,visualApproved=False)
