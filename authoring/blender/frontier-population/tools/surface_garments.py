"""Continuous fitted garments from the retained anatomical quad surface.

The torso, axilla and sleeves share edges. Cut loops are planar and bound; cloth
allowance and relaxation remove skin-muscle contours without separating joints.
"""
import gzip
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]


def garments(family, race, make, morph, materials):
    source=json.loads(gzip.decompress((ROOT/'foundations'/f'{family}.quad-surface.json.gz').read_bytes()))
    points=[Vector(p) for p in source['vertices']]
    group_names=source['vertexGroups']
    bone_groups={'hips','spine','chest','upper_chest','neck','head','jaw','eye_L','eye_R'}
    bone_groups.update(name for name in group_names.values() if name.endswith(('_L','_R')))
    groups=[]
    retained_weights=[]
    for weights in source['weights']:
        influences=[(group_names[str(i)],w) for i,w in weights if group_names[str(i)] in bone_groups]
        groups.append(max(influences,key=lambda p:p[1])[0])
        retained_weights.append(sorted(influences,key=lambda p:-p[1])[:4])
    elbow={s:Vector((s*.375,-.0191,1.276)) for s in [-1,1]}
    direction={s:Vector((s*.141,-.2002,-.134)) for s in [-1,1]}
    cuff={s:elbow[s]+direction[s]*.52 for s in [-1,1]}
    hand=lambda name:any(part in name for part in ['index','middle','ring','pinky','thumb','hand'])
    arm=lambda name:hand(name) or 'arm' in name or 'shoulder' in name
    records=[]
    for kind in ['shirt','trousers']:
        selected=[]
        selected_uvs=[]
        for face_index,face in enumerate(source['faces']):
            center=sum((points[i] for i in face),Vector())/len(face)
            names=[groups[i] for i in face]
            if kind=='shirt':
                if not .955<center.z<1.58 or any(hand(n) for n in names):continue
                side=1 if center.x>0 else -1
                if abs(center.x)>.30 and (center-cuff[side]).dot(direction[side])>0:continue
            else:
                if not .215<center.z<1.025 or any(arm(n) for n in names):continue
            selected.append(face)
            selected_uvs.append(source['faceUvs'][face_index])
        used=sorted({i for face in selected for i in face}); remap={v:i for i,v in enumerate(used)}
        faces=[tuple(remap[i] for i in face) for face in selected]
        vertices=[points[i].copy() for i in used]
        neighbors=[set() for _ in vertices]; edges={}
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                neighbors[a].add(b);neighbors[b].add(a)
                edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
        boundary={v for edge,count in edges.items() if count==1 for v in edge}
        # Use the actual mesh adjacency to relax muscle contours into cloth.
        for _ in range(18):
            relaxed=[]
            for index,p in enumerate(vertices):
                if index in boundary:relaxed.append(p);continue
                mean=sum((vertices[i] for i in neighbors[index]),Vector())/len(neighbors[index])
                relaxed.append(p.lerp(mean,.38))
            vertices=relaxed
        normals=[Vector() for _ in vertices]
        for face in faces:
            normal=(vertices[face[1]]-vertices[face[0]]).cross(vertices[face[2]]-vertices[face[0]]).normalized()
            for i in face:normals[i]+=normal
        for i,p in enumerate(vertices):
            normal=normals[i].normalized()
            allowance=.028 if kind=='shirt' else .024
            if kind=='shirt' and abs(p.x)<.27:
                # Fabric falls from the chest toward the belted waist.
                angle=math.atan2(p.y,p.x)
                allowance+=.008*math.sin(angle*9+p.z*6)**2*max(0,min(1,(1.40-p.z)/.35))
            if kind=='trousers':
                knee=math.exp(-((p.z-.54)/.08)**2)
                allowance+=.0035*math.sin(p.z*110+p.x*13)*knee
            vertices[i]=p+normal*allowance
        for index in boundary:
            p=vertices[index]
            if kind=='shirt':
                if p.z<1.07:p.z=.955
                elif abs(p.x)<.19:p.z=1.58
                else:
                    side=1 if p.x>0 else -1; axis=direction[side].normalized()
                    p-=axis*(p-cuff[side]).dot(axis)
            elif p.z>.8:p.z=1.025
            else:p.z=.215
        # The garment retains the source surface's vertex identity. Transferring
        # its exact weights avoids nearest-point jumps across the axilla/collar.
        obj=make(kind+'_continuous_tailored_surface',[morph(p,race) for p in vertices],faces,
                 materials['cloth' if kind=='shirt' else 'trousers'],custom_weights=[retained_weights[i] for i in used])
        for polygon,uvs in zip(obj.data.polygons,selected_uvs):
            for loop,uv in zip(polygon.loop_indices,uvs):obj.data.uv_layers.active.data[loop].uv=Vector(uv)*4
        smooth=obj.modifiers.new('Continuous_cloth_finish','SUBSURF');smooth.levels=1;smooth.render_levels=1
        thick=obj.modifiers.new('Sewn_cloth_thickness','SOLIDIFY');thick.thickness=.004
        # Audit connected components and boundary loops before any export.
        unseen=set(range(len(vertices))); components=[]
        while unseen:
            queue=[unseen.pop()];component=set(queue)
            while queue:
                for v in neighbors[queue.pop()]:
                    if v in unseen:unseen.remove(v);component.add(v);queue.append(v)
            components.append(len(component))
        boundary_adjacency={v:set() for v in boundary}
        for (a,b),count in edges.items():
            if count==1:boundary_adjacency[a].add(b);boundary_adjacency[b].add(a)
        left=set(boundary);loops=[]
        while left:
            stack=[left.pop()];loop=[]
            while stack:
                v=stack.pop();loop.append(v)
                for n in boundary_adjacency[v]:
                    if n in left:left.remove(n);stack.append(n)
            loops.append(len(loop))
        if kind=='shirt':
            neck={i for i in boundary if vertices[i].z>1.5 and abs(vertices[i].x)<.19}
            start=min(neck);ordered=[start];previous=None;current=start
            while True:
                following=next((i for i in boundary_adjacency[current] if i!=previous),None)
                if following==start:break
                if following is None or following in ordered:raise RuntimeError('Collar boundary is not a loop')
                ordered.append(following);previous,current=current,following
            # Fill the shoulder cut toward the neck and turn a small standing
            # collar. The outer row shares the exact garment boundary positions.
            collar=[]
            for shrink,height in [(1,0),(.93,.003),(.58,.017),(.56,.038),(.58,.040)]:
                for i in ordered:
                    p=vertices[i].copy();p.x*=shrink;p.y*=shrink;p.z+=height
                    collar.append(morph(p,race))
            count=len(ordered)
            faces=[(r*count+c,r*count+(c+1)%count,(r+1)*count+(c+1)%count,(r+1)*count+c)
                   for r in range(4) for c in range(count)]
            collar_weights=[retained_weights[used[i]] for _ in range(5) for i in ordered]
            collar_obj=make('folded_standing_shirt_collar',collar,faces,materials['cloth'],custom_weights=collar_weights)
            sub=collar_obj.modifiers.new('Collar_fold_finish','SUBSURF');sub.levels=sub.render_levels=1
            solid=collar_obj.modifiers.new('Collar_fabric_thickness','SOLIDIFY');solid.thickness=.003
        record={'garment':kind,'vertices':len(vertices),'faces':len(faces),'connectedComponents':components,'boundaryLoops':loops,
                'boundaryValenceValid':all(len(n)==2 for n in boundary_adjacency.values())}
        records.append(record)
        if len(components)!=1 or len(loops)!=(4 if kind=='shirt' else 3) or not record['boundaryValenceValid']:
            raise RuntimeError('Continuous garment topology failed: '+json.dumps(record))
    (ROOT/'review'/f'{family}_{race}_garment_topology.json').write_text(json.dumps(records,indent=2))
