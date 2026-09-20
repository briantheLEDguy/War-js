"""Original ash-blond swept scout groom fitted to retained female anatomy."""
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

AUTHORING_INPUTS=set()
WORK=Path(__file__).resolve().parents[1]


def build_head(make,sweep,body,rig,materials,shape):
    hair=bpy.data.materials.new('scout_ash_blond_hair');hair.use_nodes=True
    shader=hair.node_tree.nodes['Principled BSDF'];shader.inputs['Roughness'].default_value=.8
    size=512;yy,xx=np.mgrid[0:size,0:size]
    strands=np.sin(xx*math.tau*39/size+.25*np.sin(yy*math.tau/size))*.6+np.sin(xx*math.tau*91/size)*.18
    pigment=.83+.11*strands+.035*np.sin(xx*math.tau*3/size+yy*math.tau/size)
    for channel,data in [('basecolor',np.array([.35,.29,.18])[None,None,:]*pigment[:,:,None]),
                         ('normal',np.stack((.5+.055*np.cos(xx*math.tau*39/size),np.full_like(xx,.5,dtype=float),np.ones_like(xx,dtype=float)),axis=-1))]:
        rgba=np.ones((size,size,4),np.float32);rgba[:,:,:3]=data
        image=bpy.data.images.new('scout_hair_'+channel,width=size,height=size,alpha=True)
        image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        image.pixels.foreach_set(rgba.ravel());image.file_format='PNG';image.filepath_raw=str(WORK/'textures'/('scout_hair_'+channel+'.png'))
        image.save();image.pack();texture=hair.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
        if channel=='normal':
            normal=hair.node_tree.nodes.new('ShaderNodeNormalMap');normal.uv_map='UVMap';normal.inputs['Strength'].default_value=.3
            hair.node_tree.links.new(texture.outputs['Color'],normal.inputs['Color']);hair.node_tree.links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        else:hair.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
    body.data.update();tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    for side,sign in [('L',1),('R',-1)]:
        eye_mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH' and 'high-poly' in o.name)
        eye_points=[v.co for v in eye_mesh.data.vertices if v.co.x*sign>0]
        eye=Vector(((min(p.x for p in eye_points)+max(p.x for p in eye_points))*.5,0,(min(p.z for p in eye_points)+max(p.z for p in eye_points))*.5))
        points=[];radii=[]
        for i in range(17):
            t=i/16;x=eye.x+sign*(-.022+.046*t);z=eye.z+.021+.005*math.sin(t*math.pi)
            hit,normal,_,_=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
            if hit is None:raise RuntimeError('Scout brow has no anatomical support')
            points.append(hit+normal*.0012);radii.append(.0005+.0014*math.sin(t*math.pi))
        sweep('scout_fitted_brow',points,radii,hair,'head',6)
    selected=[]
    for face in body.data.polygons:
        p=face.center;unscaled=Vector((p.x/.94,p.y/.97,p.z/1.055))
        hairline=1.714+.080*max(0,min(1,(-unscaled.y+.005)/.135))
        if unscaled.z>hairline and abs(unscaled.x)<.12:selected.append(tuple(face.vertices))
    used=sorted({i for face in selected for i in face});remap={i:j for j,i in enumerate(used)}
    scalp=make('scout_fitted_scalp',[body.data.vertices[i].co+body.data.vertices[i].normal*.0055 for i in used],
               [tuple(remap[i] for i in f) for f in selected],hair,'head')
    finish=scalp.modifiers.new('Scalp_surface_finish','SUBSURF');finish.levels=finish.render_levels=1
    shell=scalp.modifiers.new('Hairline_turned_thickness','SOLIDIFY');shell.thickness=.003;shell.offset=0
    # Individually sectioned locks follow the measured cranium, with an offset
    # part and exposed ears rather than a helmet-shaped disconnected hair cap.
    for side in (-1,1):
        for index in range(10):
            guide=[(side*(.009+.012*index),-.059+.008*index,1.857),
                   (side*(.029+.012*index),-.023,1.849-.007*index),
                   (side*(.040+.009*index),.024,1.824-.007*index),
                   (side*(.025+.009*index),.058,1.787-.008*index),
                   (side*.019,.084,1.750)]
            if index>=6:
                k=index-6
                guide=[(side*(.006+.009*k),-.061,1.858),(side*(.024+.011*k),-.090,1.849-.003*k),
                       (side*(.042+.010*k),-.123,1.822-.004*k),(side*(.068+.004*k),-.109,1.799-.006*k),
                       (side*(.079+.002*k),-.065,1.782-.005*k)]
            points=[];normals=[]
            for a,b in zip(guide,guide[1:]):
                for step in range(7):
                    target=shape(Vector(a).lerp(Vector(b),step/7));hit,n,_,_=tree.find_nearest(target)
                    points.append(hit+n*.007);normals.append(n)
            hit,n,_,_=tree.find_nearest(shape(guide[-1]));points.append(hit+n*.007);normals.append(n)
            vertices=[];count=8
            for i,(p,n) in enumerate(zip(points,normals)):
                tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized();cross=tangent.cross(n).normalized()
                envelope=math.sin(math.pi*i/(len(points)-1))**.65
                for j in range(count):
                    angle=j/count*math.tau
                    vertices.append(p+cross*math.sin(angle)*(.002+.007*envelope)+n*math.cos(angle)*(.001+.003*envelope))
            faces=[(r*count+j,r*count+(j+1)%count,(r+1)*count+(j+1)%count,(r+1)*count+j) for r in range(len(points)-1) for j in range(count)]
            faces.extend([tuple(reversed(range(count))),tuple((len(points)-1)*count+j for j in range(count))])
            make('scout_swept_back_lock',vertices,faces,hair,'head')
    # Compact three-strand braid stays above the shoulder harness and is tied
    # at both ends. It is carried by the head rather than nearest chest weights.
    anchor_z=shape((0,0,1.745)).z
    anchor=tree.ray_cast(Vector((0,2,anchor_z)),Vector((0,-1,0)))[0]
    if anchor is None:raise RuntimeError('Braid requires an actual scalp support')
    braid_cy=anchor.y+.011
    for strand in range(3):
        points=[];radii=[]
        for i in range(97):
            t=i/96;phase=t*math.tau*5+strand*math.tau/3
            points.append(Vector((.010*math.sin(phase),braid_cy+.010*math.cos(phase)+.004*t,anchor_z-.116*t)))
            radii.append(.006*(1-.43*t))
        sweep('scout_nape_braid',points,radii,hair,'head',8)
    for z,radius,cy in [(anchor_z,.016,braid_cy),(anchor_z-.11,.010,braid_cy+.004)]:
        path=[Vector((radius*math.sin(i*math.tau/40),cy+radius*math.cos(i*math.tau/40),z)) for i in range(41)]
        sweep('scout_braid_wrap',path,[.0023]*len(path),materials['leather'],'head',6)
