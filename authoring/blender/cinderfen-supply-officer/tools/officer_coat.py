"""Extend the continuous coat waist into two joined, weighted skirt panels."""
import bpy,bmesh,math
from mathutils import Vector
from surface_bindings import ClothSurface


def extend_coat():
    obj=bpy.data.objects['shirt_continuous_tailored_surface'];old=obj.data
    points=[v.co.copy() for v in old.vertices];faces=[tuple(f.vertices) for f in old.polygons]
    old_uv=[[tuple(old.uv_layers.active.data[i].uv) for i in f.loop_indices] for f in old.polygons]
    fields=[[(obj.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in old.vertices]
    edges={}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
    low=min(p.z for p in points)
    hem_edges=[(a,b) for (a,b),count in edges.items() if count==1 and abs(points[a].z-low)<.002 and abs(points[b].z-low)<.002]
    adjacency={}
    for a,b in hem_edges:adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
    if not adjacency or any(len(n)!=2 for n in adjacency.values()):raise RuntimeError('Coat has no continuous waist boundary')
    first=min(adjacency);ordered=[first];previous=None;current=first
    while True:
        following=next(i for i in adjacency[current] if i!=previous)
        if following==first:break
        ordered.append(following);previous,current=current,following
    count=len(ordered);rows=7;old_count=len(points);old_faces=len(faces)
    support=ClothSurface(bpy.data.objects['trousers_continuous_tailored_surface'])
    def exterior(point):
        direction=Vector((point.x,point.y,0)).normalized();origin=Vector((0,0,point.z));cursor=origin.copy();outer=0
        for _ in range(12):
            hit,_,_,_=support.tree.ray_cast(cursor,direction,.8)
            if hit is None:break
            outer=max(outer,(hit-origin).length);cursor=hit+direction*.0005
        if outer:point=origin+direction*max((point-origin).length,outer+.024)
        hit,_,triangle,_=support.tree.find_nearest(point)
        return point,sorted(support.weights(hit,triangle).items(),key=lambda row:-row[1])[:4]
    for original in ordered:points[original],fields[original]=exterior(points[original])
    index=lambda r,c:ordered[c%count] if r==0 else old_count+(r-1)*count+c%count
    for row in range(1,rows+1):
        t=row/rows
        for original in ordered:
            p=points[original].copy();side='L' if p.x>=0 else 'R'
            p.x*=1+.22*t;p.y*=1+.19*t;p.y+=math.copysign(.017*t,p.y);p.z-=.155*t
            p.z+=.014*t*math.exp(-(p.x/.037)**2)
            p,weights=exterior(p)
            points.append(p);fields.append(weights)
    for row in range(rows):
        for c in range(count):
            a=points[ordered[c]];b=points[ordered[(c+1)%count]]
            # Open front and rear vents begin at the existing coat hem. Both
            # tails remain part of the same shoulder-to-waist garment mesh.
            if abs((a.x+b.x)*.5)<.024:continue
            faces.append((index(row,c),index(row,c+1),index(row+1,c+1),index(row+1,c)))
    # Remove vertices omitted by the two vents before creating the final cage.
    used=sorted({i for face in faces for i in face});remap={v:i for i,v in enumerate(used)}
    mesh=bpy.data.meshes.new('continuous_joined_supply_coat');mesh.from_pydata([points[i] for i in used],[],[tuple(remap[i] for i in face) for face in faces]);mesh.update()
    cloth=old.materials[0];skirt=cloth.copy();skirt.name='officer_split_coat'
    mesh.materials.append(cloth);mesh.materials.append(skirt);uv=mesh.uv_layers.new(name='UVMap')
    for face,values in zip(mesh.polygons,old_uv):
        for loop,value in zip(face.loop_indices,values):uv.data[loop].uv=value
    for face in list(mesh.polygons)[old_faces:]:
        face.material_index=1
        for loop in face.loop_indices:
            p=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=(math.atan2(p.y,p.x)/math.tau*4,p.z*4)
    # Joined panels must share the upper coat's outward orientation before
    # thickness is generated, not only after triangulation at export time.
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj.data=mesh;obj.vertex_groups.clear()
    for i,original in enumerate(used):
        values=fields[original];total=sum(w for _,w in values)
        for name,weight in values:
            group=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name);group.add([i],weight/total,'REPLACE')
    for face in mesh.polygons:face.use_smooth=True
