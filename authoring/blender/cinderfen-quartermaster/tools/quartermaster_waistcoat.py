"""Cut a sleeveless, open-neck supply waistcoat from the actual fitted shirt."""
import math,json
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from surface_bindings import ClothSurface,bind_detail


def make_waistcoat(make,sweep,material,mats):
    shirt=bpy.data.objects['shirt_continuous_tailored_surface']
    shirt.data.update()
    # Pattern the finished shirt surface, including its evaluated skin fields.
    # Subdividing a second cage changes the skin interpolation around the neck
    # and axilla even when the two neutral surfaces fit exactly.
    muted=[mod for mod in shirt.modifiers if mod.type in ('SOLIDIFY','ARMATURE') and mod.show_viewport]
    for mod in muted:mod.show_viewport=False
    bpy.context.view_layer.update()
    evaluated=shirt.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    points=[v.co.copy() for v in mesh.vertices]
    normals=[v.normal.copy() for v in mesh.vertices]
    fields=[]
    for v in mesh.vertices:
        field=sorted([(shirt.vertex_groups[g.group].name,g.weight) for g in v.groups],key=lambda row:-row[1])[:4]
        total=sum(weight for _,weight in field)
        fields.append([(name,weight/total) for name,weight in field])
    pattern_faces=[tuple(face.vertices) for face in mesh.polygons]
    pattern_uvs=[[tuple(mesh.uv_layers.active.data[i].uv) for i in face.loop_indices] for face in mesh.polygons]
    evaluated.to_mesh_clear();surface=ClothSurface(shirt)
    for mod in muted:mod.show_viewport=True
    bpy.context.view_layer.update()
    trousers=ClothSurface(bpy.data.objects['trousers_continuous_tailored_surface'])
    faces=[];uvs=[]
    for face,uv in zip(pattern_faces,pattern_uvs):
        center=sum((points[i] for i in face),Vector())/len(face)
        arm=sum(w for i in face for name,w in fields[i] if 'arm' in name)/len(face)
        shoulder_bridge=center.z>1.665 and abs(center.x)<.295
        if center.z<1.083 or (arm>.36 and not shoulder_bridge):continue
        # Preserve the load-bearing shoulder bridges while opening the actual
        # neck collar. A horizontal crop would leave unsupported front tongues.
        if center.z>1.74 and math.hypot(center.x,center.y*1.2)<.175:continue
        armhole=1-((center.z-1.535)/.13)**2
        if armhole>0 and abs(center.x)>.16 and abs(center.y+.025)<.12*math.sqrt(armhole):continue
        # A deep V opening and low front points make this a sleeveless merchant
        # garment rather than another work bib. The back and shoulders connect.
        if center.y<-.045 and center.z>1.41 and abs(center.x)<.024+(center.z-1.41)*.30:continue
        faces.append(face)
        uvs.append(uv)
    # Intersecting pattern cuts can leave isolated single-quad offcuts. Trim
    # those scraps instead of exporting a closed but visibly floating island.
    adjacency={}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
    pending=set(adjacency);components=[]
    while pending:
        todo=[pending.pop()];component=set(todo)
        while todo:
            for adjacent in adjacency[todo.pop()]:
                if adjacent in pending:pending.remove(adjacent);component.add(adjacent);todo.append(adjacent)
        components.append(component)
    retained=max(components,key=len)
    if any(len(component)>8 for component in components if component is not retained):
        raise RuntimeError('Waistcoat pattern has a disconnected structural panel')
    selected=[(face,uv) for face,uv in zip(faces,uvs) if face[0] in retained]
    faces=[face for face,_ in selected];uvs=[uv for _,uv in selected]
    used=sorted(retained);remap={i:n for n,i in enumerate(used)}
    # The anatomical quad rows are not sewing patterns. Relax the actual cut
    # loops on the fitted shirt, then project them back to its outer surface;
    # face-selection stair steps must never become the visible neckline.
    edge_counts={};neighbors={i:set() for i in used}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            edge=tuple(sorted((a,b)));edge_counts[edge]=edge_counts.get(edge,0)+1
            neighbors[a].add(b);neighbors[b].add(a)
    boundary={}
    for (a,b),count in edge_counts.items():
        if count==1:boundary.setdefault(a,set()).add(b);boundary.setdefault(b,set()).add(a)
    if any(len(adjacent)!=2 for adjacent in boundary.values()):
        raise RuntimeError('Waistcoat pattern cut is not a set of continuous loops')
    for _ in range(28):
        relaxed={};relaxed_fields={}
        for i,adjacent in boundary.items():
            p=points[i].lerp(sum((points[j] for j in adjacent),Vector())/2,.48)
            hit,normal,triangle,_=surface.tree.find_nearest(p)
            relaxed[i]=hit
            normals[i]=normal
            field=surface.weights(hit,triangle)
            relaxed_fields[i]=sorted(field.items(),key=lambda row:-row[1])[:4]
        for i,p in relaxed.items():points[i]=p
        for i,field in relaxed_fields.items():
            total=sum(weight for _,weight in field);fields[i]=[(name,weight/total) for name,weight in field]
    for _ in range(4):
        relaxed={}
        for i in used:
            if i in boundary or not any(j in boundary for j in neighbors[i]):continue
            p=points[i].lerp(sum((points[j] for j in neighbors[i]),Vector())/len(neighbors[i]),.28)
            hit,normal,triangle,_=surface.tree.find_nearest(p)
            relaxed[i]=hit;normals[i]=normal
            field=sorted(surface.weights(hit,triangle).items(),key=lambda row:-row[1])[:4]
            total=sum(weight for _,weight in field);fields[i]=[(name,weight/total) for name,weight in field]
        for i,p in relaxed.items():points[i]=p
    vertices=[];weights=[]
    for i in used:
        # Interior vertices remain exact counterparts of the finished shirt;
        # only the cut loops move on its surface. Do not reproject the interior
        # across the opposing face of a narrow collar or axilla fold.
        point=points[i]+normals[i]*.019;field=dict(fields[i])
        if point.z<1.22:
            direction=Vector((point.x,point.y,0)).normalized();origin=Vector((0,0,point.z))
            outer=0;outer_field=field
            for support in (surface,trousers):
                # Span the actual trouser waistband edge: a radial ray just
                # above its cut otherwise misses the hull, and the next vest
                # triangle slices through the lip between two clear vertices.
                for dz in (-.04,0,.04):
                    probe=origin+Vector((0,0,dz));cursor=probe.copy()
                    for _ in range(12):
                        contact,_,index,_=support.tree.ray_cast(cursor,direction,.8)
                        if contact is None:break
                        distance=math.hypot(contact.x,contact.y)
                        if distance>outer:outer=distance;outer_field=support.weights(contact,index)
                        cursor=contact+direction*.0005
            if (point-origin).length<outer+.020:
                point=origin+direction*(outer+.020);field=outer_field
        vertices.append(point)
        weights.append(list(field.items()))
    mat=material('quartermaster_supply_waistcoat',(.095,.067,.072),.75,textile=True)
    obj=make('quartermaster_waistcoat',vertices,[tuple(remap[i] for i in face) for face in faces],mat,custom_weights=weights)
    for face,values in zip(obj.data.polygons,uvs):
        for loop,value in zip(face.loop_indices,values):obj.data.uv_layers.active.data[loop].uv=value
    solid=obj.modifiers.new('Turned_four_mm_leather','SOLIDIFY');solid.thickness=.004
    return obj


def finish_waistcoat(obj,make,sweep,mats):
    support=ClothSurface(obj)
    def front(x,z,depth=.004):
        hit,normal,triangle,_=support.tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
        if hit is None:raise RuntimeError('Waistcoat detail has no supporting panel')
        return hit+Vector((0,-depth,0))
    # Two bellows pockets with turned lips and closed edge thickness carry
    # folded requisitions. Their seam fields follow the supporting waistcoat.
    for side in (-1,1):
        center=side*.121;cols=9;rows=7;vertices=[]
        for row in range(rows):
            t=row/(rows-1);z=1.38-.135*t
            for col in range(cols):
                u=col/(cols-1);x=center+(u-.5)*.112
                vertices.append(front(x,z,.006+.018*math.sin(math.pi*u)*math.sin(math.pi*t)))
        faces=[(r*cols+c,r*cols+c+1,(r+1)*cols+c+1,(r+1)*cols+c) for r in range(rows-1) for c in range(cols-1)]
        pocket=make('quartermaster_bellows_pocket_'+str(side),vertices,faces,obj.data.materials[0]);bind_detail(pocket,[support])
        sub=pocket.modifiers.new('Soft_formed_pocket','SUBSURF');sub.levels=sub.render_levels=1
        solid=pocket.modifiers.new('Pocket_turned_thickness','SOLIDIFY');solid.thickness=.003
        lip=sweep('quartermaster_pocket_turned_lip',vertices[:cols],[.0022]*cols,mats['leather']);bind_detail(lip,[support])
        edge=[vertices[r*cols] for r in range(rows)]+vertices[-cols:]+[vertices[r*cols+cols-1] for r in reversed(range(rows))]
        for a,b in zip(edge,edge[1:]):
            count=max(1,int((b-a).length/.007))
            for i in range(count):
                p=a.lerp(b,i/count)+Vector((0,-.0015,0));q=a.lerp(b,(i+.5)/count)+Vector((0,-.0015,0))
                stitch=sweep('quartermaster_pocket_lockstitch',[p,q],[.0007,.0007],mats['seam'],sides=5);bind_detail(stitch,[support])
    # Original broad brass hook clasps are fitted to the leather surface.
    for z in (1.185,1.255,1.325,1.395):
        for side in (-1,1):
            p=front(side*.019,z)
            outline=[(-.012,-.006),(-.015,0),(-.009,.007),(.010,.006),(.014,0),(.009,-.007)]
            vertices=[p+Vector((x,depth,h)) for depth in (0,-.003) for x,h in outline]
            faces=[(i,(i+1)%6,6+(i+1)%6,6+i) for i in range(6)]+[tuple(reversed(range(6))),tuple(range(6,12))]
            clasp=make('quartermaster_fitted_brass_clasp',vertices,faces,mats['brass']);bind_detail(clasp,[support])


def check_source_layer(work):
    """Fail early on source construction; actual-export gates still run later."""
    def geometry(objects):
        points=[];faces=[];names=[]
        for obj in objects:
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
            mesh.calc_loop_triangles();base=len(points)
            points.extend(obj.matrix_world@vertex.co for vertex in mesh.vertices)
            faces.extend(tuple(base+i for i in triangle.vertices) for triangle in mesh.loop_triangles)
            names.extend(obj.name for triangle in mesh.loop_triangles)
            evaluated.to_mesh_clear()
        return points,faces,names
    outer=[obj for obj in bpy.context.scene.objects if obj.type=='MESH' and any(mat and mat.name=='quartermaster_supply_waistcoat' for mat in obj.data.materials)]
    inner=[obj for obj in bpy.context.scene.objects if obj.type=='MESH' and any(mat and any(term in mat.name for term in ('_woven_linen','_wool','body_mire_brutish_v1_m.body')) for mat in obj.data.materials)]
    points,faces,_=geometry(outer);targets,target_faces,target_names=geometry(inner)
    tree=BVHTree.FromPolygons(targets,target_faces,all_triangles=True)
    edges={tuple(sorted((a,b))) for face in faces for a,b in zip(face,face[1:]+face[:1])};crossings=[]
    for a,b in edges:
        delta=points[b]-points[a]
        if delta.length<.001:continue
        direction=delta.normalized();hit,_,target,_=tree.ray_cast(points[a]+direction*.00025,direction,delta.length-.0005)
        if hit is not None:crossings.append({'point':list(hit),'target':target_names[target]})
    report={'method':'Evaluated neutral source triangles, before animation fitting; export audits remain mandatory','outerTriangles':len(faces),'innerTriangles':len(target_faces),'crossings':len(crossings),'points':crossings}
    (Path(work)/'review/source-layer-preflight.json').write_text(json.dumps(report,separators=(',',':')))
    print('Source layer preflight: '+str(len(crossings))+' crossings',flush=True)
    if crossings:raise RuntimeError('Source waistcoat construction still crosses underlying garment/anatomy')
