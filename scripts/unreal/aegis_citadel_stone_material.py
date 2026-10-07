"""Original weathered sculpture study, evaluated on the actual native surface.

World-space grain avoids borrowing planar ashlar UVs for carved figures. The
small bump changes shading only; it never displaces geometry or collision.
"""
from citadel_stage_contract import lighting_readback

SPEC=dict(recipeVersion=1,baseColor=[.045,.052,.063,1],grainPeriodCm=32,
    streakPeriodCm=140,roughness=.86,bumpHeightCm=.16,worldSpaceNormal=True,
    geometryChanged=False,collisionChanged=False,visualApproved=False)

NOISE=r'''
struct BastionStoneNoise {
    float Hash(float3 p) {
        p=frac(p*.1031);p+=dot(p,p.yzx+33.33);return frac((p.x+p.y)*p.z);
    }
    float Value(float3 p) {
        float3 i=floor(p),f=frac(p);f=f*f*(3-2*f);
        return lerp(lerp(lerp(Hash(i),Hash(i+float3(1,0,0)),f.x),
                         lerp(Hash(i+float3(0,1,0)),Hash(i+float3(1,1,0)),f.x),f.y),
                    lerp(lerp(Hash(i+float3(0,0,1)),Hash(i+float3(1,0,1)),f.x),
                         lerp(Hash(i+float3(0,1,1)),Hash(i+float3(1,1,1)),f.x),f.y),f.z);
    }
};
BastionStoneNoise noise;
float grain=noise.Value(P/@GRAIN@)*.7+noise.Value(P/(@GRAIN@*.28)+8.4)*.3;
'''.replace('@GRAIN@',str(SPEC['grainPeriodCm']))
COLOR_SHADER=NOISE+r'''
float streak=noise.Value(P/float3(@STREAK@,@STREAK@,@STREAK@*7));
return Base*lerp(.72,1.18,grain)*lerp(.78,1.08,streak);
'''.replace('@STREAK@',str(SPEC['streakPeriodCm']))
HEIGHT_SHADER=NOISE+'return grain*'+str(SPEC['bumpHeightCm'])+';'
NORMAL_SHADER=r'''
float3 n=normalize(N),px=ddx(P),py=ddy(P);
float3 r1=cross(py,n),r2=cross(n,px);
float determinant=dot(px,r1);
float3 gradient=sign(determinant)*(ddx(H)*r1+ddy(H)*r2);
return abs(determinant)>1e-8 ? normalize(abs(determinant)*n-gradient) : n;
'''
if any('@' in code for code in (COLOR_SHADER,HEIGHT_SHADER,NORMAL_SHADER)):
    raise ValueError('Sculpture weathering has an unbound source input')


def weather_carved_stone(unreal,material,base):
    lib=unreal.MaterialEditingLibrary
    if not isinstance(base,unreal.MaterialExpressionConstant3Vector):
        raise RuntimeError('Sculpture study requires its exact copied scalar base graph')
    if lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_NORMAL):
        raise RuntimeError('Preserve independently changed sculpture normal shading')
    position=lib.create_material_expression(material,unreal.MaterialExpressionWorldPosition)
    vertex_normal=lib.create_material_expression(material,unreal.MaterialExpressionVertexNormalWS)
    def custom(description,code,kind,inputs):
        node=lib.create_material_expression(material,unreal.MaterialExpressionCustom)
        node.set_editor_property('description',description);node.set_editor_property('output_type',kind)
        names=[]
        for name in inputs:
            entry=unreal.CustomInput();entry.set_editor_property('input_name',name);names.append(entry)
        node.set_editor_property('inputs',names);node.set_editor_property('code',code)
        if node.get_editor_property('code')!=code:raise RuntimeError('Sculpture shader differs from its signed source')
        return node
    color=custom('Bastion carved stone grain and rain staining',COLOR_SHADER,
        unreal.CustomMaterialOutputType.CMOT_FLOAT3,['P','Base'])
    height=custom('Bastion shallow sculpture pitting in centimetres',HEIGHT_SHADER,
        unreal.CustomMaterialOutputType.CMOT_FLOAT1,['P'])
    normal=custom('Bastion world surface differential bump',NORMAL_SHADER,
        unreal.CustomMaterialOutputType.CMOT_FLOAT3,['P','N','H'])
    for source,output,target,pin in ((position,'',color,'P'),(base,'',color,'Base'),(position,'',height,'P'),
            (position,'',normal,'P'),(vertex_normal,'',normal,'N'),(height,'',normal,'H')):
        if not lib.connect_material_expressions(source,output,target,pin):
            raise RuntimeError('Disconnected sculpture weathering input: '+pin)
    for node,property_name in ((color,unreal.MaterialProperty.MP_BASE_COLOR),(normal,unreal.MaterialProperty.MP_NORMAL)):
        if (not lib.connect_material_property(node,'',property_name)
                or lib.get_material_property_input_node(material,property_name)!=node):
            raise RuntimeError('Disconnected sculpture material property')
    material.set_editor_property('tangent_space_normal',False)
    lighting_readback(material.get_editor_property('tangent_space_normal'),False)
    errors=lib.recompile_material(material)
    if errors:raise RuntimeError('Sculpture weathering compilation failed: '+str(errors))
    return dict(spec=SPEC,colorShader=COLOR_SHADER,heightShader=HEIGHT_SHADER,normalShader=NORMAL_SHADER,
        actualShaderReadbackMatches=True,worldSpaceNormalReadback=True,nativePixelReviewRequired=True,
        visualApproved=False)
