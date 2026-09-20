"""Authored divided oversmock, suspended gathering satchel and medicine kit."""
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from surface_bindings import ClothSurface,bind_detail


def dress_herbalist(make,sweep,material,rig,materials):
    shirt=bpy.data.objects['shirt_continuous_tailored_surface']
    lining=[m for m in shirt.modifiers if m.type=='SOLIDIFY' and m.show_viewport]
    try:
        for m in lining:m.show_viewport=False
        bpy.context.view_layer.update();support=ClothSurface(shirt)
    finally:
        for m in lining:m.show_viewport=True
        bpy.context.view_layer.update()
    legs=ClothSurface(bpy.data.objects['trousers_continuous_tailored_surface'])
    sage=material('herbalist_sage_smock',(.16,.25,.19),.94,textile=True)
    binding=material('herbalist_smock_bound_edge',(.32,.38,.27),.9)
    canvas=material('herbalist_tool_satchel_canvas',(.27,.22,.13),.91,textile=True)
    straps=material('herbalist_hanger_leather',(.15,.085,.038),.77,textile=True)
    vial=material('herbalist_tool_vial_glaze',(.35,.41,.29),.26)
    cork=material('herbalist_tool_ash_cork',(.30,.21,.105),.89,textile=True)
    herb=material('herbalist_tool_herb_leaf',(.11,.205,.078),.86)
    stem=material('herbalist_tool_herb_stem',(.20,.26,.11),.9)

    projections={}

    def bind_torso(obj):
        # Sleeveless cloth belongs to the trunk. Close arm/neck triangles must
        # not pull opposite edges of a shoulder bridge into different limbs.
        fields=[]
        for vertex in obj.data.vertices:
            field={}
            for entry in vertex.groups:
                name=obj.vertex_groups[entry.group].name
                if 'arm' in name or 'shoulder' in name or name=='neck':name='upper_chest'
                field[name]=field.get(name,0)+entry.weight
            fields.append(field)
        obj.vertex_groups.clear()
        for i,field in enumerate(fields):
            rows=sorted(field.items(),key=lambda row:-row[1])[:4];total=sum(w for _,w in rows)
            for name,w in rows:
                group=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
                group.add([i],w/total,'REPLACE')

    def point_on(surface,p,direction,allowance):
        p=Vector(p);direction=Vector(direction)
        hit,normal,triangle,_=surface.tree.ray_cast(p-direction*2,direction)
        if hit is None:hit,normal,triangle,_=surface.tree.find_nearest(p)
        if hit is None:raise RuntimeError('Authored smock has no supporting garment')
        result=hit+normal*allowance
        projections[tuple(result)]=sorted(surface.weights(hit,triangle).items(),key=lambda row:-row[1])[:4]
        return result

    # Torso shell drops under each arm; shoulder bridges leave actual armholes.
    count=96;rows=9;verts=[];shell_weights=[]
    for row in range(rows):
        t=row/(rows-1)
        for i in range(count):
            angle=i/count*math.tau;direction=Vector((math.sin(angle),math.cos(angle),0))
            top=1.432-.28*abs(math.sin(angle))**1.5;z=1.034+(top-1.034)*t
            hit,normal,triangle,_=support.tree.ray_cast(Vector((0,0,z)),direction)
            if hit is None:raise RuntimeError('Smock torso ray missed the continuous shirt')
            verts.append(hit+direction*.014);shell_weights.append(sorted(support.weights(hit,triangle).items(),key=lambda row:-row[1])[:4])
    faces=[(r*count+i,r*count+(i+1)%count,(r+1)*count+(i+1)%count,(r+1)*count+i) for r in range(rows-1) for i in range(count)]
    shell=make('herbalist_fitted_smock_torso',verts,faces,sage,custom_weights=shell_weights);bind_torso(shell)
    thickness=shell.modifiers.new('Turned_smock_thickness','SOLIDIFY');thickness.thickness=.003;thickness.offset=0
    for row in (0,rows-1):
        path=[verts[row*count+i%count] for i in range(count+1)]
        edge=sweep('herbalist_bound_smock_opening',path,[.0022]*len(path),binding,'hips',6);bind_detail(edge,[ClothSurface(shell)]);bind_torso(edge)
    for side in (-1,1):
        # Remove the neckline from the strip's supporting patch. A closest
        # point on the open neck rim is not a shoulder support.
        support_ids=[i for i,face in enumerate(support.triangles) if all(
            support.points[v].x*side>.060 and (support.points[v].z<1.48 or support.points[v].x*side>.110)
            for v in face)]
        strip_tree=BVHTree.FromPolygons(support.points,[support.triangles[i] for i in support_ids],all_triangles=True)
        stations=[(side*.095,-.18,1.29),(side*.13,-.15,1.46),(side*.13,-.09,1.525),
                  (side*.13,-.015,1.55),(side*.13,.05,1.535),(side*.13,.125,1.46),(side*.09,.15,1.20)]
        path=[]
        for a,b in zip(stations,stations[1:]):path.extend(Vector(a).lerp(Vector(b),i/12) for i in range(12))
        path.append(Vector(stations[-1]));v=[]
        for p in path:
            direction=(0,1,0) if p.y<-.035 else (0,-1,0) if p.y>.07 else (0,0,-1)
            for sign in (-1,1):
                guide=p+Vector((sign*.008,0,0));hit,normal,triangle,_=strip_tree.find_nearest(guide)
                if hit is None:raise RuntimeError('Shoulder strip lacks a supporting shirt patch')
                point=hit+normal*.009
                triangle=support_ids[triangle]
                projections[tuple(point)]=sorted(support.weights(hit,triangle).items(),key=lambda row:-row[1])[:4]
                v.append(point)
        fs=[(r*2,r*2+1,r*2+3,r*2+2) for r in range(len(path)-1)]
        bridge=make('herbalist_smock_shoulder_bridge',v,fs,sage,custom_weights=[projections[tuple(point)] for point in v])
        thick=bridge.modifiers.new('Bridge_turned_thickness','SOLIDIFY');thick.thickness=.003;thick.offset=0
        for edge in (0,1):
            points=[v[i*2+edge] for i in range(len(path))]
            obj=sweep('herbalist_shoulder_binding',points,[.002]*len(points),binding,'hips',6);bind_detail(obj,[ClothSurface(bridge)])

    # Four divided lappets follow the supporting trousers and leave a leg slit.
    for side in (-1,1):
        for back in (-1,1):
            v=[];cols=9;rows=10
            for row in range(rows):
                t=row/(rows-1);z=1.025-.31*t
                for col in range(cols):
                    u=col/(cols-1);x=side*(.036+.050*t+(.19-.046*t)*u)
                    v.append(point_on(legs,(x,back*.15,z),(0,-back,0),.020))
            fs=[(r*cols+c,r*cols+c+1,(r+1)*cols+c+1,(r+1)*cols+c) for r in range(rows-1) for c in range(cols-1)]
            if side*back<0:fs=[tuple(reversed(face)) for face in fs]
            panel=make('herbalist_divided_smock_lappet',v,fs,sage,custom_weights=[projections[tuple(point)] for point in v])
            thick=panel.modifiers.new('Divided_hem_thickness','SOLIDIFY');thick.thickness=.003;thick.offset=0
            border=list(range(cols))+[r*cols+cols-1 for r in range(1,rows)]+[(rows-1)*cols+c for c in range(cols-2,-1,-1)]+[r*cols for r in range(rows-2,0,-1)]
            border.append(border[0]);points=[v[i] for i in border]
            obj=sweep('herbalist_lappet_turned_binding',points,[.0021]*len(points),binding,'hips',6);bind_detail(obj,[ClothSurface(panel)])



def dress_herbalist_tools(make,sweep,material,rig,materials):
    canvas=bpy.data.materials['herbalist_tool_satchel_canvas']
    straps=bpy.data.materials['herbalist_hanger_leather']
    vial=bpy.data.materials['herbalist_tool_vial_glaze']
    cork=bpy.data.materials['herbalist_tool_ash_cork']
    herb=bpy.data.materials['herbalist_tool_herb_leaf']
    stem=bpy.data.materials['herbalist_tool_herb_stem']
    belt=ClothSurface(bpy.data.objects['work_belt'])
    def belt_back(x):
        hit=belt.tree.ray_cast(Vector((x,2,1.02)),Vector((0,-1,0)))[0]
        if hit is None:raise RuntimeError('Gathering equipment lacks belt support')
        return hit.y

    def flat_hanger(name,x,center_y,front_z,half_width=.008):
        by=belt_back(x)
        points=[Vector((x,y,z)) for y,z in [(center_y-.04,front_z),(by-.006,1.01),(by-.006,1.05),
                                             (by+.008,1.052),(by+.014,1.018),(center_y+.04,front_z)]]
        vertices=[]
        for i,p in enumerate(points):
            tangent=(points[(i+1)%len(points)]-points[(i-1)%len(points)]).normalized();normal=tangent.cross(Vector((1,0,0))).normalized()
            for width,depth in [(-half_width,-.002),(half_width,-.002),(half_width,.002),(-half_width,.002)]:vertices.append(p+Vector((width,0,0))+normal*depth)
        fs=[(i*4+j,i*4+(j+1)%4,((i+1)%len(points))*4+(j+1)%4,((i+1)%len(points))*4+j) for i in range(len(points)) for j in range(4)]
        return make(name,vertices,fs,straps,'hips')

    center=Vector((-.165,belt_back(-.165)+.072,.978))
    sections=[(0,.077,.037),(-.026,.086,.044),(-.10,.087,.049),(-.17,.073,.043),(-.198,.050,.028)]
    n=40;v=[]
    for z,width,depth in sections:
        for i in range(n):
            a=i/n*math.tau;v.append(center+Vector((width*math.sin(a),depth*math.cos(a),z)))
    fs=[(r*n+i,r*n+(i+1)%n,(r+1)*n+(i+1)%n,(r+1)*n+i) for r in range(len(sections)-1) for i in range(n)]
    fs.append(tuple(reversed([(len(sections)-1)*n+i for i in range(n)])))
    bag=make('herbalist_gathering_satchel',v,fs,canvas,'hips')
    smooth=bag.modifiers.new('Filled_canvas_gusset','SUBSURF');smooth.levels=smooth.render_levels=1
    thick=bag.modifiers.new('Satchel_canvas_thickness','SOLIDIFY');thick.thickness=.003;thick.offset=0
    for offset in (-.038,.038):flat_hanger('herbalist_satchel_belt_loop',center.x+offset,center.y,.963)
    for side in (-1,1):
        points=[center+Vector((side*w,0,z)) for z,w,d in sections]
        sweep('herbalist_satchel_gusset_binding',points,[.0028]*len(points),straps,'hips',6)
    points=[center+Vector((.077*math.sin(i/n*math.tau),.037*math.cos(i/n*math.tau),0)) for i in range(n+1)]
    sweep('herbalist_satchel_rolled_mouth',points,[.003]*len(points),straps,'hips',6)

    def bottle(name,origin,profile,mat):
        n=24;v=[origin+Vector((rx*math.sin(i/n*math.tau),ry*math.cos(i/n*math.tau),z)) for z,rx,ry in profile for i in range(n)]
        fs=[(r*n+i,r*n+(i+1)%n,(r+1)*n+(i+1)%n,(r+1)*n+i) for r in range(len(profile)-1) for i in range(n)]
        fs.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))])
        return make(name,v,fs,mat,'hips')
    for index in range(2):
        x=.13+index*.052;y=belt_back(x)+.058;origin=Vector((x,y,.90))
        bottle('herbalist_stoppered_medicine_vial',origin,[(0,.011,.011),(.004,.016,.015),(.060,.016,.015),(.073,.010,.010),(.076,.009,.009),(.092,.009,.009)],vial)
        bottle('herbalist_vial_cork',origin,[(.091,.008,.008),(.095,.010,.010),(.108,.010,.010),(.11,.008,.008)],cork)
        bottle('herbalist_vial_support_cup',origin,[(.001,.017,.017),(.004,.020,.020),(.038,.020,.020)],straps)
        flat_hanger('herbalist_vial_belt_loop',x,y,.931,.006)
    bag_support=ClothSurface(bag)
    for index in range(5):
        origin=center+Vector(((index-2)*.017,.008,.0));tip=origin+Vector(((index-2)*.013,.008,.14+.016*(index%2)))
        points=[origin.lerp(tip,t/8)+Vector((.005*math.sin(t*.5+index),0,0)) for t in range(9)]
        support=bag_support.tree.ray_cast(Vector((points[0].x,points[0].y,1.15)),Vector((0,0,-1)))[0]
        if support is None:raise RuntimeError('Gathered stem lacks a satchel floor support')
        points.insert(0,support+Vector((0,0,.0015)))
        sweep('herbalist_gathered_stem',points,[.0015]+[.0015-.0006*t/8 for t in range(9)],stem,'hips',6)
        for step in (4,6,8):
            for side in (-1,1):
                root=points[step];end=root+Vector((side*(.023+.003*index),-.012,.017));axis=end-root;cross=Vector((0,1,0));v=[]
                for row in range(7):
                    t=row/6;mid=root+axis*t+Vector((0,0,.004*math.sin(t*math.pi)));width=.008*math.sin(t*math.pi)
                    v.extend([mid-cross*width,mid+Vector((0,0,.0015)),mid+cross*width])
                fs=[(r*3+c,r*3+c+1,(r+1)*3+c+1,(r+1)*3+c) for r in range(6) for c in range(2)]
                leaf=make('herbalist_lanceolate_leaf',v,fs,herb,'hips');thick=leaf.modifiers.new('Leaf_thickness','SOLIDIFY');thick.thickness=.0007
