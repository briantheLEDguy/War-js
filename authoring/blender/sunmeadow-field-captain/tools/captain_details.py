"""Original fitted field brigandine, articulated shoulder and dispatch equipment.

Surface panels and swept construction paths are fitted to the measured uniform;
semantic attachment contacts are retained for independent actual-GLB inspection.
"""
import json,math
from pathlib import Path
import bpy
from mathutils import Vector
from surface_bindings import ClothSurface,bind_detail


def dress_captain(make,sweep,material,rig,materials):
    shirt=bpy.data.objects['shirt_continuous_tailored_surface']
    lining=[m for m in shirt.modifiers if m.type=='SOLIDIFY']
    for modifier in lining:modifier.show_viewport=False
    bpy.context.view_layer.update();shirt_surface=ClothSurface(shirt)
    for modifier in lining:modifier.show_viewport=True
    bpy.context.view_layer.update()
    brigandine=material('captain_layer_leather_brigandine',(.235,.100,.051),.78,textile=True)
    felt=material('captain_layer_shoulder_felt',(.075,.091,.115),.94,textile=True)
    steel=material('captain_layer_tempered_steel',(.17,.19,.21),.44,.82)
    gear=material('captain_tool_dispatch_leather',(.115,.062,.033),.76,textile=True)
    binding=material('captain_turned_binding',(.11,.054,.028),.8)
    gold=materials['brass'];thread=materials['seam'];leather=materials['leather']
    links=[]
    def field(surface,p,triangle):return sorted(surface.weights(p,triangle).items(),key=lambda row:-row[1])[:4]
    def panel(name,vertices,faces,mat,support,thickness):
        weights=[]
        for p in vertices:
            hit,_,triangle,_=support.tree.find_nearest(Vector(p));weights.append(field(support,hit,triangle))
        obj=make(name,vertices,faces,mat,custom_weights=weights)
        solid=obj.modifiers.new('Finished_panel_thickness','SOLIDIFY');solid.thickness=thickness;solid.offset=0
        return obj
    # The fitted body is cut clear of the moving axilla. Wider shoulder bridges
    # are part of the same uniform and terminate on full-width sewn panel seams.
    count=128;rows=25;vertices=[];weights=[]
    for row in range(rows):
        t=row/(rows-1)
        for i in range(count):
            angle=i/count*math.tau;top=1.495-.265*abs(math.sin(angle))**4
            z=1.056+(top-1.056)*t;direction=Vector((math.sin(angle),math.cos(angle),0))
            hit,n,triangle,_=shirt_surface.tree.ray_cast(Vector((0,0,z)),direction)
            if hit is None:raise RuntimeError('Brigandine lacks its measured shirt support')
            vertices.append(hit+n*(.016+.012*abs(math.sin(angle))**4));weights.append(field(shirt_surface,hit,triangle))
    faces=[(r*count+i,r*count+(i+1)%count,(r+1)*count+(i+1)%count,(r+1)*count+i) for r in range(rows-1) for i in range(count)]
    torso=make('captain_fitted_brigandine',vertices,faces,brigandine,custom_weights=weights)
    solid=torso.modifiers.new('Bound_brigandine_thickness','SOLIDIFY');solid.thickness=.004;solid.offset=0
    torso_surface=ClothSurface(torso)
    for row in (0,rows-1):
        path=[vertices[row*count+i%count] for i in range(count+1)]
        edge=sweep('captain_turned_brigandine_edge',path,[.0022]*len(path),binding,'chest',6);bind_detail(edge,[torso_surface])
    def densify(stations,steps=16):
        points=[]
        for a,b in zip(stations,stations[1:]):points.extend(Vector(a).lerp(Vector(b),i/steps) for i in range(steps))
        return points+[Vector(stations[-1])]
    for side in (-1,1):
        path=densify([(side*.125,-.16,1.395),(side*.17,-.12,1.49),(side*.18,-.07,1.535),
                      (side*.18,-.012,1.55),(side*.17,.047,1.50),(side*.105,.13,1.325)])
        def outer(p):
            center=Vector((0,-.015,1.43));direction=Vector((0,center.y-p.y,center.z-p.z)).normalized()
            hit=shirt_surface.tree.ray_cast(p-direction*2,direction)
            if hit[0] is None:raise RuntimeError('Shoulder bridge guide misses the shirt')
            return hit
        points=[];fields=[]
        for i,p in enumerate(path):
            tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
            hit,n,triangle,_=outer(p);across=tangent.cross(n).normalized()
            for sign in (-1,1):
                hit,n,triangle,_=outer(p+across*.023*sign)
                points.append(hit+n*.016);fields.append(field(shirt_surface,hit,triangle))
        obj=make('captain_structural_shoulder_bridge',points,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(path)-1)],brigandine,custom_weights=fields)
        mod=obj.modifiers.new('Bridge_leather_thickness','SOLIDIFY');mod.thickness=.004;mod.offset=0
    # Closed rivet heads and their broad washers indicate the small internal
    # brigandine plates. They follow the finished panel rather than bare skin.
    def front(surface,x,z,offset=0):
        hit,n,triangle,_=surface.tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
        if hit is None:raise RuntimeError('Uniform detail is outside its supporting panel')
        return hit+n*offset,n,triangle
    def stud(name,surface,x,z,radius,mat):
        p,n,triangle=front(surface,x,z,.0008);across=Vector((1,0,0));up=n.cross(across).normalized()
        profile=[(.95,0),(1,.0012),(.82,.0032),(.35,.0045),(.04,.0046)];points=[];sides=12
        for radial,depth in profile:
            for i in range(sides):
                angle=i/sides*math.tau;points.append(p+n*depth+(across*math.cos(angle)+up*math.sin(angle))*radius*radial)
        faces=[(r*sides+i,r*sides+(i+1)%sides,(r+1)*sides+(i+1)%sides,(r+1)*sides+i) for r in range(len(profile)-1) for i in range(sides)]
        faces.extend([tuple(reversed(range(sides))),tuple((len(profile)-1)*sides+i for i in range(sides))])
        obj=make(name,points,faces,mat,'chest');bind_detail(obj,[surface]);return obj
    for row,z in enumerate([1.095,1.17,1.245,1.32,1.395]):
        for x in [-.125,-.07,0,.07,.125]:
            if row==4 and x<0:continue
            stud('captain_brigandine_plate_rivet',torso_surface,x,z,.0033,gold)
    for x in (-.012,.012):
        path=[front(torso_surface,x,1.075+i/32*.36,.0018)[0] for i in range(33)]
        seam=sweep('captain_double_front_seam',path,[.0012]*len(path),thread,'chest',5);bind_detail(seam,[torso_surface])
    # A field shield with three rising rays is an original Aegis service mark.
    # Its shaped face, turned perimeter and embroidery remain supported cloth.
    badge_x=-.084;badge_z=1.403
    outline=[(-.035,.037),(-.017,.045),(.017,.045),(.035,.037),(.033,-.008),(.020,-.030),(0,-.047),(-.020,-.030),(-.033,-.008)]
    badge=[front(torso_surface,badge_x+x,badge_z+z,.0035)[0] for x,z in outline]
    center=front(torso_surface,badge_x,badge_z,.0035)[0];badge_vertices=[center]+badge
    badge_obj=panel('captain_aegis_field_shield',badge_vertices,[(0,i+1,(i+1)%len(badge)+1) for i in range(len(badge))],felt,torso_surface,.002)
    edge=sweep('captain_aegis_shield_border',badge+[badge[0]],[.0018]*(len(badge)+1),gold,'chest',6);bind_detail(edge,[torso_surface])
    rays=[[(-.021,-.016),(0,-.032),(.021,-.016)],[(-.020,.008),(-.013,.024)],[(0,-.002),(0,.030)],[(.020,.008),(.013,.024)]]
    for path in rays:
        points=[front(torso_surface,badge_x+x,badge_z+z,.006)[0] for x,z in path]
        obj=sweep('captain_aegis_rising_ray',points,[.0018]*len(points),gold,'chest',6);bind_detail(obj,[torso_surface])
    # Three short overlapping shoulder lames articulate with the actual sleeve
    # field; the small plates leave the elbow and axilla free through combat.
    bone=rig.data.bones['upper_arm_L'];axis=(bone.tail_local-bone.head_local).normalized()
    across=axis.cross(Vector((0,1,0))).normalized();other=axis.cross(across).normalized()
    def shoulder_surface(t,angle,offset):
        center=bone.head_local.lerp(bone.tail_local,t);direction=across*math.cos(angle)+other*math.sin(angle)
        hit,n,triangle,_=shirt_surface.tree.ray_cast(center+direction*.8,-direction)
        if hit is None:raise RuntimeError('Shoulder armor has no sleeve surface')
        return hit+n*offset,triangle,hit
    def shoulder_patch(name,start,end,offset,mat,thickness):
        points=[];fields=[];segments=24;steps=8
        for row in range(steps+1):
            t=start+(end-start)*row/steps
            for i in range(segments+1):
                angle=-1.18+2.36*i/segments;p,triangle,hit=shoulder_surface(t,angle,offset)
                points.append(p);fields.append(field(shirt_surface,hit,triangle))
        faces=[(r*(segments+1)+i,r*(segments+1)+i+1,(r+1)*(segments+1)+i+1,(r+1)*(segments+1)+i) for r in range(steps) for i in range(segments)]
        obj=make(name,points,faces,mat,custom_weights=fields)
        solid=obj.modifiers.new('Formed_lame_thickness','SOLIDIFY');solid.thickness=thickness;solid.offset=0
        return obj
    pad=shoulder_patch('captain_left_shoulder_pad',.06,.51,.006,felt,.004)
    for t in (.10,.47):
        for angle in (-1.10,1.10):
            links.append({'id':f'{pad.name}_shirt_{t}_{angle}','subject':pad.name,'support':shirt.name,
                          'seed':list(shoulder_surface(t,angle,.003)[0])})
    for i in range(3):
        lame=shoulder_patch('captain_articulated_shoulder_lame',.09+i*.13,.215+i*.13,.012,steel,.0022)
        links.append({'id':lame.name+'_supported_by_pad','subject':lame.name,'support':pad.name,
                      'seed':list(shoulder_surface(.17+i*.13,0,.009)[0])})
    # Two compact, deliberately different cases stay high on the belt, above
    # the thigh fold. Their closed gussets and actual suspension are retained.
    belt=bpy.data.objects['work_belt'];belt_surface=ClothSurface(belt)
    def belt_back(x):
        hit= belt_surface.tree.ray_cast(Vector((x,2,1.02)),Vector((0,-1,0)))[0]
        if hit is None:raise RuntimeError('Dispatch hanger misses its belt')
        return hit.y
    def case(name,cx,height,width,depth):
        cy=belt_back(cx)+depth+.014;count=32;sections=[(1.065,.88),(1.052,1),(1.0,.99),(1.065-height+.020,.87),(1.065-height,.60)];points=[]
        for z,scale in sections:
            for i in range(count):
                a=i/count*math.tau;points.append(Vector((cx+width*scale*math.sin(a),cy+depth*scale*math.cos(a),z)))
        faces=[(r*count+i,r*count+(i+1)%count,(r+1)*count+(i+1)%count,(r+1)*count+i) for r in range(len(sections)-1) for i in range(count)]
        faces.extend([tuple(reversed(range(count))),tuple((len(sections)-1)*count+i for i in range(count))])
        obj=make(name,points,faces,gear,'hips');surface=ClothSurface(obj)
        rim=[points[i]+Vector((0,0,.002)) for i in range(count)]+[points[0]+Vector((0,0,.002))]
        edging=sweep(name+'_turned_flap_edge',rim,[.0022]*len(rim),binding,'hips',6);bind_detail(edging,[surface])
        return obj,cy
    dispatch,dispatch_y=case('captain_dispatch_case',.145,.160,.072,.035)
    seals,seals_y=case('captain_seal_tool_sheath',-.145,.132,.042,.026)
    for carried,cy,width in [(dispatch,dispatch_y,.032),(seals,seals_y,.019)]:
        for sign in (-1,1):
            x=(.145 if carried==dispatch else -.145)+sign*width;back=belt_back(x)
            path=densify([(x,back+.001,1.04),(x,back+.006,1.058),(x,cy,1.079),(x,cy+.018,1.059),(x,cy+.020,1.025)],6)
            points=[]
            for p in path:points.extend([p+Vector((-.008,0,0)),p+Vector((.008,0,0))])
            obj=make('captain_flat_case_hanger',points,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(path)-1)],leather,'hips')
            solid=obj.modifiers.new('Cut_hanger_leather','SOLIDIFY');solid.thickness=.003;solid.offset=0
            links.append({'id':obj.name+'_belt_root','subject':obj.name,'support':belt.name,'seed':list(path[0])})
            links.append({'id':obj.name+'_case_root','subject':obj.name,'support':carried.name,'seed':list(path[-1])})
    # Fit both terminal corners, not just their average, onto the sloping host.
    def attach_edge(obj,row,host,label):
        surface=ClothSurface(host);rows=len(obj.data.vertices)//2;row=row if row>=0 else rows+row
        corrections=[]
        for edge in range(2):
            vertex=obj.data.vertices[row*2+edge];hit,n,triangle,_=surface.tree.find_nearest(vertex.co)
            corrections.append((hit+n*.001-vertex.co,surface.weights(hit,triangle),hit))
        for r in range(max(0,row-10),min(rows,row+11)):
            t=max(0,1-abs(r-row)/10);t=t*t*(3-2*t)
            for edge in range(2):
                index=r*2+edge;vertex=obj.data.vertices[index];delta,host_field,hit=corrections[edge]
                vertex.co+=delta*t;weights={obj.vertex_groups[g.group].name:g.weight*(1-t) for g in vertex.groups}
                for name,value in host_field.items():weights[name]=weights.get(name,0)+value*t
                for group in obj.vertex_groups:group.remove([index])
                selected=sorted(weights.items(),key=lambda row:-row[1])[:4];total=sum(v for _,v in selected)
                for name,value in selected:
                    group=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name);group.add([index],value/total,'REPLACE')
        obj.data.update();bpy.context.view_layer.update()
        for edge,(_,_,hit) in enumerate(corrections):links.append({'id':label+'_edge_'+str(edge),'subject':obj.name,'support':host.name,'seed':list(hit)})
    for obj in [o for o in bpy.context.scene.objects if o.name.startswith('captain_structural_shoulder_bridge')]:
        attach_edge(obj,0,torso,obj.name+'_front_seam');attach_edge(obj,-1,torso,obj.name+'_rear_seam')
    for obj in [o for o in bpy.context.scene.objects if o.name.startswith('captain_flat_case_hanger')]:
        carried=next(link['support'] for link in links if link['id']==obj.name+'_case_root')
        attach_edge(obj,0,belt,obj.name+'_belt_seam');attach_edge(obj,-1,bpy.data.objects[carried],obj.name+'_case_seam')
    # Corner seams supersede the nominal center seeds used to identify each
    # case. Retaining those old guide points would not measure finished contacts.
    links=[link for link in links if not link['id'].endswith(('_belt_root','_case_root'))]
    for link in links:
        for role in ('subject','support'):
            obj=bpy.data.objects[link[role]];surface=ClothSurface(obj)
            hit,n,triangle,distance=surface.tree.find_nearest(Vector(link['seed']))
            if distance>.012:raise RuntimeError('Unattached source construction: '+link['id']+'/'+role+' '+str(distance))
            link[role]={'object':obj.name,'materials':[m.name for m in obj.data.materials],'point':list(hit),
                        'bounds':{'min':[min(p[i] for p in surface.points) for i in range(3)],'max':[max(p[i] for p in surface.points) for i in range(3)]}}
        link['maximumGap']=.006
    work=Path(__file__).resolve().parents[1]
    (work/'review/equipment-attachment-source.json').write_text(json.dumps({'schemaVersion':1,'status':'source_measured','links':links},indent=2)+'\n')
