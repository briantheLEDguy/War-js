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

def bake_bark(obj,lod,preview_only=False):
    before=geometry_hash(obj);scene=bpy.context.scene
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_render=False;obj.select_set(True);bpy.context.view_layer.objects.active=obj
    data=obj.data
    # Age is a continuous distance from the original trunk axis, so fine young
    # limbs do not inherit the mature bole's deep fissures. No geometry moves.
    trunk=json.loads((ROOT/'source/nature.json').read_text())['design']['alderTrunk']
    age=data.attributes.get('bark_maturity') or data.attributes.new('bark_maturity','FLOAT','POINT')
    for vertex in data.vertices:
        point=vertex.co;first,second=next(((a,b) for a,b in zip(trunk,trunk[1:]) if a[2]<=point.z<=b[2]),(trunk[0],trunk[1]) if point.z<trunk[0][2] else (trunk[-2],trunk[-1]))
        t=max(0,min(1,(point.z-first[2])/(second[2]-first[2])))
        x=first[0]+(second[0]-first[0])*t;y=first[1]+(second[1]-first[1])*t;r=first[3]+(second[3]-first[3])*t
        radial=math.hypot(point.x-x,point.y-y)
        mature=max(0,min(1,1-(radial-r*.9)/max(.3,r*1.7)))
        mature=mature*mature*(3-2*mature)
        age.data[vertex.index].value=max(mature,.65 if point.z<.4 else 0)
    if not preview_only:
        data.uv_layers['authored_uv'].name='retained_branch_uv'
        data.uv_layers.new(name='authored_uv');data.uv_layers.active_index=len(data.uv_layers)-1;data.uv_layers['authored_uv'].active_render=True
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        resolution=[4096,2048,1024][lod];pixel_margin=4/resolution
        bpy.ops.uv.smart_project(angle_limit=math.radians(68),island_margin=pixel_margin,area_weight=.8,correct_aspect=True,scale_to_bounds=True)
        bpy.ops.uv.pack_islands(rotate=True,rotate_method='ANY',scale=True,margin_method='FRACTION',margin=pixel_margin,shape_method='CONCAVE')
        bpy.ops.object.mode_set(mode='OBJECT')
        uv_data=data.uv_layers['authored_uv'].data;occupied=0
        for face in data.polygons:
            coords=[uv_data[i].uv for i in face.loop_indices]
            occupied+=abs(sum(a.x*b.y-b.x*a.y for a,b in zip(coords,coords[1:]+coords[:1])))*.5
    if not preview_only:
        data.calc_tangents(uvmap='authored_uv')
        invalid=[loop.index for loop in data.loops if loop.tangent.length<.99]
        if invalid:
            rows=[]
            for i in invalid:
                face=next(p for p in data.polygons if i in p.loop_indices)
                rows.append({'loop':i,'vertex':data.loops[i].vertex_index,'position':list(data.vertices[data.loops[i].vertex_index].co),'normal':list(data.corner_normals[i].vector),'tangent':list(data.loops[i].tangent),'face':face.index,'faceNormal':list(face.normal),'positions':[list(data.vertices[data.loops[j].vertex_index].co) for j in face.loop_indices],'uvs':[list(data.uv_layers['authored_uv'].data[j].uv) for j in face.loop_indices]})
            (ROOT/'review'/f'invalid_tangents_lod{lod}.json').write_text(json.dumps(rows,indent=2)+'\n')
        data.free_tangents()
        if invalid:raise RuntimeError(f'Bark LOD{lod} has {len(invalid)} invalid tangents before baking: {invalid[:8]}')
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
    age_node=nodes.new('ShaderNodeAttribute');age_node.attribute_name='bark_maturity';maturity=age_node.outputs['Fac']
    broad=noise((.85,.85,.72),4);grain=noise((92,92,10),3)
    fissure=ramp(noise((22,22,1.7),4),[(.30,(1,1,1)),(.44,(.55,.55,.55)),(.57,(0,0,0))])
    interrupted=ramp(noise((5,5,9),2),[(.39,(0,0,0)),(.52,(.65,.65,.65)),(.68,(1,1,1))])
    age_strength=math_node('ADD',.035,math_node('MULTIPLY',maturity,.965))
    fissure_strength=math_node('MULTIPLY',fissure,math_node('MULTIPLY',interrupted,age_strength))
    # Pigment variation is independent of narrow interrupted fissures. Sparse
    # fine lenticels and restrained lichen replace broad outlined polygons.
    bark=ramp(broad,[(.29,(.027,.030,.025)),(.48,(.075,.066,.048)),(.67,(.135,.14,.117))])
    furrow=nodes.new('ShaderNodeMixRGB');links.new(math_node('MULTIPLY',fissure_strength,.67),furrow.inputs[0]);links.new(bark,furrow.inputs[1]);furrow.inputs[2].default_value=(.019,.024,.019,1)
    lenticels=ramp(noise((27,27,125),1),[(.67,(0,0,0)),(.78,(.18,.18,.18)),(.88,(.35,.35,.35))])
    fleck=nodes.new('ShaderNodeMixRGB');links.new(lenticels,fleck.inputs[0]);links.new(furrow.outputs[0],fleck.inputs[1]);fleck.inputs[2].default_value=(.17,.16,.13,1)
    lichen=ramp(noise((11,11,7),3),[(.63,(0,0,0)),(.76,(.35,.35,.35)),(.85,(.58,.58,.58))])
    color=nodes.new('ShaderNodeMixRGB');links.new(lichen,color.inputs[0]);links.new(fleck.outputs[0],color.inputs[1]);color.inputs[2].default_value=(.12,.14,.08,1)
    position=nodes.new('ShaderNodeSeparateXYZ');links.new(coordinate.outputs['Object'],position.inputs[0])
    wet_height=math_node('ADD',math_node('SUBTRACT',.78,position.outputs['Z']),math_node('MULTIPLY',noise((3,3,.8),2),.3))
    wet=math_node('MINIMUM',1,math_node('MAXIMUM',0,math_node('DIVIDE',wet_height,.85)))
    damp=nodes.new('ShaderNodeMixRGB');links.new(math_node('MULTIPLY',wet,.7),damp.inputs[0]);links.new(color.outputs[0],damp.inputs[1]);damp.inputs[2].default_value=(.015,.024,.018,1)
    height=math_node('SUBTRACT',math_node('MULTIPLY',grain,.22),math_node('MULTIPLY',fissure_strength,.78))
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.82;bump.inputs['Distance'].default_value=.017;links.new(height,bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    links.new(damp.outputs[0],shader.inputs['Base Color']);roughness=math_node('SUBTRACT',math_node('ADD',.74,math_node('MULTIPLY',broad,.2)),math_node('MULTIPLY',wet,.19));links.new(roughness,shader.inputs['Roughness'])
    ao=nodes.new('ShaderNodeAmbientOcclusion');ao.samples=16;ao.inputs['Distance'].default_value=.14;ao.only_local=True
    orm=nodes.new('ShaderNodeCombineColor');orm.mode='RGB';links.new(ao.outputs['AO'],orm.inputs['Red']);links.new(roughness,orm.inputs['Green']);orm.inputs['Blue'].default_value=0
    data.materials.clear();data.materials.append(source)
    for face in data.polygons:face.material_index=0
    if preview_only:return {'previewOnly':True,'material':source}
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False;scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=2;scene.render.bake.normal_space='TANGENT'
    folder=ROOT/'textures/bark-projection';folder.mkdir(exist_ok=True);resolution=[4096,2048,1024][lod];images={};channels={}
    target=nodes.new('ShaderNodeTexImage');nodes.active=target;emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
    for channel,socket in [('baseColor',damp.outputs[0]),('orm',orm.outputs[0]),('normal',None)]:
        image=bpy.data.images.new(f'alder_continuous_bark_lod{lod}_{channel}',width=resolution,height=resolution,alpha=False)
        image.colorspace_settings.name='sRGB' if channel=='baseColor' else 'Non-Color'
        image.generated_color=(.5,.5,1,1) if channel=='normal' else (1,.86,0,1) if channel=='orm' else (.26,.25,.23,1)
        target.image=image;nodes.active=target
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
    record={'atlas':{'resolution':resolution,'marginPixels':4,'dilationPixels':2,'occupiedFraction':occupied,'normalBackground':[.5,.5,1]},'tool':'tools/bake_bark_projection.py','toolSha256':sha(Path(__file__)),'geometrySha256Before':before,'geometrySha256After':geometry_hash(obj),'method':'Continuous object-space 3D pigment, fissure, lichen and height fields baked on the identical joined mesh to a unique area-weighted UV atlas; no ray projection from a different LOD. Original branch UVs are retained in the master.','channels':channels}
    (ROOT/'review'/f'alder_bark_projection_lod{lod}.json').write_text(json.dumps(record,indent=2)+'\n')
    print('BARK_PROJECTION_BAKED',lod,resolution,flush=True)
    return record
