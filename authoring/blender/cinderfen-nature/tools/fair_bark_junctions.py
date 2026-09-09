"""Fair only the original joined bark junctions; retain every source cage."""
import hashlib, json, math
from pathlib import Path
import bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
DESIGN=json.loads((ROOT/'source/nature.json').read_text())['design']

def fair_junctions(obj, lod):
    def geometry_hash():
        return hashlib.sha256(json.dumps({'vertices':[list(v.co) for v in obj.data.vertices],'faces':[list(p.vertices) for p in obj.data.polygons]},separators=(',',':')).encode()).hexdigest()
    before=geometry_hash()
    bm=bmesh.new();bm.from_mesh(obj.data)
    tag=bm.verts.layers.float.new('junction_fairing_weight')
    remaining=set(bm.verts);primary=None
    while remaining:
        seed=remaining.pop();component={seed};queue=[seed]
        while queue:
            current=queue.pop()
            for edge in current.link_edges:
                other=edge.other_vert(current)
                if other in remaining:
                    remaining.remove(other);component.add(other);queue.append(other)
        if min(v.co.z for v in component)<0 and max(v.co.z for v in component)>9:
            primary=component;break
    if primary is None:raise RuntimeError('Missing joined primary bark component')
    sockets=[Vector(path[0][:3]) for path in DESIGN['alderLimbs']]
    def smooth(v):
        v=max(0,min(1,v));return v*v*(3-2*v)
    def weight(point):
        root=smooth((1.35-math.hypot(point.x,point.y))/.75)*smooth((.9-abs(point.z-.25))/.5)
        limb=max(smooth((.9-(point-socket).length)/.5) for socket in sockets)
        return max(root,limb)
    for vertex in primary:vertex[tag]=weight(vertex.co)
    edges=[e for e in bm.edges if all(v in primary and v[tag]>.025 for v in e.verts) and e.calc_length()>.18]
    if lod==1:edges=sorted(edges,key=lambda e:e.calc_length()*min(v[tag] for v in e.verts),reverse=True)[:600]
    if lod==2:edges=[]
    subdivided_count=len(edges)
    if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
    selected=[v for v in bm.verts if v[tag]>.001]
    original={v:v.co.copy() for v in selected}
    # Alternating contraction/expansion removes junction noise while limiting
    # shrinkage. The hard displacement cap keeps authored trunk and limb forms.
    for _ in range(14 if lod==0 else 9):
        for coefficient in (.44,-.46):
            updates={}
            for vertex in selected:
                neighbors=[edge.other_vert(vertex).co for edge in vertex.link_edges]
                average=sum(neighbors,Vector())/len(neighbors)
                point=vertex.co+(average-vertex.co)*coefficient*vertex[tag]
                delta=point-original[vertex]
                if delta.length>.055:point=original[vertex]+delta.normalized()*.055
                updates[vertex]=point
            for vertex,point in updates.items():vertex.co=point
    moved=[(v.co-original[v]).length for v in selected]
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    invalid=sum(len(e.link_faces)!=2 for e in bm.edges)
    if invalid:raise RuntimeError(f'Junction fairing created {invalid} nonmanifold edges')
    record={'affectedVertices':sum(d>1e-7 for d in moved),'maximumDisplacementM':max(moved,default=0),'subdividedEdges':subdivided_count,'vertices':len(bm.verts),'triangles':len(bm.faces)}
    bm.to_mesh(obj.data);bm.free()
    for edge in obj.data.edges:edge.use_edge_sharp=False
    for face in obj.data.polygons:face.use_smooth=True
    obj.data.update()
    record.update({'tool':'tools/fair_bark_junctions.py','toolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'geometryBeforeSha256':before,'geometryAfterSha256':geometry_hash(),'displacementLimitM':.055,'nonManifoldEdges':0,'method':'Local support subdivision and bounded volume-preserving fairing of the connected primary bark shell at root and limb junctions; retained source cages and unattached fine shoots are unchanged.'})
    return record
