"""Anatomically fitted scalp, jaw groom and fine facial hair for the artisan."""
import math
import random
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def build_groom(body, make, sweep, shape, hair):
    rng=random.Random(6249)
    tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    def front(x,z):
        hit=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))[0]
        if hit is None:
            hit=tree.find_nearest(Vector((x,-.18,z)))[0]
        return hit.y
    shades=[hair]
    for i in range(4):
        shade=hair.copy();shade.name='artisan_hair_tone_'+str(i)
        value=[(.048,.021,.010),(.09,.047,.023),(.15,.103,.069),(.27,.23,.19)][i]
        shade.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*value,1)
        shades.append(shade)
    cols=64;rows=24;vertices=[]
    def point(u,t):
        root=shape((u*.077,0,1.648+.041*abs(u)))
        x=root.x*(1-.64*t)
        z=root.z-.205*t*(1-.12*abs(u))
        y=front(root.x,root.z)-.004-.033*math.sin(math.pi*t)+.01*t
        y-=.0023*math.sin(u*math.pi*11+t*2)*math.sin(math.pi*t)
        return Vector((x,y,z))
    for r in range(rows):
        for c in range(cols+1):vertices.append(point(c/cols*2-1,r/(rows-1)))
    front_count=len(vertices)
    for r in range(rows):
        for c in range(cols+1):
            u=c/cols*2-1;t=r/(rows-1)
            vertices.append(vertices[r*(cols+1)+c]+Vector((0,.035*(1-u*u)*(1-t)+.002,0)))
    faces=[]
    for r in range(rows-1):
        for c in range(cols):
            a=r*(cols+1)+c;b=a+1;d=(r+1)*(cols+1)+c;e=d+1
            faces.extend([(a,b,e,d),(front_count+d,front_count+e,front_count+b,front_count+a)])
    boundary=list(range(cols+1))+[r*(cols+1)+cols for r in range(1,rows)]
    boundary+=list(range((rows-1)*(cols+1)+cols-1,(rows-1)*(cols+1)-1,-1))
    boundary+=[r*(cols+1) for r in range(rows-2,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.append((b,a,a+front_count,b+front_count))
    beard=make('fitted_full_jaw_groom',vertices,faces,hair,'head')
    sub=beard.modifiers.new('Continuous_groom_finish','SUBSURF');sub.levels=1;sub.render_levels=1
    # Short overlapping strands follow the groom instead of forming thick parallel rods.
    for i in range(440):
        u=rng.uniform(-.99,.99);start=rng.uniform(0,.65);end=min(1,start+rng.uniform(.22,.48))
        points=[]
        for j in range(9):
            t=start+(end-start)*j/8
            p=point(u+.009*math.sin(t*9+i),t);p.y-=.0014+math.sin(j/8*math.pi)*.001
            points.append(p)
        radius=rng.uniform(.00045,.00085)
        sweep('jaw_hair',points,[radius*(.75+.25*math.sin(j/8*math.pi))*(1-.7*(j/8)**4) for j in range(9)],
              rng.choices(shades,[5,4,3,1,.35])[0],'head',5)
    for side in [-1,1]:
        for i in range(90):
            t=i/89;root=shape((side*(.003+.026*t),0,1.672+.007*math.sin(t*math.pi)))
            root.y=front(root.x,root.z)-.001
            points=[root]
            for j in range(1,7):
                p=shape((side*(.003+.026*t+.031*j/6),0,1.672+.007*math.sin(t*math.pi)-.029*(j/6)**1.3))
                p.y=front(p.x,p.z)-.002-.002*math.sin(j/6*math.pi);points.append(p)
            sweep('mustache_hair',points,[.00065*(1-j/8) for j in range(7)],shades[i%3],'head',5)
        for i in range(95):
            t=i/94;x=side*(.012+.06*t);z=1.754+.009*math.sin(t*math.pi)+rng.uniform(-.003,.003)
            points=[]
            for j in range(4):
                p=shape((x+side*.009*j/3,0,z+.004*math.sin(j/3*math.pi)-.003*j/3))
                p.y=front(p.x,p.z)-.0012;points.append(p)
            sweep('brow_hair',points,[.00065,.0008,.0005,.00015],shades[i%3],'head',5)
    # The scalp retains real head topology. Relax only its cut boundary onto the anatomy.
    def threshold(p):
        frontal=max(0,min(1,(-p.y-.025)/.14))
        return shape((0,0,1.714+.085*frontal)).z
    selected=[f for f in body.data.polygons if (p:=sum((body.data.vertices[v].co for v in f.vertices),Vector())/len(f.vertices)).z>threshold(p)]
    used=sorted({v for f in selected for v in f.vertices});mapping={old:new for new,old in enumerate(used)}
    coords=[body.data.vertices[v].co.copy() for v in used]
    faces=[tuple(mapping[v] for v in f.vertices) for f in selected];edges={};neighbors={i:set() for i in range(len(coords))}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1;neighbors[a].add(b);neighbors[b].add(a)
    boundary={v for edge,count in edges.items() if count==1 for v in edge}
    border={v:[n for n in neighbors[v] if n in boundary] for v in boundary}
    for _ in range(18):
        moved={}
        for v,adj in border.items():
            if len(adj)!=2:continue
            p=coords[v]*.6+sum((coords[n] for n in adj),Vector())*.2
            moved[v]=tree.find_nearest(p)[0]
        for v,p in moved.items():coords[v]=p
    for i,p in enumerate(coords):
        hit,normal,_,_=tree.find_nearest(p);coords[i]=hit+normal*.004
    scalp=make('fitted_scalloped_hairline',coords,faces,hair,'head')
    solid=scalp.modifiers.new('Short_hair_depth','SOLIDIFY');solid.thickness=.003
    for i in range(650):
        p=coords[rng.randrange(len(coords))]
        _,normal,_,_=tree.find_nearest(p)
        tangent=Vector((.15,1,-.2));tangent=(tangent-normal*tangent.dot(normal)).normalized()
        points=[p+tangent*(j/4)*.023+normal*(.0007+.001*math.sin(j/4*math.pi)) for j in range(5)]
        sweep('scalp_hair',points,[.0006,.0008,.0007,.0004,.0001],rng.choices(shades,[7,4,2,1,.15])[0],'head',5)
