"""Surface-fitted wet-work pocket, wax wear and seam finishing."""
import math
import bpy,numpy as np
from mathutils import Vector
from surface_bindings import ClothSurface,bind_detail

def finish(apron,make,sweep,materials,work):
    support=ClothSurface(apron)
    def front(x,z,depth):
        hit,n,_,_=support.tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
        if hit is None:raise RuntimeError('Peat pocket has no supporting bib surface')
        return hit+Vector((0,-depth,0))
    vertices=[];cols=10;rows=8
    for r in range(rows):
        t=r/(rows-1);z=1.427-.135*t
        for c in range(cols):
            u=c/(cols-1);x=-.084+.168*u
            vertices.append(front(x,z,.008+.015*math.sin(math.pi*u)*math.sin(math.pi*t*.9)))
    faces=[(r*cols+c,r*cols+c+1,(r+1)*cols+c+1,(r+1)*cols+c) for r in range(rows-1) for c in range(cols-1)]
    pocket=make('peat_bib_double_stitched_pocket',vertices,faces,materials['leather'])
    sub=pocket.modifiers.new('Pocket_draped_surface','SUBSURF');sub.levels=sub.render_levels=1
    solid=pocket.modifiers.new('Pocket_real_leather_thickness','SOLIDIFY');solid.thickness=.003
    bind_detail(pocket,[support])
    edge=[vertices[r*cols] for r in range(rows)]+vertices[-cols:]+[vertices[r*cols+cols-1] for r in reversed(range(rows))]
    edging=sweep('peat_pocket_bound_edges',edge,[.0017]*len(edge),materials['leather']);bind_detail(edging,[support])
    mouth=sweep('peat_pocket_turned_mouth',vertices[:cols],[.0023]*cols,materials['leather']);bind_detail(mouth,[support])
    for a,b in zip(edge,edge[1:]):
        steps=max(1,int((b-a).length/.006))
        for i in range(steps):
            p=a.lerp(b,i/steps)+Vector((0,-.002,0));q=a.lerp(b,(i+.52)/steps)+Vector((0,-.002,0))
            stitch=sweep('peat_pocket_saddle_stitch',[p,q],[.0006,.0006],materials['seam'],sides=5);bind_detail(stitch,[support])
    # A planar UV domain follows the actual bib. Moisture and peat collect at
    # the lower edge; hand rubbing lightens the pocket lip and breast area.
    size=1024;v,u=np.mgrid[0:size,0:size]/(size-1)
    x=u*.46-.23;z=v*.63+.97
    pore=np.sin(u*780+np.sin(v*331))*np.sin(v*865+np.cos(u*210))
    tide=np.exp(-((z-1.025-.012*np.sin(x*57))/.045)**2)
    wear=np.exp(-(x/.10)**4-((z-1.427)/.009)**2)
    abrasion=np.exp(-((x-.06)/.09)**2-((z-1.23)/.09)**2)
    mottling=np.sin(u*51+np.sin(v*17))*np.cos(v*39-u*9)
    pigment=.93+.032*pore+.035*mottling-.22*tide+.16*wear+.05*abrasion
    rough=np.clip(.82+.06*mottling-.23*tide-.14*wear,.48,.93)
    relief=pore*.10+mottling*.065+.045*tide
    gy,gx=np.gradient(relief);normal=np.stack((-gx*.7,-gy*.7,np.ones_like(gx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    mat=bpy.data.materials.new('peat_worker_wax_worn_bib');mat.use_nodes=True;shader=mat.node_tree.nodes['Principled BSDF']
    for channel,values in [('basecolor',np.array([.17,.093,.047])[None,None,:]*pigment[:,:,None]),('normal',normal*.5+.5),('roughness',np.repeat(rough[:,:,None],3,axis=2))]:
        rgba=np.ones((size,size,4),np.float32);rgba[:,:,:3]=values
        image=bpy.data.images.new('peat_worker_wax_bib_'+channel,width=size,height=size,alpha=True)
        image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color';image.pixels.foreach_set(rgba.ravel())
        image.filepath_raw=str(work/'textures'/f'{image.name}.png');image.file_format='PNG';image.save();image.pack()
        texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
        if channel=='normal':
            node=mat.node_tree.nodes.new('ShaderNodeNormalMap');node.uv_map='UVMap';node.inputs['Strength'].default_value=.45
            mat.node_tree.links.new(texture.outputs['Color'],node.inputs['Color']);mat.node_tree.links.new(node.outputs['Normal'],shader.inputs['Normal'])
        else:mat.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    for obj in [apron,pocket,edging,mouth,bpy.data.objects['apron_bound_perimeter']]:
        obj.data.materials.clear();obj.data.materials.append(mat)
        for face in obj.data.polygons:
            face.material_index=0
            for loop in face.loop_indices:
                p=obj.data.vertices[obj.data.loops[loop].vertex_index].co
                obj.data.uv_layers.active.data[loop].uv=((p.x+.23)/.46,(p.z-.97)/.63)
