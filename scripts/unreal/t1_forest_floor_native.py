"""Exact privately staged ground channels and a fresh native forest-floor material; no source edits."""
import json
import unreal
from t1_materials import sha
from t1_forest_floor import forest_floor_mask,mask_png


def forest_floor_sources(root):
    receipt=root/'artifacts/unreal/licensed-kits/nature-surfaces-staged.json'
    data=json.loads(receipt.read_text());files={receipt.relative_to(root).as_posix():sha(receipt)}
    for row in data['files']:
        path=root/'unreal/AegisWar/Content'/row['path']
        if sha(path)!=row['sha256']:raise RuntimeError('Installed forest-floor package changed')
        files[path.relative_to(root).as_posix()]=row['sha256']
    names=('Grass_Near_01_BC','Grass_Near_01_N','Grass_Far_01_BC','Forest_Near_01_BC','Forest_Near_01_N','Forest_Far_01_BC')
    textures={}
    for name in names:
        rows=[r for r in data['textures'] if r['path'].rsplit('.',1)[-1]=='T_Ground_'+name]
        if len(rows)!=1:raise RuntimeError('Missing exact installed forest-floor channel')
        row=rows[0];path='unreal/AegisWar/Content/'+row['path'].split('.',1)[0].removeprefix('/Game/')+'.uasset'
        normal=name.endswith('_N');texture=unreal.load_asset(row['path'])
        if files.get(path)!=row['sourceSha256'] or not isinstance(texture,unreal.Texture2D) or texture.get_editor_property('srgb')!=row['srgb'] or row['srgb']==normal or texture.get_editor_property('virtual_texture_streaming'):
            raise RuntimeError('Forest-floor channel fingerprint, type or colour space differs')
        if texture.get_editor_property('compression_settings')!=(unreal.TextureCompressionSettings.TC_NORMALMAP if normal else unreal.TextureCompressionSettings.TC_DEFAULT):
            raise RuntimeError('Forest-floor channel compression differs')
        textures[name]=texture
    return textures,files


SHADER=r'''
struct SampleHelper {
 float2 hash(float2 p) { return frac(sin(float2(dot(p,float2(127.1,311.7)),dot(p,float2(269.5,183.3))))*43758.5453); }
 float3 sample(Texture2D T,SamplerState TS,float2 uv) {
  float2 q=float2(uv.x-uv.y*.577350269,uv.y*1.154700538)/3;
  float2 cell=floor(q), f=frac(q);float2 a,b,c;float3 w;
  if(f.x+f.y<=1) {a=cell;b=cell+float2(1,0);c=cell+float2(0,1);w=float3(1-f.x-f.y,f.x,f.y);}
  else {a=cell+1;b=cell+float2(0,1);c=cell+float2(1,0);w=float3(f.x+f.y-1,1-f.x,1-f.y);}
  w=w*w*w;w/=max(dot(w,1),.0001);
  float2 dx=ddx(uv),dy=ddy(uv);
  return Texture2DSampleGrad(T,TS,uv+hash(a)*7.3,dx,dy).rgb*w.x+Texture2DSampleGrad(T,TS,uv+hash(b)*7.3,dx,dy).rgb*w.y+Texture2DSampleGrad(T,TS,uv+hash(c)*7.3,dx,dy).rgb*w.z;
 }
};SampleHelper h;
float2 p=float2(P.y,-P.x)/100;
float2 maskUv=float2((p.x-Bounds.x)/(Bounds.y-Bounds.x),(-p.y-Bounds.z)/(Bounds.w-Bounds.z));
float floorWeight=Texture2DSample(Mask,MaskSampler,maskUv).r;
float distanceBlend=smoothstep(3500,12000,distance(P,Camera));
float3 grass=lerp(h.sample(Grass,GrassSampler,p/3.2),h.sample(GrassFar,GrassFarSampler,p/7.5),distanceBlend*.35)*float3(.55,.66,.50);
float3 forest=lerp(h.sample(Forest,ForestSampler,p/3.2),h.sample(ForestFar,ForestFarSampler,p/7.5),distanceBlend*.35)*float3(.65,.7,.60);
float macro=.93+.07*sin(p.x/37+sin(p.y/23));
float3 colour=lerp(grass,forest,floorWeight*.92)*macro;
float rock=smoothstep(.85,.63,N.z);
return lerp(colour,Fallback,rock);
'''


NORMAL_SHADER=r'''
struct SampleHelper {
 float2 hash(float2 p) { return frac(sin(float2(dot(p,float2(127.1,311.7)),dot(p,float2(269.5,183.3))))*43758.5453); }
 float3 sample(Texture2D T,SamplerState TS,float2 uv) {
  float2 q=float2(uv.x-uv.y*.577350269,uv.y*1.154700538)/3;
  float2 cell=floor(q), f=frac(q);float2 a,b,c;float3 w;
  if(f.x+f.y<=1) {a=cell;b=cell+float2(1,0);c=cell+float2(0,1);w=float3(1-f.x-f.y,f.x,f.y);}
  else {a=cell+1;b=cell+float2(0,1);c=cell+float2(1,0);w=float3(f.x+f.y-1,1-f.x,1-f.y);}
  w=w*w*w;w/=max(dot(w,1),.0001);
  float2 dx=ddx(uv),dy=ddy(uv);
  return UnpackNormalMap(Texture2DSampleGrad(T,TS,uv+hash(a)*7.3,dx,dy)).rgb*w.x+UnpackNormalMap(Texture2DSampleGrad(T,TS,uv+hash(b)*7.3,dx,dy)).rgb*w.y+UnpackNormalMap(Texture2DSampleGrad(T,TS,uv+hash(c)*7.3,dx,dy)).rgb*w.z;
 }
};SampleHelper h;
float2 p=float2(P.y,-P.x)/100;
float2 maskUv=float2((p.x-Bounds.x)/(Bounds.y-Bounds.x),(-p.y-Bounds.z)/(Bounds.w-Bounds.z));
float forestWeight=Texture2DSample(Mask,MaskSampler,maskUv).r*.92;
float3 n=normalize(lerp(h.sample(GrassNormal,GrassNormalSampler,p/3.2),h.sample(ForestNormal,ForestNormalSampler,p/3.2),forestWeight));
float fade=smoothstep(2500,14000,distance(P,Camera));
n=normalize(float3(n.xy*.45*(1-fade*.7),n.z));
float rock=smoothstep(.85,.63,N.z);
return normalize(lerp(n,Fallback,rock));
'''


def forest_floor_material(assets,original,source,states,textures,base):
    if source['id']!='sunmeadow_march' or not assets.folder.startswith('/Game/WorldRebuild/T1Redesign_Atmosphere_'):
        raise RuntimeError('Forest-floor study requires a fresh private Sunmeadow scene')
    trees=[]
    for state in states.values():
        if state['kind']!='mesh' or 'WarT1PrivateInstalledNatureStudy' not in state['tags']:continue
        mesh=unreal.load_asset(state['mesh']);ext=mesh.get_bounds().box_extent;scale=state['scale'];p=state['location']
        trees.append(dict(x=p[1]/100,z=p[0]/100,radius=max(ext.x*scale[0],ext.y*scale[1])/100*1.8+3))
    if not 200<=len(trees)<=500:raise RuntimeError('Forest-floor mask requires bounded installed canopy identities')
    size=1024;b=source['spatial']['bounds'];mask=forest_floor_mask(b,trees,size)
    output=base/'material-studies'/('forest-floor-'+assets.collection+'.png');output.parent.mkdir(exist_ok=True);output.write_bytes(mask_png(mask,size))
    task=unreal.AssetImportTask();task.filename=str(output);task.destination_path=assets.folder+'/Textures';task.destination_name='T_ForestFloorMask';task.automated=True;task.save=True
    assets.tools.import_asset_tasks([task]);objects=task.get_objects()
    if len(objects)!=1 or not isinstance(objects[0],unreal.Texture2D):raise RuntimeError('Cannot import bounded forest mask')
    texture=objects[0];texture.set_editor_property('srgb',False);texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP);texture.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
    if not unreal.EditorAssetLibrary.save_loaded_asset(texture,only_if_is_dirty=False):raise RuntimeError('Cannot save fresh forest mask')
    lib=unreal.MaterialEditingLibrary;mat=assets.tools.duplicate_asset('M_SpatialForestFloor',assets.folder+'/Materials',original)
    if not mat:raise RuntimeError('Cannot duplicate fresh forest-floor material')
    color=lib.get_material_property_input_node(mat,unreal.MaterialProperty.MP_BASE_COLOR);color_pin=lib.get_material_property_input_node_output_name(mat,unreal.MaterialProperty.MP_BASE_COLOR)
    normal=lib.get_material_property_input_node(mat,unreal.MaterialProperty.MP_NORMAL);normal_pin=lib.get_material_property_input_node_output_name(mat,unreal.MaterialProperty.MP_NORMAL)
    nodes={name:lib.create_material_expression(mat,kind) for name,kind in [('P',unreal.MaterialExpressionWorldPosition),('N',unreal.MaterialExpressionVertexNormalWS),('Camera',unreal.MaterialExpressionCameraPositionWS)]}
    bounds=lib.create_material_expression(mat,unreal.MaterialExpressionConstant4Vector);bounds.set_editor_property('constant',unreal.LinearColor(b['minX'],b['maxX'],b['maxZ'],b['minZ']));nodes['Bounds']=bounds
    bindings={'Mask':texture,'Grass':textures['Grass_Near_01_BC'],'GrassFar':textures['Grass_Far_01_BC'],'Forest':textures['Forest_Near_01_BC'],'ForestFar':textures['Forest_Far_01_BC'],'GrassNormal':textures['Grass_Near_01_N'],'ForestNormal':textures['Forest_Near_01_N']}
    for name,value in bindings.items():
        node=lib.create_material_expression(mat,unreal.MaterialExpressionTextureObject);node.set_editor_property('texture',value)
        node.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS if name=='Mask' else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if name.endswith('Normal') else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        nodes[name]=node
    for shader,names,fallback,pin,prop in [(SHADER,('P','N','Camera','Bounds','Mask','Grass','GrassFar','Forest','ForestFar','Fallback'),color,color_pin,unreal.MaterialProperty.MP_BASE_COLOR),(NORMAL_SHADER,('P','N','Camera','Bounds','Mask','GrassNormal','ForestNormal','Fallback'),normal,normal_pin,unreal.MaterialProperty.MP_NORMAL)]:
        custom=lib.create_material_expression(mat,unreal.MaterialExpressionCustom);entries=[]
        for name in names:
            entry=unreal.CustomInput();entry.set_editor_property('input_name',name);entries.append(entry)
        custom.set_editor_property('inputs',entries);custom.set_editor_property('code',shader);custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        for name in names:
            if not lib.connect_material_expressions(fallback if name=='Fallback' else nodes[name],pin if name=='Fallback' else '',custom,name):raise RuntimeError('Cannot connect forest-floor channel '+name)
        if not lib.connect_material_property(custom,'',prop):raise RuntimeError('Cannot bind completed forest-floor graph')
    errors=lib.recompile_material(mat)
    if errors:raise RuntimeError('Forest-floor material compile failed: '+str(errors))
    if not unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False):raise RuntimeError('Cannot save fresh forest-floor material')
    return mat,dict(asset=mat.get_path_name(),mask=texture.get_path_name(),maskFile=output.relative_to(assets.root).as_posix(),maskSha256=sha(output),maskSize=[size,size],treeCount=len(trees),maskCoverage=sum(v>25 for v in mask)/len(mask),nearTileMetres=3.2,farTileMetres=7.5,farBlend=.35,matchedNormalSampling=True,shaderCompileErrors=list(errors),sourcePackagesPreserved=True,geometryAndCollisionPreserved=True,licenseReviewed=False,distributionApproved=False,appearanceApproved=False,performanceAccepted=False)
