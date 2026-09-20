"""Original oak, forged metal, hemp and mineral fields for source PBR review."""
import bpy

class Field:
    def __init__(self,name):
        self.material=bpy.data.materials.new('retained_workshop_field.'+name);self.material.use_nodes=True;self.material.use_fake_user=True
        self.nodes=self.material.node_tree.nodes;self.links=self.material.node_tree.links;self.nodes.clear()
        self.output=self.nodes.new('ShaderNodeOutputMaterial');self.shader=self.nodes.new('ShaderNodeBsdfPrincipled');self.links.new(self.shader.outputs[0],self.output.inputs[0])
        self.obj=self.nodes.new('ShaderNodeTexCoord').outputs['Object']
        attribute=self.nodes.new('ShaderNodeAttribute');attribute.attribute_name='piece_grain'
        self.grain=attribute.outputs['Vector'];self.local_grain=attribute.outputs['Vector']
    def set(self,value,socket):
        if isinstance(value,(int,float,tuple,list)):socket.default_value=value
        else:self.links.new(value,socket)
    def math(self,operation,a,b=0):
        node=self.nodes.new('ShaderNodeMath');node.operation=operation;self.set(a,node.inputs[0]);self.set(b,node.inputs[1]);return node.outputs[0]
    def scaled(self,vector,scale):
        node=self.nodes.new('ShaderNodeVectorMath');node.operation='MULTIPLY';self.set(vector,node.inputs[0]);node.inputs[1].default_value=scale;return node.outputs[0]
    def noise(self,vector,scale,detail=3):
        node=self.nodes.new('ShaderNodeTexNoise');node.inputs['Scale'].default_value=1;node.inputs['Detail'].default_value=detail;node.inputs['Roughness'].default_value=.64;self.links.new(self.scaled(vector,scale),node.inputs['Vector']);return node.outputs['Fac']
    def ramp(self,value,stops):
        node=self.nodes.new('ShaderNodeValToRGB');node.color_ramp.interpolation='EASE'
        for i,(position,color) in enumerate(stops):
            element=node.color_ramp.elements[i] if i<2 else node.color_ramp.elements.new(position);element.position=position;element.color=(*color,1)
        self.set(value,node.inputs[0]);return node.outputs['Color']
    def mix(self,a,b,factor):
        node=self.nodes.new('ShaderNodeMixRGB');self.set(factor,node.inputs[0]);self.set(a,node.inputs[1]);self.set(b,node.inputs[2]);return node.outputs[0]
    def component(self,vector,name):
        node=self.nodes.new('ShaderNodeSeparateXYZ');self.set(vector,node.inputs[0]);return node.outputs[name]
    def finish(self,color,roughness,metallic,height,distance):
        bump=self.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=distance;bump.inputs['Strength'].default_value=.62;self.set(height,bump.inputs['Height']);self.links.new(bump.outputs['Normal'],self.shader.inputs['Normal']);self.set(color,self.shader.inputs['Base Color']);self.set(roughness,self.shader.inputs['Roughness']);self.set(metallic,self.shader.inputs['Metallic'])
        ao=self.nodes.new('ShaderNodeAmbientOcclusion');ao.only_local=True;ao.samples=16;ao.inputs['Distance'].default_value=.08
        orm=self.nodes.new('ShaderNodeCombineColor');orm.mode='RGB';self.links.new(ao.outputs['AO'],orm.inputs['Red']);self.set(roughness,orm.inputs['Green']);self.set(metallic,orm.inputs['Blue'])
        return {'material':self.material,'color':color,'orm':orm.outputs[0],'output':self.output,'shader':self.shader}

def create_field(name):
    f=Field(name);m=f.math;grain=f.grain;obj=f.obj
    if name in ('oak','oak_end','working_oak'):
        figure=f.noise(grain,(18,21,2.1),4);fine=f.noise(grain,(240,220,9),2)
        color=f.ramp(figure,[(.19,(.070,.035,.013)),(.45,(.162,.087,.033)),(.68,(.262,.162,.074)),(.85,(.325,.216,.113))])
        pores=f.ramp(fine,[(.25,(.77,.77,.77)),(.40,(0,0,0))])
        color=f.mix(color,(.067,.036,.017,1),m('MULTIPLY',pores,.43))
        height=m('SUBTRACT',m('MULTIPLY',figure,.35),m('MULTIPLY',pores,.7));rough=m('ADD',.70,m('MULTIPLY',figure,.18))
        if name=='oak_end':
            x=f.component(f.local_grain,'X');y=f.component(f.local_grain,'Y');radius=m('SQRT',m('ADD',m('MULTIPLY',x,x),m('MULTIPLY',y,y)))
            rings=m('ADD',m('MULTIPLY',m('SINE',m('ADD',m('MULTIPLY',radius,600),m('MULTIPLY',figure,2))),.5),.5)
            color=f.mix(color,(.108,.051,.017,1),m('MULTIPLY',rings,.32));height=m('ADD',height,m('MULTIPLY',rings,.08))
        if name=='working_oak':
            wear=f.ramp(f.noise(obj,(3.5,7,2),4),[(.33,(0,0,0)),(.68,(.65,.65,.65))])
            z=f.component(obj,'Z');on_top=f.ramp(z,[(.905,(0,0,0)),(.941,(1,1,1))]);wear=m('MULTIPLY',wear,on_top)
            color=f.mix(color,(.285,.200,.109,1),wear);rough=m('SUBTRACT',rough,m('MULTIPLY',wear,.20))
            # Short uneven tool tracks cross the longitudinal wood surface.
            scores=f.ramp(f.noise(obj,(24,155,12),3),[(.31,(.8,.8,.8)),(.41,(0,0,0))])
            scores=m('MULTIPLY',scores,on_top);color=f.mix(color,(.068,.041,.020,1),m('MULTIPLY',scores,.25));height=m('SUBTRACT',height,m('MULTIPLY',scores,.33))
        grime=f.ramp(f.noise(obj,(9,7,8),3),[(.30,(.3,.3,.3)),(.54,(0,0,0))]);color=f.mix(color,(.036,.030,.018,1),grime)
        return f.finish(color,rough,0,height,.0016)
    if name in ('forged_iron','worked_steel'):
        hammer=f.noise(obj,(115,115,115),3);scale=f.noise(obj,(22,22,22),3)
        color=f.ramp(scale,[(.2,(.026,.031,.033)),(.52,(.055,.065,.071)),(.82,(.102,.118,.123))]) if name=='forged_iron' else f.ramp(scale,[(.2,(.17,.183,.189)),(.8,(.29,.32,.33))])
        oxide=f.ramp(f.noise(obj,(37,37,37),3),[(.58,(0,0,0)),(.73,(.24,.24,.24))])
        color=f.mix(color,(.096,.037,.011,1),oxide);rough=m('ADD',.48 if name=='forged_iron' else .35,m('MULTIPLY',hammer,.19))
        height=m('MULTIPLY',hammer,.7 if name=='forged_iron' else .16)
        if name=='worked_steel':
            scratches=f.noise(grain,(420,14,130),2);height=m('ADD',height,m('MULTIPLY',scratches,.20))
        return f.finish(color,rough,m('SUBTRACT',.92,m('MULTIPLY',oxide,.8)),height,.0006)
    if name=='hemp':
        fibre=f.noise(grain,(240,240,8),3);broad=f.noise(grain,(8,8,2),2)
        color=f.ramp(broad,[(.2,(.13,.088,.040)),(.48,(.25,.18,.090)),(.82,(.38,.29,.161))]);color=f.mix(color,(.075,.050,.024,1),m('MULTIPLY',fibre,.16))
        return f.finish(color,m('ADD',.82,m('MULTIPLY',broad,.1)),0,fibre,.00038)
    mineral=f.noise(obj,(11,11,11),4);grit=f.noise(obj,(235,235,235),3)
    color=f.ramp(mineral,[(.20,(.083,.089,.081)),(.47,(.18,.19,.17)),(.78,(.29,.292,.244))]);spots=f.ramp(grit,[(.31,(.85,.85,.85)),(.45,(0,0,0))]);color=f.mix(color,(.060,.066,.055,1),m('MULTIPLY',spots,.24))
    return f.finish(color,m('ADD',.78,m('MULTIPLY',mineral,.16)),0,m('SUBTRACT',grit,m('MULTIPLY',spots,.3)),.0010)

def apply_materials(objects):
    fields={name:create_field(name) for name in ('oak','oak_end','working_oak','forged_iron','worked_steel','hemp','cut_stone')}
    for obj in objects:
        for i,material in enumerate(obj.data.materials):obj.data.materials[i]=fields[material.name.split('.')[0]]['material']
    return fields
