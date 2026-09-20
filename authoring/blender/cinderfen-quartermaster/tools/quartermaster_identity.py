"""Regional facial sculpt and rooted, curved tusks on retained anatomical mesh."""
import math,json
import bpy,bmesh,numpy as np
from mathutils import Vector

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def face_shape(point):
    x,y,z=point;mask=smooth(1.73,1.80,z)
    jaw=math.exp(-((z-1.82)/.073)**2)
    face=smooth(.035,.12,-y)
    brow=math.exp(-((z-1.944)/.025)**2)*face
    nose=math.exp(-((z-1.881)/.030)**2)*math.exp(-(x/.036)**2)*face
    # Continuous coordinate fields preserve eyelid, lip and cheek topology.
    xx=x*(1+mask*(.10+.23*jaw))
    yy=y-mask*(.038*jaw*face+.021*brow)+.007*nose
    zz=z-.032*smooth(1.96,2.046,z)
    ear=smooth(.073,.101,abs(x))*math.exp(-((z-1.91)/.072)**2)
    xx+=(1 if x>=0 else -1)*.022*ear
    zz+=.020*ear*smooth(1.89,1.93,z)
    return Vector((xx,yy,zz))

def sculpt(meshes,rig,work):
    removed=[]
    for obj in meshes:
        if obj.name=='teeth_and_mire_tusks':
            # Remove only the disconnected legacy tusks, retaining the original
            # teeth/gum geometry inside the mouth and its weights.
            bm=bmesh.new();bm.from_mesh(obj.data)
            pending=set(bm.verts)
            while pending:
                start=pending.pop();component={start};queue=[start]
                while queue:
                    v=queue.pop()
                    for edge in v.link_edges:
                        adjacent=edge.other_vert(v)
                        if adjacent in pending:pending.remove(adjacent);component.add(adjacent);queue.append(adjacent)
                if min(v.co.y for v in component)<-.20:
                    removed.append({'vertices':len(component),'minimumY':min(v.co.y for v in component)})
                    bmesh.ops.delete(bm,geom=list(component),context='VERTS')
            bm.to_mesh(obj.data);bm.free()
        for vertex in obj.data.vertices:
            if vertex.co.z>1.73:vertex.co=face_shape(vertex.co)
        obj.data.update()
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        if bone.head.z>1.73:bone.head=face_shape(bone.head)
        if bone.tail.z>1.73:bone.tail=face_shape(bone.tail)
    bpy.ops.object.mode_set(mode='OBJECT')
    for obj in meshes:
        for mat in obj.data.materials:
            if not mat or '.body' not in mat.name:continue
            shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.84
            node=shader.inputs['Base Color'].links[0].from_node
            if node.type=='TEX_IMAGE':
                image=node.image.copy();image.name='cinderfen_quartermaster_umber_olive_skin'
                pixels=np.array(image.pixels[:],dtype=np.float32).reshape(-1,4)
                pixels[:,:3]*=np.array([.39,.56,.30])
                image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(work/'textures'/f'{image.name}.png');image.file_format='PNG';image.save();image.pack();node.image=image
    (work/'source/facial-sculpt.json').write_text(json.dumps({'method':'continuous anatomical mesh deformation','legacyTuskComponentsRemoved':removed,'sculptedFeatures':['broad mandibular angle','projecting lower muzzle','low heavy brow','broad nose','shortened cranium','pointed lateral ears'],'newTusks':'rooted curved profiles from lower lip corners'},indent=2))

def tusks(make,material):
    ivory=material('quartermaster_worn_ivory',(.49,.43,.28),.64,textile=True)
    for side in (-1,1):
        # The root is beneath the lower lip. A broad enamel shoulder narrows,
        # bends outwards and returns inwards at the polished, asymmetric tip.
        stations=[(.045,-.198,1.818,.0105,.0075),(.047,-.217,1.822,.011,.008),
                  (.050,-.231,1.832,.0103,.007),(.054,-.237,1.846,.0088,.006),
                  (.057,-.238,1.857,.0068,.0048),(.056,-.236,1.864,.0043,.003),
                  (.053,-.232,1.871,.0011,.001)]
        vertices=[];count=14
        centers=[Vector((side*x,y,z+(-0.004 if side<0 else 0))) for x,y,z,_,_ in stations]
        for row,(center,station) in enumerate(zip(centers,stations)):
            tangent=centers[min(row+1,len(centers)-1)]-centers[max(0,row-1)]
            across=Vector((1,0,0));other=tangent.normalized().cross(across).normalized()
            for i in range(count):
                a=i/count*math.tau;ripple=1+.025*math.sin(a*3+row*.8)
                vertices.append(center+across*(math.cos(a)*station[3]*ripple)+other*(math.sin(a)*station[4]*ripple))
        faces=[(r*count+i,r*count+(i+1)%count,(r+1)*count+(i+1)%count,(r+1)*count+i) for r in range(len(stations)-1) for i in range(count)]
        faces.extend([tuple(reversed(range(count))),tuple((len(stations)-1)*count+i for i in range(count))])
        tooth=make('quartermaster_curved_lower_tusk_'+str(side),vertices,faces,ivory,'jaw')
        sub=tooth.modifiers.new('Enamel_continuity','SUBSURF');sub.levels=sub.render_levels=1
