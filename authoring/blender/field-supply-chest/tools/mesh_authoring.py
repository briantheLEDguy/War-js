"""Explicit fitted polygon construction; no mesh primitive operators."""
import math
import bpy, bmesh
from mathutils import Vector

BEAM = [(-.43,-.5),(.39,-.5),(.5,-.37),(.5,.35),(.37,.5),(-.38,.5),(-.5,.34),(-.5,-.36)]
ROUND = [(math.cos(i*math.tau/16)*.5,math.sin(i*math.tau/16)*.5) for i in range(16)]

def explicit(name, vertices, faces, material, uv=None, smooth=False, bevel=0):
    mesh=bpy.data.meshes.new(name+'.cage');mesh.from_pydata(vertices,[],faces);mesh.update()
    mesh.materials.append(material);mesh.uv_layers.new(name='authored_uv')
    for polygon in mesh.polygons:
        polygon.use_smooth=smooth
        coords=uv[polygon.index] if uv else [(vertices[v][0],vertices[v][1]) for v in polygon.vertices]
        for loop,coord in zip(polygon.loop_indices,coords):mesh.uv_layers[0].data[loop].uv=coord
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    obj['authoredPart']=name;obj['construction']='explicit tailored polygon mesh';obj['bevelWidth']=bevel
    return obj

def loft(name, stations, material, section=BEAM, smooth=False, bevel=.002, guide=(0,0,1), closed_path=False):
    vertices=[];faces=[];uv=[];runs=[];run=0
    for index,station in enumerate(stations):
        p=Vector(station[:3]);before=Vector(stations[(index-1)%len(stations) if closed_path else max(0,index-1)][:3]);after=Vector(stations[(index+1)%len(stations) if closed_path else min(len(stations)-1,index+1)][:3]);tangent=(after-before).normalized()
        ref=Vector(guide)
        if abs(tangent.dot(ref))>.94:ref=Vector((0,1,0))
        side=ref.cross(tangent).normalized();up=tangent.cross(side).normalized()
        if index:run+=(p-Vector(stations[index-1][:3])).length
        runs.append(run)
        vertices.extend(list(p+side*(a*station[3])+up*(b*station[4])) for a,b in section)
    n=len(section)
    for row in range(len(stations) if closed_path else len(stations)-1):
        following=(row+1)%len(stations)
        endrun=runs[following] if following else runs[-1]+(Vector(stations[-1][:3])-Vector(stations[0][:3])).length
        for j in range(n):
            k=(j+1)%n;faces.append([row*n+j,row*n+k,following*n+k,following*n+j])
            uv.append([(j/n,runs[row]),((j+1)/n,runs[row]),((j+1)/n,endrun),(j/n,endrun)])
    if not closed_path:
        faces.extend([list(reversed(range(n))),list(range((len(stations)-1)*n,len(stations)*n))]);uv.extend([list(reversed(section)),list(section)])
    return explicit(name,vertices,faces,material,uv,smooth,bevel)

def beam(name,a,b,width,height,material,bevel=.002):
    # Extra end stations permit dressed end edges without repeated coplanar blocks.
    a=Vector(a);b=Vector(b);d=b-a
    return loft(name,[(*(a+d*t),width*(.985 if t in(0,1) else 1),height) for t in(0,.05,.48,.95,1)],material,bevel=bevel)

def plate(name,outline,thickness,material,axis='Z',centre=0,bevel=.001):
    vertices=[]
    for offset in(-thickness/2,thickness/2):
        vertices.extend((a,b,centre+offset) if axis=='Z' else(a,centre+offset,b) if axis=='Y' else(centre+offset,a,b) for a,b in outline)
    n=len(outline);faces=[list(reversed(range(n))),list(range(n,2*n))];uv=[list(reversed(outline)),list(outline)]
    for i in range(n):
        j=(i+1)%n;faces.append([i,j,n+j,n+i]);uv.append([(0,0),(1,0),(1,thickness),(0,thickness)])
    return explicit(name,vertices,faces,material,uv,False,bevel)

def turned(name,centre,profile,material,lod,closed=True):
    # Profile travels around the actual outer and, when supplied, inner wall.
    n=(24,16,10)[lod];vertices=[];uv=[];faces=[]
    for row,(height,radius) in enumerate(profile):
        for i in range(n):
            angle=i*math.tau/n;variation=1+.018*math.sin(angle*3+row*.25)
            vertices.append((centre[0]+radius*math.cos(angle)*variation,centre[1]+radius*math.sin(angle),centre[2]+height))
    for row in range(len(profile)-1):
        for i in range(n):
            j=(i+1)%n;faces.append([row*n+i,row*n+j,(row+1)*n+j,(row+1)*n+i]);uv.append([(i/n,row/(len(profile)-1)),((i+1)/n,row/(len(profile)-1)),((i+1)/n,(row+1)/(len(profile)-1)),(i/n,(row+1)/(len(profile)-1))])
    if closed:
        for row,reverse in[(0,True),(len(profile)-1,False)]:
            ids=list(range(row*n,(row+1)*n));coords=[(.5+math.cos(i*math.tau/n)*.48,.5+math.sin(i*math.tau/n)*.48) for i in range(n)]
            faces.append(list(reversed(ids)) if reverse else ids);uv.append(list(reversed(coords)) if reverse else coords)
    return explicit(name,vertices,faces,material,uv,True,0)

def strand(name,points,width,material,lod):
    section=ROUND[::(1 if lod==0 else 2 if lod==1 else 4)]
    closed=(Vector(points[0])-Vector(points[-1])).length<1e-7
    return loft(name,[(*p,width,width) for p in(points[:-1] if closed else points)],material,section,True,0,closed_path=closed)

def leaf(name,base,tip,width,material,lod,phase):
    a=Vector(base);b=Vector(tip);direction=b-a;side=Vector((-direction.y,direction.x,.07)).normalized();normal=direction.cross(side).normalized()
    # A thick, curved lanceolate leaf with a central raised fold and closed edge.
    rows=(7,5,4)[lod];vertices=[];faces=[];uv=[]
    for layer in(-1,1):
        for r in range(rows):
            t=r/(rows-1);w=width*(.025+.975*math.sin(math.pi*t)**.8)
            centre=a+direction*t+normal*(math.sin(t*math.pi)*width*.25+math.sin(t*5+phase)*width*.08)
            for s in(-1,0,1):
                vertices.append(list(centre+side*w*.5*s+normal*((1-abs(s))*width*.12+layer*.00055)))
    half=rows*3
    for layer in range(2):
        for r in range(rows-1):
            for c in range(2):
                ids=[layer*half+r*3+c,layer*half+r*3+c+1,layer*half+(r+1)*3+c+1,layer*half+(r+1)*3+c]
                coords=[(c*.5,r/(rows-1)),((c+1)*.5,r/(rows-1)),((c+1)*.5,(r+1)/(rows-1)),(c*.5,(r+1)/(rows-1))]
                faces.append(ids if layer else list(reversed(ids)));uv.append(coords if layer else list(reversed(coords)))
    perimeter=[0,1,2]+[r*3+2 for r in range(1,rows)]+[(rows-1)*3+1,(rows-1)*3]+[r*3 for r in range(rows-2,0,-1)]
    for i,p in enumerate(perimeter):
        q=perimeter[(i+1)%len(perimeter)];faces.append([p,q,q+half,p+half]);uv.append([(0,0),(1,0),(1,.01),(0,.01)])
    return explicit(name,vertices,faces,material,uv,True,0)

def finish(objects,lod):
    for obj in objects:
        bpy.context.view_layer.objects.active=obj
        if lod<2 and obj['bevelWidth']:
            mod=obj.modifiers.new('dressed_handworked_edge','BEVEL');mod.width=obj['bevelWidth'];mod.segments=2 if lod==0 else 1;mod.limit_method='ANGLE';mod.angle_limit=math.radians(38);bpy.ops.object.modifier_apply(modifier=mod.name)
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.dissolve_degenerate(bm,dist=1e-9,edges=list(bm.edges));bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()

def cut_socket(receiver,cutter):
    bpy.context.view_layer.objects.active=receiver
    mod=receiver.modifiers.new('fitted_receiving_mortise','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
