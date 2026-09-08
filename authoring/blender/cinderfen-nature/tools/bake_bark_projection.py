"""Bake a continuous 3D bark field onto the unchanged joined alder mesh.

Inherited branch UV strips reset at cage rows. A new area-weighted atlas samples
one object-space field across every join. Retained cages/UVs remain inspectable;
the projection is baked on this same mesh, avoiding low-LOD ray-transfer errors.
"""
import hashlib,json,math
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def geometry_hash(obj):
    return hashlib.sha256(json.dumps({'vertices':[list(v.co) for v in obj.data.vertices],'faces':[list(p.vertices) for p in obj.data.polygons]},separators=(',',':')).encode()).hexdigest()

def bake_bark(obj,lod):
    before=geometry_hash(obj);scene=bpy.context.scene
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_render=False;obj.select_set(True);bpy.context.view_layer.objects.active=obj
    data=obj.data
    data.uv_layers['authored_uv'].name='retained_branch_uv'
    data.uv_layers.new(name='authored_uv');data.uv_layers.active_index=len(data.uv_layers)-1;data.uv_layers['authored_uv'].active_render=True
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(68),island_margin=.006,area_weight=.8,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    source=bpy.data.materials.new(f'retained_continuous_bark_projection_lod{lod}');source.use_nodes=True;source.use_fake_user=True
    nodes=source.node_tree.nodes;links=source.node_tree.links;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial');shader=nodes.new('ShaderNodeBsdfPrincipled');links.new(shader.outputs[0],output.inputs[0])
    coordinate=nodes.new('ShaderNodeTexCoord')
    def scaled(scale):
        node=nodes.new('ShaderNodeVectorMath');node.operation='MULTIPLY';node.inputs[1].default_value=scale;links.new(coordinate.outputs['Object'],node.inputs[0]);return node.outputs[0]
    def noise(scale,detail=3):
        node=nodes.new('ShaderNodeTexNoise');node.noise_dimensions='3D';node.inputs['Scale'].default_value=1;node.inputs['Detail'].default_value=detail;node.inputs['Roughness'].default_value=.67;links.new(scaled(scale),node.inputs['Vector']);return node.outputs['Fac']
    def math_node(operation,a,b):
        node=nodes.new('ShaderNodeMath');node.operation=operation
        for i,value in enumerate((a,b)):
            if isinstance(value,(int,float)):node.inputs[i].default_value=value
            else:links.new(value,node.inputs[i])
        return node.outputs[0]
    def ramp(value,stops):
        node=nodes.new('ShaderNodeValToRGB');node.color_ramp.interpolation='EASE'
        for element in list(node.color_ramp.elements)[2:]:node.color_ramp.elements.remove(element)
        for index,(position,color) in enumerate(stops):
            item=node.color_ramp.elements[index] if index<2 else node.color_ramp.elements.new(position)
            item.position=position;item.color=(*color,1)
        links.new(value,node.inputs[0]);return node.outputs['Color']
    broad=noise((1.3,1.3,.9));grain=noise((30,30,3.5),2)
    warp=nodes.new('ShaderNodeVectorMath');warp.operation='SCALE';links.new(noise((3,3,1)),warp.inputs[0]);warp.inputs['Scale'].default_value=.17
    field=nodes.new('ShaderNodeVectorMath');field.operation='ADD';links.new(scaled((6,6,.8)),field.inputs[0]);links.new(warp.outputs[0],field.inputs[1])
    cracks=nodes.new('ShaderNodeTexVoronoi');cracks.voronoi_dimensions='3D';cracks.feature='DISTANCE_TO_EDGE';cracks.inputs['Scale'].default_value=1;links.new(field.outputs[0],cracks.inputs['Vector'])
    fissure=ramp(cracks.outputs['Distance'],[(.008,(.10,.10,.10)),(.028,(.72,.72,.72)),(.11,(1,1,1))])
    # Neutral grey-brown bark, longitudinal broken fissures and small lichen
    # islands are all continuous in space; there is no repeat boundary in Z.
    bark=ramp(broad,[(.16,(.030,.028,.023)),(.49,(.067,.064,.051)),(.84,(.113,.109,.088))])
    multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=.43;links.new(bark,multiply.inputs[1]);links.new(fissure,multiply.inputs[2])
    lichen=ramp(noise((6,6,5),2),[(.64,(0,0,0)),(.72,(.42,.42,.42)),(.79,(.72,.72,.72))])
    color=nodes.new('ShaderNodeMixRGB');links.new(lichen,color.inputs[0]);links.new(multiply.outputs[0],color.inputs[1]);color.inputs[2].default_value=(.12,.14,.082,1)
    height=math_node('ADD',math_node('MULTIPLY',grain,.30),math_node('MULTIPLY',cracks.outputs['Distance'],.70))
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.38;bump.inputs['Distance'].default_value=.028;links.new(height,bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    links.new(color.outputs[0],shader.inputs['Base Color']);roughness=math_node('ADD',.79,math_node('MULTIPLY',grain,.14));links.new(roughness,shader.inputs['Roughness'])
    ao=nodes.new('ShaderNodeAmbientOcclusion');ao.samples=16;ao.inputs['Distance'].default_value=.14;ao.only_local=True
    orm=nodes.new('ShaderNodeCombineColor');orm.mode='RGB';links.new(ao.outputs['AO'],orm.inputs['Red']);links.new(roughness,orm.inputs['Green']);orm.inputs['Blue'].default_value=0
    data.materials.clear();data.materials.append(source)
    for face in data.polygons:face.material_index=0
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False;scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=True;scene.render.bake.margin=12;scene.render.bake.normal_space='TANGENT'
    folder=ROOT/'textures/bark-projection';folder.mkdir(exist_ok=True);resolution=[2048,1024,512][lod];images={};channels={}
    target=nodes.new('ShaderNodeTexImage');nodes.active=target;emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
    for channel,socket in [('baseColor',color.outputs[0]),('orm',orm.outputs[0]),('normal',None)]:
        image=bpy.data.images.new(f'alder_continuous_bark_lod{lod}_{channel}',width=resolution,height=resolution,alpha=False)
        image.colorspace_settings.name='sRGB' if channel=='baseColor' else 'Non-Color';target.image=image;nodes.active=target
        for link in list(output.inputs[0].links):links.remove(link)
        if socket is None:links.new(shader.outputs[0],output.inputs[0]);kind='NORMAL'
        else:links.new(socket,emission.inputs['Color']);links.new(emission.outputs[0],output.inputs[0]);kind='EMIT'
        bpy.ops.object.bake(type=kind)
        path=folder/f'alder_bark_lod{lod}_{channel}.png';image.filepath_raw=str(path);image.file_format='PNG';image.save();images[channel]=image
        channels[channel]={'file':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(path),'resolution':resolution}
    result=bpy.data.materials.new(f'cinderfen_nature.alder_bark.continuous_lod{lod}');result.use_nodes=True;result.use_backface_culling=True
    nodes=result.node_tree.nodes;links=result.node_tree.links;shader=nodes.get('Principled BSDF');uv=nodes.new('ShaderNodeUVMap');uv.uv_map='authored_uv';maps={}
    for channel,image in images.items():
        node=nodes.new('ShaderNodeTexImage');node.image=image;node.extension='EXTEND';links.new(uv.outputs['UV'],node.inputs['Vector']);maps[channel]=node
    links.new(maps['baseColor'].outputs['Color'],shader.inputs['Base Color'])
    normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='authored_uv';links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    split=nodes.new('ShaderNodeSeparateColor');links.new(maps['orm'].outputs['Color'],split.inputs[0]);links.new(split.outputs['Green'],shader.inputs['Roughness']);links.new(split.outputs['Blue'],shader.inputs['Metallic'])
    output=nodes.new('ShaderNodeGroup');output.node_tree=bpy.data.node_groups['glTF Material Output'];links.new(split.outputs['Red'],output.inputs['Occlusion'])
    data.materials.clear();data.materials.append(result)
    if geometry_hash(obj)!=before:raise RuntimeError('Bark projection changed authored geometry')
    record={'tool':'tools/bake_bark_projection.py','toolSha256':sha(Path(__file__)),'geometrySha256Before':before,'geometrySha256After':geometry_hash(obj),'method':'Continuous object-space 3D pigment, fissure, lichen and height fields baked on the identical joined mesh to a unique area-weighted UV atlas; no ray projection from a different LOD. Original branch UVs are retained in the master.','channels':channels}
    (ROOT/'review'/f'alder_bark_projection_lod{lod}.json').write_text(json.dumps(record,indent=2)+'\n')
    print('BARK_PROJECTION_BAKED',lod,resolution,flush=True)
    return record
