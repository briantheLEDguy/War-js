"""Private bare-earth road adaptation; original verge graph, terrain support and source packages are retained."""
import json
import unreal
from t1_materials import sha
from t1_forest_floor_native import SHADER,NORMAL_SHADER
from t1_road_earth import road_earth_recipe,road_earth_shaders


def road_earth_sources(root):
    receipt=root/'artifacts/unreal/licensed-kits/nature-surfaces-staged.json';data=json.loads(receipt.read_text());files={receipt.relative_to(root).as_posix():sha(receipt)};textures={}
    for suffix in ('BC','N'):
        matches=[r for r in data['textures'] if r['path'].rsplit('.',1)[-1]=='T_Ground_Dirt_Near_01_'+suffix]
        if len(matches)!=1:raise RuntimeError('Missing exact bare-earth road channel')
        row=matches[0];file=root/'unreal/AegisWar/Content'/(row['path'].split('.',1)[0].removeprefix('/Game/')+'.uasset')
        normal=suffix=='N';texture=unreal.load_asset(row['path'])
        if sha(file)!=row['sourceSha256'] or not isinstance(texture,unreal.Texture2D) or texture.get_editor_property('srgb')==normal or texture.get_editor_property('virtual_texture_streaming'):
            raise RuntimeError('Bare-earth road fingerprint, type or colour space differs')
        if texture.get_editor_property('compression_settings')!=(unreal.TextureCompressionSettings.TC_NORMALMAP if normal else unreal.TextureCompressionSettings.TC_DEFAULT):raise RuntimeError('Bare-earth road compression differs')
        files[file.relative_to(root).as_posix()]=row['sourceSha256'];textures[suffix]=texture
    return textures,files


def road_earth_material(assets,original,source,road_channels,textures):
    recipe=road_earth_recipe(source['id'])
    if recipe is None:raise RuntimeError('Road earth adaptation is admitted only for Sunmeadow')
    if not assets.folder.startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_') or original.get_editor_property('blend_mode')!=unreal.BlendMode.BLEND_TRANSLUCENT:
        raise RuntimeError('Road earth requires a fresh private candidate and retained soft verge material')
    mat=assets.tools.duplicate_asset('M_SpatialRoadEarth',assets.folder+'/Materials',original);lib=unreal.MaterialEditingLibrary;nodes={}
    nodes['P']=lib.create_material_expression(mat,unreal.MaterialExpressionWorldPosition)
    for key,row in [('Village',source['spawnPoint']),('KeepA',source['orvrLayout']['keeps'][0]),('KeepB',source['orvrLayout']['keeps'][1])]:
        n=lib.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector);n.set_editor_property('constant',unreal.LinearColor(row['z']*100,row['x']*100,0,1));nodes[key]=n
    bindings=dict(Stone=assets.texture(road_channels['color'],False),Soil=textures['BC'],StoneNormal=assets.texture(road_channels['normal'],True),SoilNormal=textures['N'])
    for key,texture in bindings.items():
        n=lib.create_material_expression(mat,unreal.MaterialExpressionTextureObject);n.set_editor_property('texture',texture);n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if key.endswith('Normal') else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR);nodes[key]=n
    colour,normal=road_earth_shaders(SHADER,NORMAL_SHADER,recipe)
    for shader,channels,prop in [(colour,('Stone','Soil'),unreal.MaterialProperty.MP_BASE_COLOR),(normal,('StoneNormal','SoilNormal'),unreal.MaterialProperty.MP_NORMAL)]:
        keys=['P','Village','KeepA','KeepB',*channels];custom=lib.create_material_expression(mat,unreal.MaterialExpressionCustom);entries=[]
        for key in keys:
            entry=unreal.CustomInput();entry.set_editor_property('input_name',key);entries.append(entry)
        custom.set_editor_property('inputs',entries);custom.set_editor_property('code',shader);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        for key in keys:
            if not lib.connect_material_expressions(nodes[key],'',custom,key):raise RuntimeError('Cannot connect road earth channel '+key)
        if not lib.connect_material_property(custom,'',prop):raise RuntimeError('Cannot bind road earth material')
    errors=lib.recompile_material(mat)
    if errors:raise RuntimeError('Road earth shader compilation failed: '+str(list(errors)))
    if not unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False):raise RuntimeError('Cannot save fresh road earth material')
    return mat,dict(asset=mat.get_path_name(),recipe=recipe,sourceMaterial=original.get_path_name(),bareEarthChannels={k:v.get_path_name() for k,v in textures.items()},
        matchingColourNormalWeights=True,softVergeGraphRetained=True,geometryAndCollisionPreserved=True,stochasticColourNormalTextureLookups=12,retainedOpacityAndRoughnessGraph=True,
        shaderCompileErrors=list(errors),sourcePackagesPreserved=True,appearanceApproved=False,performanceAccepted=False,distributionApproved=False)
