"""Source-derived stone shading for private rock adaptations; no surface displacement."""
import unreal
from t1_geology_surface import NORMAL_SHADER,bump_controls
from t1_strata_surface import STRATA_SHADER,validate_strata


def stone_material(assets,identity,recipe):
    if identity not in ('sunmeadow_march','cinderfen_outskirts') or not assets.folder.startswith('/Game/WorldRebuild/T1Redesign_'):
        raise RuntimeError('Stone adaptations require a fresh private first-pair asset collection')
    lib=unreal.MaterialEditingLibrary
    m=assets.tools.create_asset('M_'+identity+'_bedded_stone',assets.folder+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    if not m:raise RuntimeError('Cannot create private stone material')
    def node(kind,**values):
        n=lib.create_material_expression(m,getattr(unreal,'MaterialExpression'+kind))
        for k,v in values.items():n.set_editor_property(k,v)
        return n
    def wire(a,ap,b,bp):
        if not lib.connect_material_expressions(a,ap,b,bp):raise RuntimeError('Cannot bind private stone graph')
    def scalar(v):return node('Constant',r=v)
    def binary(kind,a,b,ap='',bp=''):
        n=node(kind);wire(a,ap,n,'A');wire(b,bp,n,'B');return n
    def vector(v):return node('Constant3Vector',constant=unreal.LinearColor(*v,1))
    def mask(n,i):
        v=node('ComponentMask',r=i==0,g=i==1,b=i==2,a=False);wire(n,'',v,'');return v
    def lerp(a,b,t):
        n=node('LinearInterpolate');wire(a,'',n,'A');wire(b,'',n,'B');wire(t,'',n,'Alpha');return n
    p=node('WorldPosition');normal=node('VertexNormalWS');axes=[mask(p,i) for i in range(3)];weights=[];projected=[]
    for i,uv in enumerate([(1,2),(0,2),(0,1)]):
        n=mask(normal,i);square=binary('Multiply',n,n);w=binary('Multiply',square,square);weights.append(w)
        tex=node('TextureSample',texture=assets.texture(recipe['color'],False),sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        coords=binary('Divide',binary('AppendVector',axes[uv[0]],axes[uv[1]]),scalar(recipe['tileMetres']*100));wire(coords,'',tex,'UVs')
        projected.append(binary('Multiply',tex,w,'RGB'))
    source=binary('Divide',binary('Add',binary('Add',projected[0],projected[1]),projected[2]),binary('Add',binary('Add',weights[0],weights[1]),weights[2]))
    g=recipe['geological'];coarse=node('Noise',quality=1,levels=2,turbulence=False,output_min=0,output_max=1,noise_function=unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX3D)
    fine=node('Noise',quality=1,levels=1,turbulence=False,output_min=0,output_max=1,noise_function=unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX3D)
    wire(binary('Divide',p,scalar(g['noiseMetres']*100)),'',coarse,'');wire(binary('Divide',p,scalar(g['fineMetres']*100)),'',fine,'')
    color=lerp(vector(g['baseColor']),source,scalar(g['sourceMix']))
    macro=binary('Add',scalar(g['macroMinimum']),binary('Multiply',coarse,scalar(g['macroMaximum']-g['macroMinimum'])))
    grain=binary('Add',scalar(g['fineMinimum']),binary('Multiply',fine,scalar(1-g['fineMinimum'])))
    color=binary('Multiply',color,binary('Multiply',macro,grain))
    strata_color,strata_height=strata_nodes(lib,m,p,coarse,g['strata']);color=binary('Multiply',color,strata_color)
    bump=bump_controls(g);height=binary('Add',binary('Multiply',binary('Subtract',coarse,scalar(.5)),scalar(bump[0])),binary('Multiply',binary('Subtract',fine,scalar(.5)),scalar(bump[1])))
    height=binary('Add',height,strata_height)
    detail=node('Custom',description='T1 bounded stone shading normal',output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,code=NORMAL_SHADER)
    pins=[]
    for key in ('P','N','H'):
        pin=unreal.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    detail.set_editor_property('inputs',pins)
    if detail.get_editor_property('code')!=NORMAL_SHADER:raise RuntimeError('Private stone shader differs from source')
    for v,key in [(p,'P'),(normal,'N'),(height,'H')]:wire(v,'',detail,key)
    for v,pin in [(color,unreal.MaterialProperty.MP_BASE_COLOR),(detail,unreal.MaterialProperty.MP_NORMAL),(scalar(.92),unreal.MaterialProperty.MP_ROUGHNESS),(scalar(0),unreal.MaterialProperty.MP_METALLIC)]:
        if not lib.connect_material_property(v,'',pin):raise RuntimeError('Cannot bind private stone output')
    if lib.recompile_material(m):raise RuntimeError('Private stone material compilation failed')
    if not unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False):raise RuntimeError('Cannot save private stone material')
    return m


def strata_nodes(lib,material,world,noise,recipe):
    validate_strata(recipe)
    n=lib.create_material_expression(material,unreal.MaterialExpressionCustom)
    n.set_editor_property('description','T1 soft regional geological layers');n.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT2);n.set_editor_property('code',STRATA_SHADER)
    names=['P','Noise','Wavelength','Warp','Contrast','Bump'];pins=[]
    for name in names:
        pin=unreal.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    if n.get_editor_property('code')!=STRATA_SHADER:raise RuntimeError('Strata shader readback differs')
    values=[world,noise]
    for key in ('wavelengthMetres','warpMetres','contrast','bumpHeightCm'):
        v=lib.create_material_expression(material,unreal.MaterialExpressionConstant);v.set_editor_property('r',recipe[key]);values.append(v)
    for v,name in zip(values,names):
        if not lib.connect_material_expressions(v,'',n,name):raise RuntimeError('Cannot bind regional strata')
    results=[]
    for i in range(2):
        mask=lib.create_material_expression(material,unreal.MaterialExpressionComponentMask);mask.set_editor_property('r',i==0);mask.set_editor_property('g',i==1);mask.set_editor_property('b',False);mask.set_editor_property('a',False)
        if not lib.connect_material_expressions(n,'',mask,''):raise RuntimeError('Cannot bind strata output')
        results.append(mask)
    return results
