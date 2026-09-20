"""Surface-bound shirt stitching and apron wear placed at actual use areas."""
import math
import bpy
import numpy as np
from mathutils import Vector
from surface_bindings import ClothSurface, bind_detail


def garment_boundaries(obj):
    muted=[mod for mod in obj.modifiers if mod.type in ('ARMATURE','SOLIDIFY') and mod.show_viewport]
    for mod in muted:mod.show_viewport=False
    bpy.context.view_layer.update()
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    points=[evaluated.matrix_world@vertex.co for vertex in mesh.vertices];counts={}
    for face in mesh.polygons:
        ids=tuple(face.vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            pair=tuple(sorted((a,b)));counts[pair]=counts.get(pair,0)+1
    adjacent={}
    for (a,b),count in counts.items():
        if count==1:adjacent.setdefault(a,[]).append(b);adjacent.setdefault(b,[]).append(a)
    remaining=set(adjacent);loops=[]
    while remaining:
        start=min(remaining);ordered=[start];previous=None;current=start
        while True:
            following=next(index for index in adjacent[current] if index!=previous)
            if following==start:break
            if following in ordered:raise RuntimeError('Garment seam boundary crosses itself')
            ordered.append(following);previous,current=current,following
        remaining.difference_update(ordered);loops.append([points[index] for index in ordered])
    evaluated.to_mesh_clear()
    for mod in muted:mod.show_viewport=True
    bpy.context.view_layer.update()
    return loops


def sew_work_shirt(make,material,morph,rig):
    shirt=bpy.data.objects['shirt_continuous_tailored_surface'];support=ClothSurface(shirt)
    finished_support=support
    vertices=[];faces=[]

    def fit(point):
        hit,normal,_,_=support.tree.find_nearest(point)
        return hit+normal*.0012,normal

    def stitch(a,b):
        fitted=[fit(a.lerp(b,t)) for t in (0,.5,1)]
        start=len(vertices);sides=5
        for i,(point,normal) in enumerate(fitted):
            tangent=fitted[min(i+1,2)][0]-fitted[max(i-1,0)][0]
            lateral=tangent.normalized().cross(normal).normalized()
            for j in range(sides):
                angle=j*math.tau/sides
                vertices.append(point+normal*(.00065*math.cos(angle))+lateral*(.00065*math.sin(angle)))
        faces.extend(tuple(start+r*sides+j for r,j in [(row,col),(row,(col+1)%sides),(row+1,(col+1)%sides),(row+1,col)])
                     for row in range(2) for col in range(sides))

    def sew(path,closed=False):
        segments=list(zip(path,path[1:]+path[:1] if closed else path[1:]))
        lengths=[(b-a).length for a,b in segments];total=sum(lengths)
        def along(distance):
            for (a,b),length in zip(segments,lengths):
                if distance<=length:return a.lerp(b,distance/max(length,1e-8))
                distance-=length
            return segments[-1][1]
        for distance in np.arange(.001,total-.004,.006):stitch(along(distance),along(distance+.0032))

    for loop in garment_boundaries(shirt):
        center=sum(loop,Vector())/len(loop)
        if abs(center.x)<.30:continue
        side='L' if center.x>0 else 'R'
        inward=(rig.data.bones['forearm_'+side].head_local-center).normalized()
        for offset in (.008,.017):sew([point+inward*offset for point in loop],True)
    # Guided shoulder stations can lie inside the sleeve. Only the exterior
    # cloth is a sewing support; the thickness lining must not attract a seam.
    thickness=[mod for mod in shirt.modifiers if mod.type=='SOLIDIFY' and mod.show_viewport]
    try:
        for mod in thickness:mod.show_viewport=False
        bpy.context.view_layer.update()
        support=ClothSurface(shirt)
    finally:
        for mod in thickness:mod.show_viewport=True
        bpy.context.view_layer.update()
    for side in (-1,1):
        stations=[morph((side*x,y,z)) for x,y,z in [(.13,.018,1.55),(.23,.020,1.51),(.31,.010,1.44),(.37,-.025,1.32),(.43,-.094,1.22)]]
        path=[]
        for a,b in zip(stations,stations[1:]):path.extend(a.lerp(b,t/8) for t in range(8))
        path.append(stations[-1])
        for offset in (-.0025,.0025):sew([point+Vector((0,offset,0)) for point in path])
    thread=material('farmer_shirt_sewing_thread',(.29,.225,.14),.92)
    obj=make('farmer_shirt_sewn_seams',vertices,faces,thread,'hips')
    bind_detail(obj,[finished_support])


def finish_apron(apron,authored,waist,work):
    """Use maps follow this apron and its pockets, never arbitrary global dirt."""
    size=1024;v,u=np.mgrid[0:size,0:size]/(size-1)
    x=u*.60-.30;z=v*.75+.34
    distance=np.full_like(x,2.)
    for loop in garment_boundaries(apron):
        # The finished subdivided boundary is dense; its control-length pieces
        # can be sampled at 5 mm without moving the painted edge beyond a pixel.
        sampled=[loop[0]]
        for point in loop[1:]:
            if (point-sampled[-1]).length>=.005:sampled.append(point)
        for a,b in zip(sampled,sampled[1:]+sampled[:1]):
            dx,dz=b.x-a.x,b.z-a.z
            t=np.clip(((x-a.x)*dx+(z-a.z)*dz)/max(dx*dx+dz*dz,1e-12),0,1)
            distance=np.minimum(distance,np.hypot(x-a.x-dx*t,z-a.z-dz*t))
    edge=np.exp(-(distance/.0045)**2)
    use=np.zeros_like(x);mouth=np.zeros_like(x)
    for sign in (-1,1):
        use+=np.exp(-((x-sign*.105)/.075)**2-((z-(waist-.09))/.062)**2)
        mouth=np.maximum(mouth,np.exp(-((z-(waist-.05))/.004)**2)*np.exp(-((x-sign*.103)/.085)**8))
    # Irregular leather pores support the use marks without replacing them.
    yy,xx=np.mgrid[0:size,0:size]
    pore=np.sin(xx*.73+np.sin(yy*.31))*np.sin(yy*.81+np.cos(xx*.19))
    grain=.12*pore+.055*np.sin(xx*.21+yy*.17)
    relief=grain-.018*edge
    gy,gx=np.gradient(relief);normal=np.stack((-gx*.9,-gy*.9,np.ones_like(gx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    pigment=.92+.035*pore+.10*np.minimum(use,1)-.10*edge+.12*mouth
    base=np.array([.24,.105,.046])[None,None,:]*pigment[:,:,None]
    rough=np.clip(.83-.20*edge-.10*mouth-.055*np.minimum(use,1)+.025*pore,.52,.9)
    mat=bpy.data.materials.new('artisan_use_worn_apron_leather');mat.use_nodes=True
    shader=mat.node_tree.nodes['Principled BSDF']
    for channel,data in [('basecolor',base),('normal',normal*.5+.5),('roughness',np.repeat(rough[:,:,None],3,axis=2))]:
        rgba=np.ones((size,size,4),np.float32);rgba[:,:,:3]=data
        image=bpy.data.images.new('artisan_apron_'+channel,width=size,height=size,alpha=True)
        image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        image.pixels.foreach_set(rgba.ravel());image.filepath_raw=str(work/'textures'/('artisan_apron_'+channel+'.png'))
        image.file_format='PNG';image.save();image.pack()
        texture=mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
        if channel=='normal':
            node=mat.node_tree.nodes.new('ShaderNodeNormalMap');node.uv_map='UVMap';node.inputs['Strength'].default_value=.45
            mat.node_tree.links.new(texture.outputs['Color'],node.inputs['Color']);mat.node_tree.links.new(node.outputs['Normal'],shader.inputs['Normal'])
        else:mat.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    for obj in authored:
        if obj!=apron and not obj.name.startswith(('apron_bound_perimeter','artisan_apron_tool_pocket','pocket_bound_edge','pocket_rolled_mouth')):continue
        obj.data.materials.clear();obj.data.materials.append(mat)
        for face in obj.data.polygons:
            face.material_index=0
            for index in face.loop_indices:
                point=obj.matrix_world@obj.data.vertices[obj.data.loops[index].vertex_index].co
                obj.data.uv_layers.active.data[index].uv=((point.x+.30)/.60,(point.z-.34)/.75)
