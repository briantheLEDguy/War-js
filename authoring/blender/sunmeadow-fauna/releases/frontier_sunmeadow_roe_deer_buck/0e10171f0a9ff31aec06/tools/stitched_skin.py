"""Connected quad shoulders/hips with explicit attachment loops and skin fields."""
import math
import bpy
import bmesh
from mathutils import Vector

def build_stitched_skin(cage,key,material,lod,definition,Cage,atlas,skin_fields):
    sides=[24,16,10][lod];width,height=[(4,8),(3,5),(2,3)][lod]
    body=cage.subset(lambda name:name=='continuous_rump_chest_neck_head');ring_count=len(body.vertices)//sides
    centers=[sum((Vector(v) for v in body.vertices[i*sides:(i+1)*sides]),Vector())/sides for i in range(ring_count)]
    holes=[]
    for limb in ['front_leg','hind_leg']:
        root=definition[limb][0];row=min(range(ring_count),key=lambda i:abs(centers[i].y-root[1]));first=max(1,min(ring_count-height-2,row-height//2))
        for side,label in [(1,'L'),(-1,'R')]:
            # The attachment emerges from the ventrolateral ribcage. An
            # equatorial opening folds inward into a false shoulder socket.
            left=round(sides*.79) if side>0 else round(sides*.5)-round(sides*.79)-width
            if limb=='hind_leg':left=-width//2 if side>0 else sides//2-width//2
            columns={(left+i)%sides for i in range(width)}
            loop=[first*sides+(left+j)%sides for j in range(width)]
            loop += [(first+i)*sides+(left+width)%sides for i in range(height)]
            loop += [(first+height)*sides+(left+j)%sides for j in range(width,0,-1)]
            loop += [(first+i)*sides+left%sides for i in range(height,0,-1)]
            if len(loop)!=sides:raise ValueError('Attachment perimeter must match the authored limb ring')
            holes.append({'name':limb+'_'+label,'first':first,'last':first+height,'columns':columns,'loop':loop,'side':side})
    keep=[];uv=[]
    for index,(face,coords) in enumerate(zip(body.faces,body.uv)):
        if len(face)==4:
            row=index//sides;column=index%sides
            if any(h['first']<=row<h['last'] and column in h['columns'] for h in holes):continue
        keep.append(face);uv.append(coords)
    result=Cage();result.add('continuous_anatomical_body',body.vertices,keep,uv,body.weights)
    for hole in holes:
        leg=cage.subset(lambda name:name==hole['name']);hind=hole['name'].startswith('hind_leg');entry=[4,3,2][lod]*(2 if hind else 3);cut=entry*sides
        # The upper limb emerges from a closed shoulder/haunch loop instead of
        # an intersecting cap. Two transition loops retain a rounded muscle mass.
        leg_faces=[];leg_uv=[]
        for face,coords in zip(leg.faces,leg.uv):
            if all(index>=cut for index in face):leg_faces.append([index-cut for index in face]);leg_uv.append(coords)
        offset=len(result.vertices);result.add(hole['name'],leg.vertices[cut:],leg_faces,leg_uv,leg.weights[cut:]);entry_indices=list(range(offset,offset+sides))
        boundary=hole['loop'];positions=[Vector(result.vertices[i]) for i in boundary]
        candidates=[]
        for reverse in [False,True]:
            for shift in range(sides):
                sequence=[entry_indices[(shift+(-i if reverse else i))%sides] for i in range(sides)]
                cost=sum((positions[i]-Vector(result.vertices[sequence[i]])).length_squared for i in range(sides));candidates.append((cost,sequence))
        entry_indices=min(candidates,key=lambda item:item[0])[1]
        rows=[boundary];first_new=len(result.vertices)
        for t in [.33,.67]:
            indices=[]
            for i,(a,b) in enumerate(zip(boundary,entry_indices)):
                p=Vector(result.vertices[a]).lerp(Vector(result.vertices[b]),t)
                p.x+=hole['side']*definition[hole['name'].rsplit('_',1)[0]][0][3]*(.85 if hind else .16)*math.sin(t*math.pi)
                indices.append(len(result.vertices));result.vertices.append(list(p));record={}
                blend=t*t*(3-2*t)
                for name,value in result.weights[a].items():record[name]=record.get(name,0)+value*(1-blend)
                for name,value in result.weights[b].items():record[name]=record.get(name,0)+value*blend
                result.weights.append(record)
            rows.append(indices)
        rows.append(entry_indices)
        for row in range(3):
            for j in range(sides):
                nxt=(j+1)%sides;result.faces.append([rows[row][j],rows[row][nxt],rows[row+1][nxt],rows[row+1][j]])
                result.uv.append([atlas(j/sides,row/3,0),atlas((j+1)/sides,row/3,0),atlas((j+1)/sides,(row+1)/3,0),atlas(j/sides,(row+1)/3,0)])
        result.parts.append({'name':hole['name']+'_attachment_loops','first_vertex':first_new,'vertices':sides*2,'faces':sides*3})
    # Remove unused interior body-grid vertices before refinement and binding.
    used=sorted({index for face in result.faces for index in face});mapping={old:new for new,old in enumerate(used)}
    result.vertices=[result.vertices[i] for i in used];result.weights=[result.weights[i] for i in used];result.faces=[[mapping[i] for i in face] for face in result.faces]
    result.parts=[{'name':'continuous_stitched_skin','first_vertex':0,'vertices':len(result.vertices),'faces':len(result.faces)}]
    obj=result.object(key+'_stitched_skin',material)
    edit=bmesh.new();edit.from_mesh(obj.data)
    open_edges=sum(not edge.is_manifold for edge in edit.edges)
    if open_edges:raise RuntimeError(f'Stitched skin has {open_edges} open/nonmanifold edges')
    bmesh.ops.recalc_face_normals(edit,faces=list(edit.faces));edit.to_mesh(obj.data);edit.free()
    names=sorted({name for record in result.weights for name in record});groups={name:obj.vertex_groups.new(name=name) for name in names}
    for index,record in enumerate(result.weights):
        for name,weight in record.items():groups[name].add([index],weight,'REPLACE')
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    if lod<2:
        subdivision=obj.modifiers.new('Anatomical_quad_refinement','SUBSURF');subdivision.levels=1;subdivision.subdivision_type='CATMULL_CLARK';bpy.ops.object.modifier_apply(modifier=subdivision.name)
    weights=skin_fields(obj.data.vertices,definition)
    while obj.vertex_groups:obj.vertex_groups.remove(obj.vertex_groups[0])
    extras=cage.subset(lambda name:name!='continuous_rump_chest_neck_head' and not name.startswith(('front_leg_','hind_leg_')));extra=extras.object(key+'_features',material)
    original_count=len(obj.data.vertices);weights.extend(extras.weights);bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);extra.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
    if len(obj.data.vertices)!=original_count+len(extras.vertices):raise RuntimeError('Refined skin/feature join changed vertex ordering')
    # Preserve the new quad cage, including its true connected shoulder loops.
    for part in extras.parts:
        first=part['first_vertex'];last=first+part['vertices'];faces=[];coords=[]
        for face,uv in zip(extras.faces,extras.uv):
            if first<=face[0]<last:faces.append([i-first for i in face]);coords.append(uv)
        result.add(part['name'],extras.vertices[first:last],faces,coords,extras.weights[first:last])
    return obj,weights,result
