"""Continuous mineral and fracture fields on the unchanged finished rock mesh."""
import hashlib,json,math
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def geometry_hash(obj):
    return hashlib.sha256(json.dumps({'vertices':[list(v.co) for v in obj.data.vertices],'faces':[list(p.vertices) for p in obj.data.polygons]},separators=(',',':')).encode()).hexdigest()

def bake_basalt(obj,lod,preview_only=False):
    before=geometry_hash(obj);scene=bpy.context.scene;data=obj.data
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_render=False;obj.select_set(True);bpy.context.view_layer.objects.active=obj
    data.uv_layers['authored_uv'].name='retained_fracture_uv';data.uv_layers.new(name='authored_uv');data.uv_layers.active_index=len(data.uv_layers)-1;data.uv_layers['authored_uv'].active_render=True
    resolution=[2048,1024,512][lod];margin=4/resolution
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(52),island_margin=margin,area_weight=.8,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.uv.pack_islands(rotate=True,rotate_method='ANY',scale=True,margin_method='FRACTION',margin=margin,shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT');uv=data.uv_layers['authored_uv'].data;occupied=0
    for face in data.polygons:
        coords=[uv[i].uv for i in face.loop_indices];occupied+=abs(sum(a.x*b.y-b.x*a.y for a,b in zip(coords,coords[1:]+coords[:1])))*.5
    # A sub-square-millimetre bevel sliver inherits almost perpendicular
    # weighted corner normals. An independent chart exposes its undefined
    # tangent. Use that real facet's geometric normal only on affected tiny
    # faces; preserve every vertex, triangle and all other corner normals.
    data.calc_tangents(uvmap='authored_uv');invalid=[loop.index for loop in data.loops if loop.tangent.length<.99];data.free_tangents()
    normal_repairs=[]
    if invalid:
        normals=[list(item.vector) for item in data.corner_normals]
        for face in data.polygons:
            if not any(i in invalid for i in face.loop_indices):continue
            alignments=[data.corner_normals[i].vector.dot(face.normal) for i in face.loop_indices]
            if face.area>1e-6 or min(alignments)>.2:raise RuntimeError('Unexpected basalt tangent defect outside tiny bevel-normal case')
            normal_repairs.append({'face':face.index,'cornerIndices':list(face.loop_indices),'areaM2':face.area,'minimumOriginalNormalAlignment':min(alignments),'method':'Geometric normal on tiny bevel facet; geometry and other corner normals retained.'})
            for i in face.loop_indices:normals[i]=list(face.normal)
        data.normals_split_custom_set(normals);data.update()
        data.calc_tangents(uvmap='authored_uv');invalid=[loop.index for loop in data.loops if loop.tangent.length<.99];data.free_tangents()
    if invalid:raise RuntimeError(f'Basalt LOD{lod} still has invalid tangents: {invalid[:8]}')
    source=bpy.data.materials.new(f'retained_continuous_basalt_projection_lod{lod}');source.use_nodes=True;source.use_fake_user=True
    nodes=source.node_tree.nodes;links=source.node_tree.links;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial');shader=nodes.new('ShaderNodeBsdfPrincipled');links.new(shader.outputs[0],output.inputs[0]);coordinate=nodes.new('ShaderNodeTexCoord')
    def scaled(scale):
        n=nodes.new('ShaderNodeVectorMath');n.operation='MULTIPLY';n.inputs[1].default_value=scale;links.new(coordinate.outputs['Object'],n.inputs[0]);return n.outputs[0]
    def noise(scale,detail=3):
        n=nodes.new('ShaderNodeTexNoise');n.noise_dimensions='3D';n.inputs['Scale'].default_value=1;n.inputs['Detail'].default_value=detail;n.inputs['Roughness'].default_value=.68;links.new(scaled(scale),n.inputs['Vector']);return n.outputs['Fac']
    def math_node(operation,a,b=0):
        n=nodes.new('ShaderNodeMath');n.operation=operation
        for i,value in enumerate((a,b)):
            if isinstance(value,(int,float)):n.inputs[i].default_value=value
            else:links.new(value,n.inputs[i])
        return n.outputs[0]
    def ramp(value,stops):
        n=nodes.new('ShaderNodeValToRGB');n.color_ramp.interpolation='EASE'
        for index,(position,color) in enumerate(stops):
            item=n.color_ramp.elements[index] if index<2 else n.color_ramp.elements.new(position);item.position=position;item.color=(*color,1)
        links.new(value,n.inputs[0]);return n.outputs['Color']
    def mix(a,b,factor):
        n=nodes.new('ShaderNodeMixRGB')
        for socket,value in [(n.inputs[0],factor),(n.inputs[1],a),(n.inputs[2],b)]:
            if isinstance(value,tuple):socket.default_value=value
            elif isinstance(value,(int,float)):socket.default_value=value
            else:links.new(value,socket)
        return n.outputs[0]
    mineral=ramp(noise((4,4,4),5),[(.17,(.038,.045,.045)),(.50,(.073,.081,.078)),(.83,(.135,.14,.128))])
    weather=ramp(noise((1.15,.85,1.6),3),[(.52,(0,0,0)),(.68,(.20,.20,.20)),(.82,(.58,.58,.58))])
    pigment=mix(mineral,(.18,.117,.060,1),weather)
    grain=noise((145,145,145),2);pits=ramp(grain,[(.24,(1,1,1)),(.35,(.15,.15,.15)),(.44,(0,0,0))])
    pigment=mix(pigment,(.025,.032,.031,1),math_node('MULTIPLY',pits,.58))
    # Three explicitly directed cooling-fracture traces cross neighboring faces
    # in the same object coordinates. Their paths never reset at a UV seam.
    warp=math_node('MULTIPLY',math_node('SUBTRACT',noise((3,3,3),3),.5),.042)
    fracture=0
    for normal,offset in [((.24,.13,1),.84),((1,-.32,.19),-.61),((-.2,1,.34),.57)]:
        dot=nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';dot.inputs[1].default_value=normal;links.new(coordinate.outputs['Object'],dot.inputs[0])
        distance=math_node('ABSOLUTE',math_node('ADD',math_node('SUBTRACT',dot.outputs['Value'],offset),warp))
        line=ramp(distance,[(.001,(1,1,1)),(.005,(.55,.55,.55)),(.015,(0,0,0))])
        fracture=math_node('MAXIMUM',fracture,line)
    color=mix(pigment,(.017,.020,.019,1),math_node('MULTIPLY',fracture,.8))
    height=math_node('SUBTRACT',math_node('MULTIPLY',grain,.2),math_node('ADD',math_node('MULTIPLY',pits,.25),math_node('MULTIPLY',fracture,.75)))
    roughness=math_node('ADD',.76,math_node('MULTIPLY',grain,.18))
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.62;bump.inputs['Distance'].default_value=.012;links.new(height,bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal']);links.new(color,shader.inputs['Base Color']);links.new(roughness,shader.inputs['Roughness'])
    ao=nodes.new('ShaderNodeAmbientOcclusion');ao.samples=16;ao.inputs['Distance'].default_value=.17;ao.only_local=True
    orm=nodes.new('ShaderNodeCombineColor');orm.mode='RGB';links.new(ao.outputs['AO'],orm.inputs['Red']);links.new(roughness,orm.inputs['Green']);orm.inputs['Blue'].default_value=0
    data.materials.clear();data.materials.append(source)
    for face in data.polygons:face.material_index=0
    if preview_only:return {'previewOnly':True,'material':source}
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False;scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=2;scene.render.bake.normal_space='TANGENT'
    folder=ROOT/'textures/basalt-projection';folder.mkdir(exist_ok=True);images={};channels={};target=nodes.new('ShaderNodeTexImage');nodes.active=target;emission=nodes.new('ShaderNodeEmission')
    for channel,socket in [('baseColor',color),('orm',orm.outputs[0]),('normal',None)]:
        image=bpy.data.images.new(f'basalt_continuous_lod{lod}_{channel}',width=resolution,height=resolution,alpha=False);image.colorspace_settings.name='sRGB' if channel=='baseColor' else 'Non-Color';image.generated_color=(.5,.5,1,1) if channel=='normal' else (1,.86,0,1) if channel=='orm' else (.29,.31,.30,1);target.image=image;nodes.active=target
        for link in list(output.inputs[0].links):links.remove(link)
        if socket is None:links.new(shader.outputs[0],output.inputs[0]);kind='NORMAL'
        else:links.new(socket,emission.inputs['Color']);links.new(emission.outputs[0],output.inputs[0]);kind='EMIT'
        bpy.ops.object.bake(type=kind);path=folder/f'basalt_lod{lod}_{channel}.png';image.filepath_raw=str(path);image.file_format='PNG';image.save();images[channel]=image;channels[channel]={'file':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(path),'resolution':resolution}
    result=bpy.data.materials.new(f'cinderfen_nature.basalt.continuous_lod{lod}');result.use_nodes=True;result.use_backface_culling=True;nodes=result.node_tree.nodes;links=result.node_tree.links;shader=nodes.get('Principled BSDF');uv=nodes.new('ShaderNodeUVMap');uv.uv_map='authored_uv';maps={}
    for channel,image in images.items():
        n=nodes.new('ShaderNodeTexImage');n.image=image;n.extension='EXTEND';links.new(uv.outputs['UV'],n.inputs['Vector']);maps[channel]=n
    links.new(maps['baseColor'].outputs['Color'],shader.inputs['Base Color']);normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='authored_uv';links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal']);split=nodes.new('ShaderNodeSeparateColor');links.new(maps['orm'].outputs['Color'],split.inputs[0]);links.new(split.outputs['Green'],shader.inputs['Roughness']);links.new(split.outputs['Blue'],shader.inputs['Metallic']);output=nodes.new('ShaderNodeGroup');output.node_tree=bpy.data.node_groups['glTF Material Output'];links.new(split.outputs['Red'],output.inputs['Occlusion']);data.materials.clear();data.materials.append(result)
    if geometry_hash(obj)!=before:raise RuntimeError('Basalt projection changed finished geometry')
    record={'tool':'tools/bake_basalt_projection.py','toolSha256':sha(Path(__file__)),'geometrySha256Before':before,'geometrySha256After':geometry_hash(obj),'atlas':{'resolution':resolution,'occupiedFraction':occupied,'marginPixels':4,'dilationPixels':2,'normalRepairs':normal_repairs},'channels':channels,'method':'Continuous object-space mineral, weathering, pits and three original cooling-fracture paths baked directly on the identical finished mesh; original face UVs remain in the master.'}
    (ROOT/'review'/f'basalt_projection_lod{lod}.json').write_text(json.dumps(record,indent=2)+'\n');print('BASALT_PROJECTION_BAKED',lod,resolution,flush=True);return record
