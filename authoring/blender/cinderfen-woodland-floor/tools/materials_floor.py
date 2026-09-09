"""Original shaded-floor foliage maps and continuous branch-local wood fields."""
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]

def occlusion_socket(material,value):
    group=bpy.data.node_groups.get('glTF Material Output')
    if not group:
        group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
        group.interface.new_socket('Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
    node=material.node_tree.nodes.new('ShaderNodeGroup');node.node_tree=group
    material.node_tree.links.new(value,node.inputs['Occlusion'])

def image_material(name,images=None,uv_name='source_uv'):
    material=bpy.data.materials.new('cinderfen_floor.'+name);material.use_nodes=True;material.use_backface_culling=True
    nodes=material.node_tree.nodes;links=material.node_tree.links;shader=nodes.get('Principled BSDF')
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map=uv_name;maps={}
    for channel in ('baseColor','normal','orm'):
        node=nodes.new('ShaderNodeTexImage');node.image=images[channel] if images else bpy.data.images.load(str(ROOT/'textures/source'/f'{name}_{channel}.png'),check_existing=True)
        node.image.colorspace_settings.name='sRGB' if channel=='baseColor' else 'Non-Color';node.extension='EXTEND';links.new(uv.outputs['UV'],node.inputs['Vector']);maps[channel]=node
    links.new(maps['baseColor'].outputs['Color'],shader.inputs['Base Color'])
    normal=nodes.new('ShaderNodeNormalMap');normal.uv_map=uv_name;links.new(maps['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    split=nodes.new('ShaderNodeSeparateColor');links.new(maps['orm'].outputs['Color'],split.inputs[0]);links.new(split.outputs['Green'],shader.inputs['Roughness']);links.new(split.outputs['Blue'],shader.inputs['Metallic'])
    occlusion_socket(material,split.outputs['Red'])
    return material

class Field:
    def __init__(self,name):
        self.material=bpy.data.materials.new('retained_floor_field.'+name);self.material.use_nodes=True;self.material.use_fake_user=True
        self.nodes=self.material.node_tree.nodes;self.links=self.material.node_tree.links;self.nodes.clear()
        self.output=self.nodes.new('ShaderNodeOutputMaterial');self.shader=self.nodes.new('ShaderNodeBsdfPrincipled');self.links.new(self.shader.outputs[0],self.output.inputs[0])
        self.coordinates=self.nodes.new('ShaderNodeTexCoord').outputs['Object']
        attribute=self.nodes.new('ShaderNodeAttribute');attribute.attribute_name='wood_grain';self.grain=attribute.outputs['Vector']
    def connect(self,value,socket):
        if isinstance(value,(int,float,tuple,list)):socket.default_value=value
        else:self.links.new(value,socket)
    def scaled(self,vector,scale):
        node=self.nodes.new('ShaderNodeVectorMath');node.operation='MULTIPLY';self.connect(vector,node.inputs[0]);node.inputs[1].default_value=scale;return node.outputs[0]
    def noise(self,vector,scale,detail=3):
        node=self.nodes.new('ShaderNodeTexNoise');node.inputs['Scale'].default_value=1;node.inputs['Detail'].default_value=detail;node.inputs['Roughness'].default_value=.68;self.links.new(self.scaled(vector,scale),node.inputs['Vector']);return node.outputs['Fac']
    def math(self,operation,a,b=0):
        node=self.nodes.new('ShaderNodeMath');node.operation=operation;self.connect(a,node.inputs[0]);self.connect(b,node.inputs[1]);return node.outputs[0]
    def ramp(self,value,stops):
        node=self.nodes.new('ShaderNodeValToRGB');node.color_ramp.interpolation='EASE'
        for index,(position,color) in enumerate(stops):
            element=node.color_ramp.elements[index] if index<2 else node.color_ramp.elements.new(position);element.position=position;element.color=(*color,1)
        self.connect(value,node.inputs[0]);return node.outputs['Color']
    def mix(self,a,b,factor):
        node=self.nodes.new('ShaderNodeMixRGB');self.connect(factor,node.inputs[0]);self.connect(a,node.inputs[1]);self.connect(b,node.inputs[2]);return node.outputs[0]
    def component(self,vector,axis):
        node=self.nodes.new('ShaderNodeSeparateXYZ');self.connect(vector,node.inputs[0]);return node.outputs[axis]
    def finish(self,color,roughness,height,distance):
        bump=self.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=distance;bump.inputs['Strength'].default_value=.65;self.connect(height,bump.inputs['Height']);self.links.new(bump.outputs['Normal'],self.shader.inputs['Normal']);self.connect(color,self.shader.inputs['Base Color']);self.connect(roughness,self.shader.inputs['Roughness'])
        ao=self.nodes.new('ShaderNodeAmbientOcclusion');ao.samples=16;ao.only_local=True;ao.inputs['Distance'].default_value=.10
        orm=self.nodes.new('ShaderNodeCombineColor');orm.mode='RGB';self.links.new(ao.outputs['AO'],orm.inputs['Red']);self.connect(roughness,orm.inputs['Green']);orm.inputs['Blue'].default_value=0
        return {'material':self.material,'color':color,'orm':orm.outputs[0],'shader':self.shader,'output':self.output}

def wood_field(name):
    field=Field(name);obj=field.coordinates;grain=field.grain;m=field.math
    broad=field.noise(obj,(3.1,3.6,3.9),4)
    fibres=field.noise(grain,(165,165,7.5),3)
    if name=='fallen_bark':
        color=field.ramp(broad,[(.2,(.037,.033,.026)),(.49,(.073,.064,.050)),(.78,(.13,.118,.095))])
        # Branch-local fibres carry fine grain around the bend. Broad pigment,
        # fissure interruption and lichen share object space across fork joins.
        fissure=field.ramp(field.noise(grain,(52,52,4.2),4),[(.48,(0,0,0)),(.65,(.10,.10,.10)),(.73,(.92,.92,.92))])
        interruption=field.ramp(field.noise(obj,(14,14,14),3),[(.25,(.12,.12,.12)),(.61,(1,1,1))])
        fissure=m('MULTIPLY',fissure,interruption)
        color=field.mix(color,(.022,.022,.018,1),m('MULTIPLY',fissure,.78))
        lichen_patch=field.ramp(field.noise(obj,(9,9,9),3),[(.58,(0,0,0)),(.69,(.8,.8,.8))])
        lichen_grain=field.ramp(field.noise(obj,(105,105,105),2),[(.39,(0,0,0)),(.54,(1,1,1))])
        lichen=m('MULTIPLY',lichen_patch,lichen_grain)
        color=field.mix(color,(.19,.204,.132,1),m('MULTIPLY',lichen,.58))
        z=field.component(obj,'Z');damp=field.ramp(z,[(.015,(.58,.58,.58)),(.10,(.22,.22,.22)),(.23,(0,0,0))])
        color=field.mix(color,(.021,.023,.017,1),damp)
        height=m('ADD',m('SUBTRACT',m('MULTIPLY',fibres,.18),m('MULTIPLY',fissure,.8)),m('MULTIPLY',lichen,.11))
        rough=m('SUBTRACT',m('ADD',.78,m('MULTIPLY',broad,.16)),m('MULTIPLY',damp,.14))
        return field.finish(color,rough,height,.009)
    x=field.component(grain,'X');y=field.component(grain,'Y')
    radius=m('SQRT',m('ADD',m('MULTIPLY',x,x),m('MULTIPLY',y,y)))
    warp=m('MULTIPLY',field.noise(grain,(27,27,.8),3),2.4)
    rings=m('SINE',m('ADD',m('MULTIPLY',radius,335),warp))
    ring_stain=m('MULTIPLY',m('ADD',rings,1),.5)
    if name=='pale_fracture':
        color=field.ramp(fibres,[(.2,(.135,.086,.042)),(.53,(.26,.18,.096)),(.8,(.37,.283,.165))])
    else:
        color=field.ramp(broad,[(.22,(.040,.022,.009)),(.51,(.112,.058,.022)),(.80,(.184,.106,.044))])
        color=field.mix(color,(.22,.144,.069,1),m('MULTIPLY',fibres,.24))
    color=field.mix(color,(.061,.032,.011,1),m('MULTIPLY',ring_stain,.14))
    pores=field.ramp(fibres,[(.29,(.85,.85,.85)),(.43,(0,0,0))])
    color=field.mix(color,(.032,.018,.007,1),m('MULTIPLY',pores,.42))
    height=m('SUBTRACT',m('MULTIPLY',fibres,.32),m('MULTIPLY',pores,.55))
    rough=m('ADD',.76,m('MULTIPLY',broad,.16))
    return field.finish(color,rough,height,.004)

def apply_materials(objects):
    fields={name:wood_field(name) for name in ('fallen_bark','broken_heartwood','pale_fracture')}
    materials={name:value['material'] for name,value in fields.items()}
    materials.update({name:image_material(name) for name in ('fern_stem','fern_leaf','wood_sedge')})
    for obj in objects:
        for index,old in enumerate(obj.data.materials):
            name=old.name.split('.')[0];obj.data.materials[index]=materials[name]
    return fields
