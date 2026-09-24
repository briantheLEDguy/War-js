"""Shaped ledger satchel, inventory stylus, coat closures and original rank marks."""
import math,json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector,Matrix
from surface_bindings import ClothSurface,bind_detail
from apron_clearance import _surface,_skin


CARRIER_PARTS=('officer_closed_ledger_case','officer_ledger_case_flap','officer_inventory_stylus','officer_stylus_sleeve_binding','officer_case_saddle_stitch')


def fit_equipment(make,rig,mount):
    """Place the rear carrier outside the rest clothing envelope; native motion clearance is separate."""
    center,waist,rotation,leather=mount
    case=bpy.data.objects['officer_closed_ledger_case'];base=_surface(case)
    case_points=(base[0]@np.array(base[3]).T)[:,:3]
    lower=case_points.min(axis=0)-.010;upper=case_points.max(axis=0)+.010
    surfaces=[(name,_surface(bpy.data.objects[name])) for name in ('shirt_continuous_tailored_surface','trousers_continuous_tailored_surface','dark_elf_supply_officer_exposed_anatomy')]
    maximum=-100;worst=None;sample_count=0
    rig.animation_data_clear()
    for bone in rig.pose.bones: bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    hip=rig.pose.bones['hips']
    inverse=np.array((rig.matrix_world@hip.matrix@hip.bone.matrix_local.inverted()@rig.matrix_world.inverted()).inverted())
    for name,surface in surfaces:
        points=_skin(surface,rig);points=points@inverse[:3,:3].T+inverse[:3,3]
        triangles=points[np.array(surface[1],dtype=int)]
        # Triangle AABBs conservatively cover the footprint, including
        # triangles whose vertices fall just outside a case edge.
        lo=triangles.min(axis=1);hi=triangles.max(axis=1)
        mask=(hi[:,0]>=lower[0])&(lo[:,0]<=upper[0])&(hi[:,2]>=lower[2])&(lo[:,2]<=upper[2])
        if np.any(mask):
            posterior=float(triangles[mask,:,1].max())
            if posterior>maximum:maximum=posterior;worst={'pose':'rest','surface':name,'posterior':posterior}
    sample_count=1
    rig.animation_data_clear()
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    margin=.012;shift=max(0,maximum+margin-float(case_points[:,1].min()))
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.name.startswith(CARRIER_PARTS):
            for vertex in obj.data.vertices:vertex.co.y+=shift
            obj.data.update()
    fitted=center+Vector((0,shift,0));bpy.context.view_layer.update()
    suspend_case(make,leather,bpy.data.objects['work_belt'],case,fitted,waist,rotation)
    report={'method':'Rest body surface, conservatively clipped triangle AABBs in carrier hip frame',
            'samples':sample_count,'restCenter':list(center),'fittedCenter':list(fitted),'posteriorShift':shift,'minimumClearance':margin,'worstEnvelope':worst}
    (Path(__file__).resolve().parents[1]/'review/carrier-fit.json').write_text(json.dumps(report,separators=(',',':')))
    print('Fitted carrier to animated envelope: '+json.dumps(report),flush=True)


def suspend_case(make,leather,belt,case,center,waist,rotation):
    """Closed leather loops join real surface patches at both loaded ends."""
    support_material=belt.data.materials[0].copy();support_material.name='officer_belt_attachment_support'
    belt.data.materials[0]=support_material
    belt_surface=ClothSurface(belt);case_surface=ClothSurface(case)
    mats=[]
    for role in ('leather','belt_contact','case_contact'):
        mat=leather.copy();mat.name='officer_case_suspension_'+role;mats.append(mat)
    width=.018;columns=5
    outward=rotation@Vector((-1,0,0));width_axis=rotation@Vector((0,1,0))
    for number,offset in enumerate((-.049,.049)):
        def contact(surface,z,dy,direction):
            origin=center+width_axis*(offset+dy)+Vector((0,0,z-center.z))+outward*(2*direction)
            hit,normal,triangle,distance=surface.tree.ray_cast(origin,-outward*direction)
            if hit is None:raise RuntimeError('Suspension end has no finished support')
            return hit,surface.weights(hit,triangle)
        belt_end,_=contact(belt_surface,waist-.010,0,1)
        case_end,_=contact(case_surface,waist-.065,0,-1)
        # The loop descends around the clear space between coat and case, then
        # folds upward onto the case back. Thickness normals follow that turn.
        rows=[('belt',waist+z) for z in (.014,.002,-.010)]
        rows += [('bridge',t) for t in (.16,.32,.48,.64,.80,.92)]
        rows += [('case',waist+z) for z in (-.065,-.055,-.045)]
        centers=[]
        for role,value in rows:
            if role=='belt':point,_=contact(belt_surface,value,0,1)
            elif role=='case':point,_=contact(case_surface,value,0,-1)
            else:
                t=value;point=belt_end.lerp(case_end,t)
                point.z=(waist-.010)*(1-t)+(waist-.065)*t-.020*math.sin(math.pi*t)
            centers.append(point)
        vertices=[];weights=[]
        for index,(role,value) in enumerate(rows):
            tangent=centers[min(len(rows)-1,index+1)]-centers[max(0,index-1)]
            normal=width_axis.cross(tangent).normalized()
            if role=='belt':normal=outward
            if role=='case':normal=-outward
            for layer in range(2):
                for column in range(columns):
                    dy=width*(column/(columns-1)-.5)
                    if role=='belt':point,field=contact(belt_surface,value,dy,1)
                    elif role=='case':point,field=contact(case_surface,value,dy,-1)
                    else:
                        start,start_field=contact(belt_surface,waist-.010,dy,1)
                        end,end_field=contact(case_surface,waist-.065,dy,-1)
                        point=start.lerp(end,value);point.z=centers[index].z
                        field={name:start_field.get(name,0)*(1-value)+end_field.get(name,0)*value
                               for name in set(start_field)|set(end_field)}
                    vertices.append(point+normal*(.0005+layer*.003))
                    weights.append(list(field.items()))
        faces=[];roles=[];row_size=columns*2
        for row in range(len(rows)-1):
            for layer in range(2):
                for column in range(columns-1):
                    a=row*row_size+layer*columns+column;b=a+row_size
                    faces.append((a,a+1,b+1,b) if layer==0 else (a,b,b+1,a+1))
                    role=rows[row][0] if rows[row][0]==rows[row+1][0] else 'bridge'
                    roles.append(1 if role=='belt' and layer==0 else 2 if role=='case' and layer==0 else 0)
            for column in (0,columns-1):
                a=row*row_size+column;b=a+row_size
                faces.append((a,b,b+columns,a+columns));roles.append(0)
        for row in (0,len(rows)-1):
            for column in range(columns-1):
                a=row*row_size+column;faces.append((a,a+columns,a+columns+1,a+1));roles.append(0)
        obj=make('officer_case_suspension_'+str(number),vertices,faces,mats[0],custom_weights=weights)
        obj.data.materials.append(mats[1]);obj.data.materials.append(mats[2])
        for face,role in zip(obj.data.polygons,roles):face.material_index=role


def equip(make,sweep,material,mats,waist):
    shirt=ClothSurface(bpy.data.objects['shirt_continuous_tailored_surface'])
    leather=material('officer_ledger_case_leather',(.085,.051,.044),.73,textile=True)
    iron=material('officer_inventory_metal',(.26,.28,.30),.36,.8)
    brass=mats['brass'];seam=mats['seam']
    belt=bpy.data.objects['work_belt'];left=min(v.co.x for v in belt.data.vertices)
    # Full closed rounded profile: contoured sides, folded bottom and flap lip.
    center=Vector((left-.051,.045,waist-.084));count=16
    outline=[(-.064,-.078),(-.071,-.066),(-.073,.047),(-.065,.077),(-.047,.084),(.047,.084),(.065,.077),(.073,.047),(.071,-.066),(.064,-.078),(.042,-.083),(.018,-.084),(-.018,-.084),(-.042,-.083),(-.055,-.082),(-.061,-.080)]
    points=[]
    for depth,scale in [(0,.90),(-.004,1),(-.035,1.02),(-.041,.93)]:
        for y,z in outline:points.append(center+Vector((depth,y*scale,z*scale)))
    faces=[(r*count+i,r*count+(i+1)%count,(r+1)*count+(i+1)%count,(r+1)*count+i) for r in range(3) for i in range(count)]
    faces.extend([tuple(reversed(range(count))),tuple(3*count+i for i in range(count))])
    shell_material=leather.copy();shell_material.name='officer_ledger_case_shell'
    obj=make('officer_closed_ledger_case',points,faces,shell_material,'hips')
    mod=obj.modifiers.new('Turned_ledger_edges','SUBSURF');mod.levels=mod.render_levels=1
    # A separate closed folded flap crosses the upper lip and overlaps the case.
    rows=[(center.x+.002,.075),(center.x-.02,.091),(center.x-.043,.079),(center.x-.046,.017)]
    points=[Vector((x,center.y+y,center.z+z)) for x,z in rows for y in [-.057,-.028,0,.028,.057]]
    faces=[(r*5+i,r*5+i+1,(r+1)*5+i+1,(r+1)*5+i) for r in range(3) for i in range(4)]
    flap=make('officer_ledger_case_flap',points,faces,leather,'hips')
    sub=flap.modifiers.new('Flap_fold','SUBSURF');sub.levels=sub.render_levels=2
    thick=flap.modifiers.new('Flap_leather_thickness','SOLIDIFY');thick.thickness=.003
    # The inventory stylus sits in its outer sleeve, clear of clothing and hands.
    root=Vector((center.x-.051,center.y+.045,center.z-.06))
    path=[root+Vector((0,0,z)) for z in [0,.018,.125,.155]]
    sweep('officer_inventory_stylus',path,[.0035,.004,.004,.001],iron,'hips',10)
    for z in [.028,.096]:
        path=[root+Vector((.004*math.sin(i*math.tau/16),.004*math.cos(i*math.tau/16),z)) for i in range(17)]
        sweep('officer_stylus_sleeve_binding',path,[.002]*17,leather,'hips',6)
    # Rank is original: three short offset bars in a bound breast patch.
    def front(x,z):
        hit=shirt.tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))[0]
        if hit is None:raise RuntimeError('Rank detail has no coat support')
        return hit+Vector((0,-.004,0))
    for row in range(3):
        z=waist+.276+row*.016;a=front(-.076,z);b=front(-.032,z+.010)
        obj=sweep('officer_rank_bar',[a,b],[.0028,.0028],brass,'chest',8);bind_detail(obj,[shirt])
    # Crossed small closures have shaped mesh profiles and surface weights.
    for z in [waist+.08,waist+.145,waist+.21,waist+.275]:
        p=front(0,z);outline=[(-.008,-.006),(-.011,0),(-.008,.006),(.008,.006),(.011,0),(.008,-.006)]
        vertices=[p+Vector((x,depth,h)) for depth in [0,-.003] for x,h in outline]
        faces=[(i,(i+1)%6,6+(i+1)%6,6+i) for i in range(6)]+[tuple(reversed(range(6))),tuple(range(6,12))]
        obj=make('officer_coat_closure',vertices,faces,brass,'chest');bind_detail(obj,[shirt])
    # Stitching is embedded along the case perimeter and kept on the same bone.
    for z in [center.z-.067,center.z+.069]:
        for y in range(13):
            p=Vector((center.x-.042,center.y-.051+y*.008,z))
            sweep('officer_case_saddle_stitch',[p,p+Vector((0,.004,0))],[.0008,.0008],seam,'hips',5)
    # A rear belt mount leaves the complete case outside the arm swing. Fit its
    # back to the finished coat envelope instead of guessing a waist radius.
    rotation=Matrix.Rotation(-math.pi/2,3,'Z')
    mounted=Vector((-.125,0,center.z));back=[]
    for dx in (-.073,-.036,0,.036,.073):
        for dz in (-.083,-.04,0,.04,.084):
            hit=shirt.tree.ray_cast(Vector((mounted.x+dx,2,mounted.z+dz)),Vector((0,-1,0)))[0]
            if hit is not None:back.append(hit.y)
    if not back:raise RuntimeError('Rear carrier has no finished coat envelope')
    mounted.y=max(back)+.020
    for part in bpy.context.scene.objects:
        if part.type=='MESH' and part.name.startswith(CARRIER_PARTS):
            for vertex in part.data.vertices:vertex.co=mounted+rotation@(vertex.co-center)
            part.data.update()
    bpy.context.view_layer.update()
    return mounted,waist,rotation,leather
