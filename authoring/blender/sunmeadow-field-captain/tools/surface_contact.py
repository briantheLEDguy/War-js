"""Parity contact for closed surfaces, independent of nearest open-face signs."""
from collections import Counter
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
_TOPOLOGY_CACHE={}
CONTAINMENT_DIAGNOSTICS=[]


class RaySurface:
    """Native broad phase with retained double-precision triangle evidence."""
    def __init__(self,points,faces):
        self.bvh=BVHTree.FromPolygons(points,faces,all_triangles=True)
        triangles=np.asarray(points,dtype=np.float64)[np.asarray(faces,dtype=int)]
        self.origins=triangles[:,0];self.edge1=triangles[:,1]-triangles[:,0];self.edge2=triangles[:,2]-triangles[:,0]

    def __getattr__(self,name):return getattr(self.bvh,name)

    def overlap(self,other):return self.bvh.overlap(other.bvh if isinstance(other,RaySurface) else other)

    def exact_inside(self,point):
        # Verify a reported containment against every actual triangle, avoiding
        # the BVH's float32 grazing-hit duplication. Shared-edge rays are
        # rejected and repeated with a different direction rather than guessed.
        origin=np.asarray(point,dtype=np.float64);offset=origin-self.origins
        for axis in ((.381966,.723607,.575),(-.61,.45,.65),(.45,-.73,.515)):
            direction=np.array(axis,dtype=np.float64);direction/=np.linalg.norm(direction)
            h=np.cross(direction,self.edge2);det=np.einsum('ij,ij->i',self.edge1,h)
            selected=np.abs(det)>1e-13
            inverse=np.zeros_like(det);inverse[selected]=1/det[selected]
            u=np.einsum('ij,ij->i',offset,h)*inverse;q=np.cross(offset,self.edge1)
            v=q@direction*inverse;t=np.einsum('ij,ij->i',self.edge2,q)*inverse
            hits=selected&(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)&(t>1e-10)
            if np.any(hits&((np.abs(u)<1e-9)|(np.abs(v)<1e-9)|(np.abs(1-u-v)<1e-9))):continue
            return bool(np.count_nonzero(hits)%2)
        raise RuntimeError('Exact containment rays all intersect a triangle edge')


def require_closed(points,faces,label):
    identities={i:tuple(float(v) for v in point) for i,point in enumerate(points)}
    counts=Counter(tuple(sorted((identities[a],identities[b]))) for face in faces
                   for a,b in zip(face,face[1:]+face[:1]) if identities[a]!=identities[b])
    invalid=[(edge,n) for edge,n in counts.items() if n!=2]
    if invalid:
        import json
        details=[{'edge':edge,'valence':n,'length':float(np.linalg.norm(np.array(edge[1])-np.array(edge[0])))} for edge,n in invalid]
        raise RuntimeError(f'{label} cannot support parity: {len(invalid)} non-manifold/boundary edges '+json.dumps(sorted(details,key=lambda r:-r['length'])[:8]))
    return {'edges':len(counts),'boundaryEdges':0,'nonManifoldEdges':0}


def connected_shells(points,faces):
    identities={i:tuple(float(v) for v in point) for i,point in enumerate(points)}
    users={}
    for i,face in enumerate(faces):
        for a,b in zip(face,face[1:]+face[:1]):
            users.setdefault(tuple(sorted((identities[a],identities[b]))),[]).append(i)
    adjacent=[set() for _ in faces]
    for rows in users.values():
        # A separately thickened collar shares its seam coordinates with the
        # shirt. Do not weld two closed solids into a four-face edge. Their
        # remaining edges identify each complete shell, which is then required
        # to be closed independently; no face or probe is dropped.
        if len(rows)==2:
            a,b=rows;adjacent[a].add(b);adjacent[b].add(a)
    remaining=set(range(len(faces)));shells=[]
    while remaining:
        queue=[remaining.pop()];indices=[]
        while queue:
            i=queue.pop();indices.append(i)
            for j in adjacent[i]:
                if j in remaining:remaining.remove(j);queue.append(j)
        shell=[faces[i] for i in indices]
        require_closed(points,shell,'connected cloth shell')
        shells.append(shell)
    return shells


def inside_closed(tree,point):
    # A nearly tangential float32 BVH hit can repeat its own triangle. Reject
    # that ray and try a distinct oblique direction; never count ambiguous
    # hits or accept a missing probe. Any unambiguous full crossing ray gives
    # the same parity on the already-proven closed surface.
    directions=((.381966,.723607,.575),(-.61,.45,.65),(.45,-.73,.515),
                (-.38,-.62,.689),(.79,.53,-.31),(-.72,.31,-.62),(.23,-.48,-.846))
    for axis in directions:
        direction=Vector(axis).normalized();origin=Vector(point);count=0;previous=None
        for _ in range(96):
            hit,normal,index,distance=tree.ray_cast(origin,direction)
            if hit is None:
                result=bool(count%2)
                if result and isinstance(tree,RaySurface):
                    exact=tree.exact_inside(point)
                    if not exact and len(CONTAINMENT_DIAGNOSTICS)<8:
                        CONTAINMENT_DIAGNOSTICS.append({'point':list(point),'nativeParity':True,'exactTriangleParity':False,'triangles':len(tree.origins)})
                    return exact
                return result
            alignment=abs(normal.dot(direction))
            if alignment<.035 or (previous==index and distance<.00002):break
            count+=1;previous=index
            origin=hit+direction*(.000004/alignment)
        else:raise RuntimeError('Closed-surface parity did not leave the object')
    raise RuntimeError('Every closed-surface parity direction was ambiguous')


def crossings(posed,subject,tree):
    target=bounded_tree(posed,subject)[0]
    pairs=target.overlap(tree)
    edges={tuple(sorted((a,b))) for i,_ in pairs for face in [subject[i]] for a,b in zip(face,face[1:]+face[:1])}
    count=0
    for a,b in edges:
        start=Vector(posed[a]);delta=Vector(posed[b])-start
        if delta.length<.00003:continue
        direction=delta.normalized()
        if tree.ray_cast(start+direction*.00001,direction,delta.length-.00002)[0] is not None:count+=1
    return count,len(pairs)


def signed_clearance(point,trees):
    closest=None;buried=None
    for tree,low,high in trees:
        in_bounds=all(low[i]<=point[i]<=high[i] for i in range(3))
        # Outside an AABB, the box distance is a lower bound for every surface
        # point. Such a shell cannot contain this probe or improve a closer
        # measured surface; this avoids redundant nearest queries only.
        if not in_bounds and closest is not None:
            lower_bound=sum(max(float(low[i])-point[i],point[i]-float(high[i]),0.)**2 for i in range(3))
            if lower_bound>=closest[0]**2:continue
        hit,n,triangle,distance=tree.find_nearest(Vector(point))
        if hit is None:raise RuntimeError('Required contact surface is empty')
        row=(distance,hit,n)
        if closest is None or distance<closest[0]:closest=row
        if in_bounds and inside_closed(tree,point) and (buried is None or distance<buried[0]):buried=row
    distance,hit,normal=buried or closest
    return (-distance if buried else distance),hit


def bounded_tree(points,faces,triangles=True):
    key=id(faces)
    if key not in _TOPOLOGY_CACHE:
        selected=np.array(sorted({i for face in faces for i in face}),dtype=int)
        remap={int(index):local for local,index in enumerate(selected)}
        local_faces=[tuple(remap[i] for i in face) for face in faces]
        if not triangles:
            # Explicitly triangulate the retained anatomical quad cage. A
            # deformed nonplanar quad must have separate triangle normals and
            # hit IDs, not one ambiguous polygon plane in the ray classifier.
            if any(len(face) not in (3,4) for face in local_faces):raise RuntimeError('Unsupported anatomical face')
            local_faces=[(face[0],face[i],face[i+1]) for face in local_faces for i in range(1,len(face)-1)]
        _TOPOLOGY_CACHE[key]=(faces,selected,local_faces)
    _,selected,local_faces=_TOPOLOGY_CACHE[key]
    bounds=np.asarray(points)[selected]
    return RaySurface(bounds,local_faces),bounds.min(axis=0),bounds.max(axis=0)


def signed_clearances(points,trees):
    """Batch AABB rejection with identical per-probe surface/parity queries."""
    probes=np.asarray(points);nearest=np.full(len(probes),np.inf);inside=np.full(len(probes),np.inf)
    closest=np.zeros_like(probes);buried=np.zeros_like(probes)
    for tree,low,high in trees:
        in_bounds=np.all((probes>=low)&(probes<=high),axis=1)
        deltas=np.maximum(np.maximum(low-probes,probes-high),0.)
        lower=np.einsum('ij,ij->i',deltas,deltas)
        for index in np.flatnonzero(in_bounds|(lower<=nearest*nearest)):
            point=Vector(probes[index]);hit,normal,triangle,distance=tree.find_nearest(point)
            if hit is None:raise RuntimeError('Required contact surface is empty')
            if distance<nearest[index]:nearest[index]=distance;closest[index]=hit
            if in_bounds[index] and inside_closed(tree,point) and distance<inside[index]:
                inside[index]=distance;buried[index]=hit
    contained=np.isfinite(inside)
    return np.where(contained,-inside,nearest),np.where(contained[:,None],buried,closest)


def skin_reference(points,fields,rig):
    result=np.zeros_like(points)
    for name,(indices,weights) in fields.items():
        matrix=np.array(rig.pose.bones[name].matrix@rig.data.bones[name].matrix_local.inverted())
        transformed=points[indices]@matrix[:3,:3].T+matrix[:3,3]
        result[indices]+=transformed*weights[:,None]
    world=np.array(rig.matrix_world)
    return result@world[:3,:3].T+world[:3,3]
