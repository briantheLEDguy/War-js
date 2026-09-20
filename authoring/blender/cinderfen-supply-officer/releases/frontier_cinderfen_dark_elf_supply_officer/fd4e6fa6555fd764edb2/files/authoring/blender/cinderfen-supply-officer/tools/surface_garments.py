"""Continuous fitted garments from the retained anatomical quad surface.

The torso, axilla and sleeves share edges. Cut loops are planar and bound; cloth
allowance and relaxation remove skin-muscle contours without separating joints.
"""
import gzip
import json
import math
import bpy
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]


def garments(family, race, make, morph, materials):
    source=json.loads(gzip.decompress((ROOT.parent/'frontier-population/foundations'/f'{family}.quad-surface.json.gz').read_bytes()))
    points=[Vector((p[0]/1.098,p[1]/1.12,p[2]/1.11)) if race=='greenskin' else Vector((p[0]*1.12,p[1]*1.1,p[2]*(1.86/1.76))) if race=='dark_elf' else Vector(p) for p in source['vertices']]
    group_names=source['vertexGroups']
    bone_groups={'hips','spine','chest','upper_chest','neck','head','jaw','eye_L','eye_R'}
    bone_groups.update(name for name in group_names.values() if name.endswith(('_L','_R')))
    groups=[]
    retained_weights=[]
    for weights in source['weights']:
        influences=[(group_names[str(i)],w) for i,w in weights if group_names[str(i)] in bone_groups]
        groups.append(max(influences,key=lambda p:p[1])[0])
        retained_weights.append(sorted(influences,key=lambda p:-p[1])[:4])
    elbow={s:Vector((s*.3413039148*1.12,-.0222115982*1.1,1.202018261*(1.86/1.76))) for s in [-1,1]}
    direction={s:Vector((s*(.4636598527-.3413039148)*1.12,(-.1777928025+.0222115982)*1.1,(1.072563529-1.202018261)*(1.86/1.76))) for s in [-1,1]}
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
        fields=[dict(retained_weights[i]) for i in used]
        neighbors=[set() for _ in vertices]; edges={}
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                neighbors[a].add(b);neighbors[b].add(a)
                edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
        boundary={v for edge,count in edges.items() if count==1 for v in edge}
        # Use the actual mesh adjacency to relax muscle contours into cloth.
        for _ in range(18):
            relaxed=[]
            relaxed_fields=[]
            for index,p in enumerate(vertices):
                if index in boundary:relaxed.append(p);relaxed_fields.append(fields[index]);continue
                mean=sum((vertices[i] for i in neighbors[index]),Vector())/len(neighbors[index])
                relaxed.append(p.lerp(mean,.38))
                field={name:weight*.62 for name,weight in fields[index].items()}
                for adjacent in neighbors[index]:
                    for name,weight in fields[adjacent].items():field[name]=field.get(name,0)+weight*.38/len(neighbors[index])
                relaxed_fields.append(field)
            vertices=relaxed;fields=relaxed_fields
        normals=[Vector() for _ in vertices]
        for face in faces:
            normal=(vertices[face[1]]-vertices[face[0]]).cross(vertices[face[2]]-vertices[face[0]]).normalized()
            for i in face:normals[i]+=normal
        for i,p in enumerate(vertices):
            normal=normals[i].normalized()
            allowance=.028 if kind=='shirt' else .024
            if kind=='shirt' and p.z<1.12 and abs(p.x)<.30:
                tuck=max(0,min(1,(1.12-p.z)/.165));tuck=tuck*tuck*(3-2*tuck)
                allowance+=.022*tuck
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
        if race in ('dwarf','greenskin','dark_elf') and kind=='trousers':
            # The wool is tucked inside the authored boot mouth. Give that
            # hidden hem the same ankle field as the cuff, then ease into the
            # original calf so ankle pitch cannot expose a serrated overlap.
            for index,p in enumerate(vertices):
                blend=max(0,min(1,(.47-p.z)/.13));blend=blend*blend*(3-2*blend)
                if not blend:continue
                side=1 if p.x>0 else -1
                dx=p.x-side*.20855;dy=p.y+.008
                radius=math.sqrt((dx/.050)**2+(dy/.042)**2)
                if radius>1:
                    p.x=side*.20855+dx*(1-blend+blend/radius)
                    p.y=-.008+dy*(1-blend+blend/radius)
                field={name:weight*(1-blend) for name,weight in fields[index].items()}
                bone_side='L' if side>0 else 'R'
                ankle=max(0,min(1,(morph((0,0,p.z),race).z-morph((0,0,.12),race).z)/(morph((0,0,.27),race).z-morph((0,0,.12),race).z)))
                ankle=ankle*ankle*(3-2*ankle)
                for name,weight in [('shin_'+bone_side,ankle),('foot_'+bone_side,1-ankle)]:field[name]=field.get(name,0)+weight*blend
                fields[index]=field
        # The garment retains the source surface's vertex identity. Transferring
        # its exact weights avoids nearest-point jumps across the axilla/collar.
        obj=make(kind+'_continuous_tailored_surface',[morph(p,race) for p in vertices],faces,
                 materials['cloth' if kind=='shirt' else 'trousers'],custom_weights=[sorted(field.items(),key=lambda p:-p[1])[:4] for field in fields])
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
            # Share the outer collar row with the shirt neckline. Separate
            # subdivision cages shrink away from each other and leave an open
            # shoulder seam even when the control vertices initially coincide.
            old=obj.data;old_uv=[[tuple(old.uv_layers.active.data[i].uv) for i in f.loop_indices] for f in old.polygons]
            old_faces=[tuple(f.vertices) for f in old.polygons];base=len(old.vertices)
            index=lambda r,c:ordered[c] if r==0 else base+(r-1)*count+c
            joined_faces=old_faces+[(index(r,c),index(r,(c+1)%count),index(r+1,(c+1)%count),index(r+1,c)) for r in range(4) for c in range(count)]
            mesh=bpy.data.meshes.new('continuous_shirt_and_turned_collar')
            mesh.from_pydata([v.co[:] for v in old.vertices]+collar[count:],[],joined_faces);mesh.update();mesh.materials.append(materials['cloth'])
            uv=mesh.uv_layers.new(name='UVMap')
            for face,values in zip(mesh.polygons,old_uv):
                for loop,value in zip(face.loop_indices,values):uv.data[loop].uv=value
            for face in list(mesh.polygons)[len(old_faces):]:
                for loop in face.loop_indices:
                    p=mesh.vertices[mesh.loops[loop].vertex_index].co;uv.data[loop].uv=(p.x*4,p.y*4)
            obj.data=mesh
            final_weights=[sorted(field.items(),key=lambda p:-p[1])[:4] for field in fields]+collar_weights[count:]
            for i,values in enumerate(final_weights):
                total=sum(w for _,w in values)
                for name,w in values:
                    group=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name);group.add([i],w/total,'REPLACE')
            for face in mesh.polygons:face.use_smooth=True
        record={'garment':kind,'vertices':len(vertices),'faces':len(faces),'connectedComponents':components,'boundaryLoops':loops,
                'boundaryValenceValid':all(len(n)==2 for n in boundary_adjacency.values())}
        records.append(record)
        if len(components)!=1 or len(loops)!=(4 if kind=='shirt' else 3) or not record['boundaryValenceValid']:
            raise RuntimeError('Continuous garment topology failed: '+json.dumps(record))
    (ROOT/'review'/f'{family}_{race}_garment_topology.json').write_text(json.dumps(records,indent=2))
