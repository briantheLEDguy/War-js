"""Retained female face with an original fitted, swept and braided work groom."""
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AUTHORING_INPUTS=set()
WORK=Path(__file__).resolve().parents[1]


def build_head(make,sweep,body,rig,materials):
    hair=bpy.data.materials.new('herbalist_chestnut_hair');hair.use_nodes=True
    shader=hair.node_tree.nodes['Principled BSDF'];shader.inputs['Roughness'].default_value=.84
    size=512;yy,xx=np.mgrid[0:size,0:size]
    strands=np.sin(xx*.47+.28*np.sin(yy*.012))*.5+np.sin(xx*1.38+yy*.001)*.18
    dye=.86+.09*strands+.035*np.sin(xx*.024+yy*.01)
    for channel,data in [('basecolor',np.array([.115,.060,.032])[None,None,:]*dye[:,:,None]),
                         ('normal',np.stack((.5+.07*np.cos(xx*.47),np.full_like(xx,.5,dtype=float),np.ones_like(xx,dtype=float)),axis=-1))]:
        rgba=np.ones((size,size,4),np.float32);rgba[:,:,:3]=data
        image=bpy.data.images.new('herbalist_hair_'+channel,width=size,height=size,alpha=True)
        image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        image.pixels.foreach_set(rgba.ravel());image.file_format='PNG'
        image.filepath_raw=str(WORK/'textures'/('herbalist_hair_'+channel+'.png'));image.save();image.pack()
        texture=hair.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
        if channel=='normal':
            normal=hair.node_tree.nodes.new('ShaderNodeNormalMap');normal.uv_map='UVMap';normal.inputs['Strength'].default_value=.35
            hair.node_tree.links.new(texture.outputs['Color'],normal.inputs['Color']);hair.node_tree.links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        else:hair.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
    body.data.update();tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    for side,sign in [('L',1),('R',-1)]:
        eye_mesh=next(o for o in bpy.data.objects if o.type=='MESH' and 'high-poly' in o.name)
        eye_vertices=[v.co for v in eye_mesh.data.vertices if v.co.x*sign>0]
        eye=sum(eye_vertices,Vector())/len(eye_vertices);points=[];radii=[]
        for i in range(15):
            t=i/14;x=eye.x+sign*(-.023+.047*t);z=eye.z+.024+.006*math.sin(t*math.pi)
            hit,normal,_,_=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
            if hit is None:raise RuntimeError('Herbalist brow has no anatomical support')
            points.append(hit+normal*.0011);radii.append(.0005+.0016*math.sin(t*math.pi))
        sweep('herbalist_fitted_brow',points,radii,hair,'head',6)
    selected=[]
    for face in body.data.polygons:
        p=face.center
        hairline=1.711+.083*max(0,min(1,(-p.y+.005)/.135))
        if p.z>hairline and abs(p.x)<.15:selected.append(tuple(face.vertices))
    used=sorted({i for face in selected for i in face});remap={i:j for j,i in enumerate(used)}
    vertices=[body.data.vertices[i].co+body.data.vertices[i].normal*.006 for i in used]
    faces=[tuple(remap[i] for i in face) for face in selected]
    scalp=make('herbalist_fitted_scalp',vertices,faces,hair,'head')
    finish=scalp.modifiers.new('Scalp_finish','SUBSURF');finish.levels=finish.render_levels=1
    shell=scalp.modifiers.new('Hairline_thickness','SOLIDIFY');shell.thickness=.003;shell.offset=0
    # Locks follow the actual retained female cranium, then gather at the nape.
    for side in (-1,1):
        for index in range(4):
            guide=[(side*(.008+.019*index),-.065+.009*index,1.853),
                   (side*(.04+.015*index),-.015,1.846-.012*index),
                   (side*(.05+.017*index),.035,1.813-.011*index),
                   (side*(.04+.014*index),.078,1.762-.006*index),
                   (side*.02,.101,1.716)]
            points=[];normals=[]
            for a,b in zip(guide,guide[1:]):
                for step in range(6):
                    p=Vector(a).lerp(Vector(b),step/6);hit,n,_,_=tree.find_nearest(p)
                    points.append(hit+n*.007);normals.append(n)
            hit,n,_,_=tree.find_nearest(Vector(guide[-1]));points.append(hit+n*.007);normals.append(n)
            verts=[];count=8
            for i,(p,n) in enumerate(zip(points,normals)):
                tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized();cross=tangent.cross(n).normalized()
                envelope=math.sin(math.pi*i/(len(points)-1))**.65
                for j in range(count):
                    angle=j/count*math.tau
                    verts.append(p+cross*math.sin(angle)*(.003+.009*envelope)+n*math.cos(angle)*(.001+.003*envelope))
            fs=[(r*count+j,r*count+(j+1)%count,(r+1)*count+(j+1)%count,(r+1)*count+j) for r in range(len(points)-1) for j in range(count)]
            fs.extend([tuple(reversed(range(count))),tuple((len(points)-1)*count+j for j in range(count))])
            make('herbalist_swept_nape_lock',verts,fs,hair,'head')
    # Three interwoven strands coil into a low, compact gathering knot.
    for strand in range(3):
        points=[];radii=[]
        for i in range(130):
            t=i/129;angle=t*math.tau*2.2;radius=.009+.047*t
            braid=angle*4+strand*math.tau/3
            x=(radius+.006*math.cos(braid))*math.sin(angle);z=1.746+(radius+.006*math.cos(braid))*math.cos(angle)
            hit,normal,_,_=tree.ray_cast(Vector((x,2,z)),Vector((0,-1,0)))
            if hit is None:hit,normal,_,_=tree.find_nearest(Vector((x,.10,z)))
            points.append(hit+normal*(.009+.006*math.sin(braid)))
            radii.append(.0055+.001*math.sin(math.pi*t))
        sweep('herbalist_coiled_braid',points,radii,hair,'head',8)
    # A short linen tie visibly binds the groom at its supporting nape.
    points=[]
    for i in range(41):
        a=i*math.tau/40;x=.020*math.sin(a);z=1.731+.008*math.cos(a)
        hit,normal,_,_=tree.ray_cast(Vector((x,2,z)),Vector((0,-1,0)))
        if hit is None:raise RuntimeError('Groom tie has no nape support')
        points.append(hit+normal*.008)
    sweep('herbalist_nape_tie',points,[.0027]*len(points),materials['seam'],'head',6)
