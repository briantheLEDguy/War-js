"""Fitted scout jerkin, suspended field quiver, recurve bow and belt map case.

All meshes are authored surface panels, section lofts and swept construction
paths. Hardware is supported by visible straps; nothing is glued to bare skin.
"""
import math
import json
from pathlib import Path
import bpy
from mathutils import Vector
from surface_bindings import ClothSurface,bind_detail


def dress_scout(make,sweep,material,rig,materials,shape):
    shirt=bpy.data.objects['shirt_continuous_tailored_surface']
    lining=[m for m in shirt.modifiers if m.type=='SOLIDIFY']
    for modifier in lining:modifier.show_viewport=False
    bpy.context.view_layer.update();support=ClothSurface(shirt)
    for modifier in lining:modifier.show_viewport=True
    bpy.context.view_layer.update()
    suede=material('scout_forest_suede_jerkin',(.145,.205,.115),.84,textile=True)
    edge_mat=material('scout_jerkin_turned_binding',(.27,.29,.13),.86)
    strap_mat=material('scout_harness_leather',(.17,.09,.040),.73,textile=True)
    gear_mat=material('scout_tool_quiver_leather',(.22,.135,.067),.76,textile=True)
    bow_mat=material('scout_tool_bow_ash',(.38,.255,.12),.66,textile=True)
    thread_mat=material('scout_tool_fletching',(.36,.40,.28),.88,textile=True)
    metal=material('scout_tool_forged_caps',(.27,.29,.24),.42,.74)

    def field(surface,hit,triangle):
        weights=surface.weights(hit,triangle)
        return sorted(weights.items(),key=lambda row:-row[1])[:4]

    def ribbon(name,path,width,mat,offset=.008,shoulder=False):
        vertices=[];weights=[]
        def outer(point):
            # A nominal guide can be inside the chest allowance. Project from
            # outside, since nearest-surface fitting could select its lining.
            if shoulder:
                # A continuous radial direction follows the shoulder arc.
                # Switching abruptly between front/down/rear rays created a
                # jump in the fitted strip even when every point touched cloth.
                center=shape((0,-.015,1.43))
                direction=Vector((0,center.y-point.y,center.z-point.z)).normalized()
            else:
                direction=Vector((0,1,0)) if point.y<-.065 else Vector((0,-1,0)) if point.y>.035 else Vector((0,0,-1))
            hit,n,triangle,distance=support.tree.ray_cast(point-direction*2,direction)
            if hit is None:hit,n,triangle,distance=support.tree.find_nearest(point)
            return hit,n,triangle,distance
        for i,p in enumerate(path):
            p=Vector(p);tangent=(Vector(path[min(i+1,len(path)-1)])-Vector(path[max(0,i-1)])).normalized()
            hit,n,triangle,_=outer(p)
            cross=tangent.cross(n).normalized()
            for side in (-1,1):
                point=p+cross*width*.5*side;hit,n,triangle,_=outer(point)
                vertices.append(hit+n*offset);weights.append(field(support,hit,triangle))
        faces=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(path)-1)]
        obj=make(name,vertices,faces,mat,custom_weights=weights)
        thick=obj.modifiers.new('Turned_leather_thickness','SOLIDIFY');thick.thickness=.003;thick.offset=0
        return obj

    def dense(stations,steps=8):
        result=[]
        for a,b in zip(stations,stations[1:]):result.extend(Vector(a).lerp(Vector(b),i/steps) for i in range(steps))
        result.append(Vector(stations[-1]));return result

    # The jerkin is cut beneath the axilla with separate narrow shoulder yokes.
    # Each row follows the actual shirt, keeping one coherent allowance field.
    vertices=[];weights=[];count=128;rows=25
    for row in range(rows):
        t=row/(rows-1)
        for i in range(count):
            angle=i/count*math.tau;direction=Vector((math.sin(angle),math.cos(angle),0))
            top=1.452-.205*abs(math.sin(angle))**4;z=shape((0,0,1.044+(top-1.044)*t)).z
            hit,n,triangle,_=support.tree.ray_cast(Vector((0,0,z)),direction)
            if hit is None:raise RuntimeError('Jerkin must be supported by the continuous shirt')
            allowance=.015+.014*abs(math.sin(angle))**4
            vertices.append(hit+n*allowance);weights.append(field(support,hit,triangle))
    faces=[(r*count+i,r*count+(i+1)%count,(r+1)*count+(i+1)%count,(r+1)*count+i) for r in range(rows-1) for i in range(count)]
    jerkin=make('scout_fitted_jerkin',vertices,faces,suede,custom_weights=weights)
    thick=jerkin.modifiers.new('Turned_jerkin_thickness','SOLIDIFY');thick.thickness=.003;thick.offset=0
    jerkin_surface=ClothSurface(jerkin)
    for row in (0,rows-1):
        path=[vertices[row*count+i%count] for i in range(count+1)]
        obj=sweep('scout_jerkin_bound_opening',path,[.002]*len(path),edge_mat,'chest',6);bind_detail(obj,[jerkin_surface])
    for side in (-1,1):
        # Route over the shoulder outside the neck opening. The former inner
        # guide could catch the cut collar edge and kink up into a visible fin.
        # Both ends extend onto the jerkin panels; the shirt is only the
        # intermediate shoulder support. Terminal seams are bound below.
        stations=[shape(p) for p in [(side*.12,-.145,1.400),(side*.17,-.12,1.49),(side*.18,-.075,1.534),
                                    (side*.18,-.015,1.55),(side*.17,.04,1.515),(side*.108,.11,1.350)]]
        ribbon('scout_tapered_shoulder_yoke',dense(stations,steps=16),.033,suede,.016,shoulder=True)
    # Two long parallel seams emphasize a tailored panel, with restrained leaf
    # stitch marks fitted directly to its outer surface.
    for side in (-1,1):
        path=[]
        for i in range(41):
            t=i/40;z=shape((0,0,1.07+.355*t)).z;x=side*(.061+.013*math.sin(t*math.pi))
            hit,n,_,_=jerkin_surface.tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
            if hit is None:continue
            path.append(hit+n*.002)
        obj=sweep('scout_leaf_panel_piping',path,[.0015]*len(path),edge_mat,'chest',6);bind_detail(obj,[jerkin_surface])
        for i in range(3,len(path)-3,4):
            p=path[i];points=[p+Vector((side*.009,0,-.004)),p+Vector((0,-.0005,.001)),p+Vector((side*.008,0,.008))]
            obj=sweep('scout_leaf_stitch',points,[.00075]*3,edge_mat,'chest',5);bind_detail(obj,[jerkin_surface])

    # Quiver harness crosses the jerkin, turns over the left shoulder, and
    # returns along the back to its two sewn suspension loops.
    support=jerkin_surface
    front=dense([shape(p) for p in [(-.15,-.17,1.445),(-.07,-.185,1.35),(.045,-.18,1.21),(.115,-.165,1.07)]])
    ribbon('scout_front_quiver_harness',front,.034,strap_mat,.010)
    support=ClothSurface(shirt)
    shoulder=dense([shape(p) for p in [(-.15,-.17,1.445),(-.18,-.12,1.505),(-.185,-.05,1.551),(-.185,.015,1.533),(-.13,.064,1.48)]])
    ribbon('scout_over_shoulder_harness',shoulder,.034,strap_mat,.023,shoulder=True)
    support=jerkin_surface
    rear=dense([shape(p) for p in [(-.13,.09,1.445),(-.095,.12,1.34),(-.065,.14,1.225),(-.025,.13,1.09)]])
    ribbon('scout_rear_quiver_harness',rear,.035,strap_mat,.012)

    def loft(name,sections,mat,bone='chest',sides=16,open_top=False):
        verts=[]
        for z,cx,cy,rx,ry in sections:
            for i in range(sides):
                a=i*math.tau/sides;verts.append(Vector((cx+rx*math.cos(a),cy+ry*math.sin(a),z)))
        faces=[(r*sides+i,r*sides+(i+1)%sides,(r+1)*sides+(i+1)%sides,(r+1)*sides+i) for r in range(len(sections)-1) for i in range(sides)]
        faces.append(tuple(reversed(range(sides))))
        if not open_top:faces.append(tuple((len(sections)-1)*sides+i for i in range(sides)))
        obj=make(name,verts,faces,mat,bone)
        return obj

    # A narrowed base, bulged leather body and rolled opening form the quiver;
    # the inner rim visibly turns into a real cavity around its arrow shafts.
    quiver=[(1.19,-.025,.215,.035,.032),(1.21,-.027,.216,.049,.042),(1.28,-.032,.221,.049,.043),
            (1.52,-.059,.244,.057,.047),(1.64,-.069,.254,.06,.05),(1.665,-.071,.256,.062,.052),
            (1.676,-.072,.257,.057,.048),(1.659,-.071,.256,.051,.042),(1.55,-.060,.245,.050,.041),
            (1.221,-.027,.216,.041,.034)]
    loft('scout_suspended_quiver',quiver,gear_mat)
    for z,cx,cy,rx,ry in [quiver[1],quiver[4]]:
        points=[Vector((cx+(rx+.003)*math.cos(i*math.tau/65),cy+(ry+.003)*math.sin(i*math.tau/65),z)) for i in range(66)]
        sweep('scout_quiver_bound_seam',points,[.002]*len(points),strap_mat,'chest',6)
    for i in range(17):
        t=i/16;z=1.24+.35*t;cx=-.03-.033*t;cy=.219+.028*t
        points=[(cx+.044,cy+.024,z-.002),(cx+.047,cy+.025,z+.002)]
        sweep('scout_quiver_saddle_stitch',points,[.0008]*2,materials['seam'],'chest',5)
    for z,cx,cy in [(1.29,-.034,.223),(1.56,-.064,.249)]:
        # Suspension strap reaches the rear harness and encircles the quiver.
        path=[(cx-.025,.151,z-.009),(cx-.066,cy,z-.009),(cx,cy+.050,z-.009),(cx+.060,cy,z+.009),(cx+.025,.151,z+.009)]
        sweep('scout_quiver_retaining_loop',dense(path,4),[.008]*17,strap_mat,'chest',8)
    for index,(dx,dy,lift) in enumerate([(-.023,-.009,.0),(.0,.010,.043),(.026,-.005,.024),(.010,-.026,-.012)]):
        top=Vector((-.075+dx,.26+dy,1.828+lift));bottom=Vector((-.027+dx*.6,.216+dy*.6,1.225))
        sweep('scout_tool_arrow_shaft',[bottom,top],[.0031,.0027],bow_mat,'chest',8)
        for turn in range(3):
            angle=turn*math.tau/3;u=Vector((math.cos(angle),math.sin(angle),0))
            verts=[];rows=9
            for row in range(rows):
                t=row/(rows-1);center=top+Vector((0,0,-.020-.085*t));width=.017*math.sin(t*math.pi)**.65
                verts.extend([center+u*.003,center+u*(.003+width)+Vector((0,0,-.010*math.sin(t*math.pi)))])
            faces=[(r*2,r*2+1,r*2+3,r*2+2) for r in range(rows-1)]
            obj=make('scout_tool_cut_arrow_fletching',verts,faces,thread_mat,'chest')
            thick=obj.modifiers.new('Fletching_thickness','SOLIDIFY');thick.thickness=.001
        sweep('scout_arrow_nock',[top+Vector((0,0,.006)),top+Vector((0,0,-.008))],[.004,.003],metal,'chest',6)

    # Authored recurve stations form one narrow stave; its belly and back have
    # separate thickness. Two leather keepers secure it to the same harness.
    stations=[(-.18,.282,.74,.011,.005),(-.20,.267,.81,.013,.006),(-.17,.253,.97,.016,.007),
              (-.155,.247,1.16,.017,.010),(-.157,.247,1.27,.017,.010),(-.18,.256,1.46,.016,.007),
              (-.22,.281,1.64,.012,.005),(-.205,.30,1.71,.008,.004)]
    verts=[]
    for x,y,z,width,depth in stations:
        for px,py in [(-1,-.6),(-.6,-1),(.6,-1),(1,-.6),(1,.6),(.6,1),(-.6,1),(-1,.6)]:
            verts.append((x+px*width,y+py*depth,z))
    faces=[(r*8+i,r*8+(i+1)%8,(r+1)*8+(i+1)%8,(r+1)*8+i) for r in range(len(stations)-1) for i in range(8)]
    faces.extend([tuple(reversed(range(8))),tuple((len(stations)-1)*8+i for i in range(8))])
    bow=make('scout_carried_recurve_stave',verts,faces,bow_mat,'chest')
    sub=bow.modifiers.new('Recurve_surface_finish','SUBSURF');sub.levels=sub.render_levels=2
    sweep('scout_tool_bowstring',[(-.18,.292,.748),(-.205,.310,1.705)],[.0013,.0013],materials['seam'],'chest',6)
    for x,y,z in [(-.18,.283,.748),(-.205,.301,1.704)]:
        path=[(x+.009*math.sin(i*math.tau/30),y+.009*math.cos(i*math.tau/30),z) for i in range(31)]
        sweep('scout_bow_nock_binding',path,[.0017]*len(path),strap_mat,'chest',6)
    for i in range(12):
        z=1.17+i*.006
        path=[(-.157+.019*math.cos(j*math.tau/20),.247+.012*math.sin(j*math.tau/20),z+j/20*.006) for j in range(21)]
        sweep('scout_bow_grip_wrap',path,[.0017]*len(path),strap_mat,'chest',6)
    for z in (1.08,1.40):
        path=[(-.06,.201,z),(-.14,.239,z+.014),(-.203,.266,z),(-.16,.267,z-.014),(-.065,.228,z-.011)]
        sweep('scout_bow_keeper',dense(path,4),[.006]*17,strap_mat,'chest',8)

    # Short map case hangs high on the rear-right belt, above the flexing thigh.
    loft('scout_tool_belt_map_case',[(1.065,.134,.133,.048,.032),(1.073,.134,.136,.053,.036),(1.158,.133,.137,.051,.035),(1.172,.131,.135,.047,.032)],gear_mat,'hips',16)
    for x in (.107,.157):
        points=[(x,.077,1.095),(x,.090,1.183),(x,.151,1.19),(x,.176,1.165),(x,.172,1.132)]
        sweep('scout_map_case_belt_loop',dense(points,4),[.006]*17,strap_mat,'hips',8)
    sweep('scout_map_case_toggle',[(.110,.176,1.14),(.155,.176,1.14)],[.004,.004],bow_mat,'hips',8)

    # Retain room for cloth movement while bringing the rigid back assembly
    # onto its visible harness. The inspection gate checks this real clearance.
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or not obj.name.startswith(('scout_suspended_quiver','scout_quiver_',
                'scout_tool_arrow_','scout_tool_cut_arrow_','scout_arrow_nock','scout_carried_recurve_',
                'scout_tool_bowstring','scout_bow_')):continue
        for vertex in obj.data.vertices:vertex.co.y-=.070
    # The recurve hangs above the hip fold. Its complete stave, string, wraps
    # and nocks move together; the two leather keepers are subsequently fitted
    # to both this real surface and the quiver's suspension points.
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or not obj.name.startswith(('scout_carried_recurve_','scout_tool_bowstring',
                'scout_bow_nock_binding','scout_bow_grip_wrap')):continue
        for vertex in obj.data.vertices:vertex.co.z+=.20
    # Suspension roots must touch the exterior harness; the closed retaining
    # portion keeps its original relation to the quiver and bow.
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or not obj.name.startswith('scout_quiver_retaining_loop'):continue
        for vertex in obj.data.vertices:
            if vertex.co.y>.095:continue
            hit,n,_,_=support.tree.ray_cast(Vector((vertex.co.x,2,vertex.co.z)),Vector((0,-1,0)))
            if hit is not None:vertex.co.y=max(vertex.co.y,hit.y+.006)

    # Retaining hardware is cut leather, not a round cord. Preserve the broad
    # strap width while fitting a 3–4 mm section normal to each carrying path.
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or not obj.name.startswith(('scout_quiver_retaining_loop','scout_bow_keeper','scout_map_case_belt_loop')):continue
        rows=len(obj.data.vertices)//8
        centers=[sum((obj.data.vertices[r*8+i].co for i in range(8)),Vector())/8 for r in range(rows)]
        width_axis=Vector((1,0,0)) if obj.name.startswith('scout_map_case') else Vector((0,0,1))
        for r,center in enumerate(centers):
            tangent=(centers[min(r+1,rows-1)]-centers[max(0,r-1)]).normalized()
            across=(width_axis-tangent*width_axis.dot(tangent)).normalized();normal=tangent.cross(across).normalized()
            for i in range(8):
                vertex=obj.data.vertices[r*8+i];offset=vertex.co-center
                vertex.co=center+across*offset.dot(across)+normal*offset.dot(normal)*.22
        obj.data.update()

    # Close actual semantic attachment chains after the equipment is positioned.
    # End fields inherit the supporting cloth/belt; the rest remains on the
    # carried item's bone so a shoulder gesture cannot detach its hanger.
    links=[]
    def attach(part,ring,sides,target,label,match_edge=False):
        obj=bpy.data.objects[part];host=bpy.data.objects[target]
        surface=ClothSurface(host)
        rows=len(obj.data.vertices)//sides
        row=ring if ring>=0 else rows+ring
        indices=list(range(row*sides,(row+1)*sides))
        center=sum((obj.data.vertices[i].co for i in indices),Vector())/len(indices)
        hit,normal,triangle,_=surface.tree.find_nearest(center)
        delta=hit+normal*.001-center
        endpoint=ring in (0,-1)
        extent=4 if sides==8 else 10
        field=surface.weights(hit,triangle)
        edge_fields=[]
        if match_edge:
            # Fit both corners independently; a center contact does not sew
            # the full width of a bridge onto a sloping panel boundary.
            for i in indices:
                point=obj.data.vertices[i].co
                edge_hit,edge_normal,edge_triangle,_=surface.tree.find_nearest(point)
                edge_fields.append((edge_hit+edge_normal*.001-point,surface.weights(edge_hit,edge_triangle)))
        for r in range(max(0,row-extent),min(rows,row+extent+1)):
            t=max(0,1-abs(r-row)/extent);t=t*t*(3-2*t)
            for i in range(r*sides,(r+1)*sides):
                displacement,host_field=edge_fields[i%sides] if match_edge else (delta,field)
                vertex=obj.data.vertices[i];vertex.co+=displacement*t
                if not endpoint:continue
                weights={obj.vertex_groups[g.group].name:g.weight*(1-t) for g in vertex.groups}
                for name,weight in host_field.items():weights[name]=weights.get(name,0)+weight*t
                for group in obj.vertex_groups:group.remove([i])
                values=sorted(weights.items(),key=lambda v:-v[1])[:4];total=sum(w for _,w in values)
                for name,weight in values:
                    group=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
                    group.add([i],weight/total,'REPLACE')
        obj.data.update();bpy.context.view_layer.update()
        links.append({'id':label,'subject':part,'support':target,'seed':list(hit)})

    for obj in sorted((o for o in bpy.context.scene.objects if o.name.startswith('scout_tapered_shoulder_yoke')),key=lambda o:o.name):
        for ring,end in ((0,'front'),(-1,'rear')):
            label=obj.name+'_'+end+'_jerkin_seam'
            attach(obj.name,ring,2,'scout_fitted_jerkin',label,match_edge=True)
            surface=ClothSurface(jerkin);row=0 if ring==0 else len(obj.data.vertices)//2-1
            for edge in range(2):
                hit,_,_,_=surface.tree.find_nearest(obj.data.vertices[row*2+edge].co)
                links.append({'id':label+'_edge_'+str(edge),'subject':obj.name,'support':jerkin.name,'seed':list(hit)})
    attach('scout_front_quiver_harness',0,2,'scout_over_shoulder_harness','front_harness_to_shoulder')
    attach('scout_front_quiver_harness',-1,2,'work_belt','front_harness_to_belt')
    attach('scout_rear_quiver_harness',0,2,'scout_over_shoulder_harness','rear_harness_to_shoulder')
    attach('scout_rear_quiver_harness',-1,2,'work_belt','rear_harness_to_belt')
    for obj in sorted((o for o in bpy.context.scene.objects if o.name.startswith('scout_quiver_retaining_loop')),key=lambda o:o.name):
        attach(obj.name,0,8,'scout_rear_quiver_harness',obj.name+'_left_harness_root')
        attach(obj.name,-1,8,'scout_rear_quiver_harness',obj.name+'_right_harness_root')
        attach(obj.name,8,8,'scout_suspended_quiver',obj.name+'_quiver_contact')
    for obj in sorted((o for o in bpy.context.scene.objects if o.name.startswith('scout_bow_keeper') and 'nock' not in o.name),key=lambda o:o.name):
        attach(obj.name,0,8,'scout_suspended_quiver',obj.name+'_quiver_root')
        attach(obj.name,-1,8,'scout_suspended_quiver',obj.name+'_quiver_return')
        attach(obj.name,8,8,'scout_carried_recurve_stave',obj.name+'_bow_contact')
    for obj in sorted((o for o in bpy.context.scene.objects if o.name.startswith('scout_map_case_belt_loop')),key=lambda o:o.name):
        attach(obj.name,0,8,'work_belt',obj.name+'_belt_root')
        attach(obj.name,-1,8,'scout_tool_belt_map_case',obj.name+'_case_root')
    # Capture literal finished surfaces near each semantic anchor. The reimport
    # gate must find both parts in every real LOD and follow their actual skinned
    # triangles across all clips; these coordinates are not invisible supports.
    for link in links:
        parts={}
        for role in ('subject','support'):
            obj=bpy.data.objects[link[role]];surface=ClothSurface(obj)
            hit,normal,triangle,distance=surface.tree.find_nearest(Vector(link['seed']))
            if distance>.010:raise RuntimeError('Unattached source anchor: '+link['id']+'/'+role+' '+str(distance))
            parts[role]={'object':obj.name,'materials':[m.name for m in obj.data.materials],
                         'point':list(hit),'bounds':{'min':[min(p[i] for p in surface.points) for i in range(3)],
                                                  'max':[max(p[i] for p in surface.points) for i in range(3)]}}
        link.update(parts);link['maximumGap']=.010
    work=Path(__file__).resolve().parents[1]
    (work/'review/equipment-attachment-source.json').write_text(json.dumps({'schemaVersion':1,'status':'source_measured','links':links},indent=2)+'\n')
