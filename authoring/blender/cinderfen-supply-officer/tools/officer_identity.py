"""Original Dark Elf anatomy and close-fitted swept, tied hair construction."""
import math,json
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def smooth(a,b,value):
    t=max(0,min(1,(value-a)/(b-a)));return t*t*(3-2*t)


def facial_shape(p):
    x,y,z=p;front=smooth(.025,.09,-y)
    cheek=math.exp(-((z-1.612)/.032)**2)*front
    jaw=math.exp(-((z-1.550)/.036)**2)*front
    brow=math.exp(-((z-1.665)/.018)**2)*front
    ear=smooth(.078,.091,abs(x))*smooth(-.075,-.035,y)*math.exp(-((z-1.638)/.027)**2)
    return Vector((x*(1+.045*cheek-.065*jaw)+(1 if x>=0 else -1)*.043*ear,
                   y-.005*cheek-.003*brow,
                   z+.048*ear+.003*brow*min(1,abs(x)/.06)))


def sculpt(meshes,rig,work):
    for obj in meshes:
        for v in obj.data.vertices:
            if v.co.z>1.49:v.co=facial_shape(v.co)
        obj.data.update()
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        if bone.head.z>1.49:bone.head=facial_shape(bone.head)
        if bone.tail.z>1.49:bone.tail=facial_shape(bone.tail)
    bpy.ops.object.mode_set(mode='OBJECT')
    for obj in meshes:
        for mat in obj.data.materials:
            if not mat or '.body' not in mat.name:continue
            shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Roughness'].default_value=.76
            node=shader.inputs['Base Color'].links[0].from_node
            if node.type=='TEX_IMAGE':
                image=node.image.copy();image.name='cinderfen_officer_cool_skin'
                pixels=np.array(image.pixels[:],np.float32).reshape(-1,4)
                luma=pixels[:,:3]@np.array([.24,.52,.24]);pixels[:,:3]=luma[:,None]*np.array([.76,.69,.84])
                image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(work/'textures'/f'{image.name}.png');image.file_format='PNG';image.save();image.pack();node.image=image
    (work/'source/facial-sculpt.json').write_text(json.dumps({'method':'continuous retained facial topology and matching rest joints','features':['raised lateral cheek plane','tapered lower jaw','arched brow','long swept ears','cool mineral-marsh complexion'],'hair':'original continuous fitted scalp and swept tied hair'},separators=(',',':')))


def dress_hair(body,make,sweep,material):
    hair=material('officer_directional_hair',(.021,.018,.032),.72,textile=True)
    tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get());center=Vector((0,-.029,1.755))
    def cap(phi,t):
        front=max(0,-math.sin(phi));back=max(0,math.sin(phi));limit=1.57-.38*front+.28*back
        polar=.008+t*limit;direction=Vector((math.sin(polar)*math.cos(phi),math.sin(polar)*math.sin(phi),math.cos(polar)))
        hit,normal,_,_=tree.ray_cast(center,direction,.25)
        if hit is None:raise RuntimeError('Hair has no anatomical scalp support')
        return hit+direction*(.0045+.00035*math.sin(phi*26+t*5)**2)
    count=72;rows=18;points=[cap(i*math.tau/count,r/(rows-1)) for r in range(rows) for i in range(count)]
    faces=[(r*count+i,r*count+(i+1)%count,(r+1)*count+(i+1)%count,(r+1)*count+i) for r in range(rows-1) for i in range(count)]
    faces.append(tuple(reversed(range(count))))
    obj=make('officer_continuous_swept_scalp',points,faces,hair,'head')
    for face in obj.data.polygons:
        for loop in face.loop_indices:
            vertex=obj.data.loops[loop].vertex_index
            obj.data.uv_layers.active.data[loop].uv=((vertex%count)/count*2,(vertex//count)/(rows-1))
    thick=obj.modifiers.new('Dense_hair_surface','SOLIDIFY');thick.thickness=.002
    for index in range(48):
        phi=index*math.tau/48;path=[cap(phi+.15*math.sin(t*math.pi),t) for t in np.linspace(.09,.99,22)]
        sweep('officer_swept_hair_lock',path,[.00065+.00045*math.sin(i/21*math.pi) for i in range(22)],hair,'head',6)
    for side in (-1,1):
        for index in range(24):
            t=index/23;x=side*(.013+.040*t);z=1.735+.005*math.sin(t*math.pi)-.003*t
            points=[]
            for dx,dz in [(0,0),(side*.0015,.0025),(side*.003,.0035)]:
                hit=tree.ray_cast(Vector((x+dx,-2,z+dz)),Vector((0,1,0)))[0]
                if hit is None:raise RuntimeError('Brow has no facial support')
                points.append(hit+Vector((0,-.00065,0)))
            sweep('officer_brow_fiber',points,[.00065,.0005,.00015],hair,'head',5)
    # A compact coiled knot has an authored, flattened profile and a buried root.
    points=[];sections=54;sides=12;knot_root=cap(math.pi/2,.82)
    for i in range(sections):
        t=i/(sections-1);a=t*math.tau*2.15
        center=knot_root+Vector((math.sin(a)*(.029-.007*t),.003+.010*math.cos(a),.036*(t-.5)))
        tangent=Vector((math.cos(a),-.35*math.sin(a),.16)).normalized();across=Vector((0,1,0));up=tangent.cross(across).normalized()
        for j in range(sides):
            angle=j*math.tau/sides;points.append(center+across*(.009*math.cos(angle))+up*(.008*math.sin(angle)))
    faces=[(r*sides+j,r*sides+(j+1)%sides,(r+1)*sides+(j+1)%sides,(r+1)*sides+j) for r in range(sections-1) for j in range(sides)]
    faces.extend([tuple(reversed(range(sides))),tuple((sections-1)*sides+j for j in range(sides))])
    make('officer_coiled_hair_knot',points,faces,hair,'head')
