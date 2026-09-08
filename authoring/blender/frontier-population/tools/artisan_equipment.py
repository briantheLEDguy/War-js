"""Fitted, stitched apron pockets and a carried cross-peen workshop hammer."""
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def dress_artisan(apron, make, sweep, materials, waist):
    bpy.context.view_layer.update()
    tree=BVHTree.FromObject(apron,bpy.context.evaluated_depsgraph_get())
    def front(x,z,offset=.006):
        hit=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))[0]
        if hit is None:raise RuntimeError('Apron accessory lies outside its supporting panel')
        return hit+Vector((0,-offset,0))
    leather=materials['leather'];thread=materials['seam']
    for side in [-1,1]:
        vertices=[];cols=8;rows=6
        for r in range(rows):
            t=r/(rows-1);z=waist-.05-.13*t
            for c in range(cols):
                u=c/(cols-1);x=side*(.025+.155*u)
                vertices.append(front(x,z,.007+.012*math.sin(math.pi*u)*math.sin(math.pi*t*.85)))
        faces=[(r*cols+c,r*cols+c+1,(r+1)*cols+c+1,(r+1)*cols+c)
               for r in range(rows-1) for c in range(cols-1)]
        pocket=make('artisan_apron_tool_pocket_'+str(side),vertices,faces,leather)
        smooth=pocket.modifiers.new('Pocket_panel_finish','SUBSURF');smooth.levels=smooth.render_levels=1
        solid=pocket.modifiers.new('Pocket_leather_thickness','SOLIDIFY');solid.thickness=.003
        edge=[vertices[r*cols] for r in range(rows)]+vertices[-cols:]+[vertices[r*cols+cols-1] for r in reversed(range(rows))]
        sweep('pocket_bound_edge',edge,[.0018]*len(edge),leather)
        # Separate short stitches leave the pocket mouth open and show seam pitch.
        for a,b in zip(edge,edge[1:]):
            length=(b-a).length
            for i in range(max(1,int(length/.007))):
                t=i/max(1,int(length/.007));dt=min(.65*.007/max(length,.0001),1-t)
                points=[a.lerp(b,t)+Vector((0,-.002,0)),a.lerp(b,t+dt)+Vector((0,-.002,0))]
                if (points[1]-points[0]).length>.0001:sweep('saddle_stitch',points,[.00065,.00065],thread,sides=5)
        mouth=vertices[:cols]
        sweep('pocket_rolled_mouth',mouth,[.0024]*cols,leather)

    # Carried at the right hip, with the handle inclined clear of the thigh.
    origin=Vector((.31,-.15,waist+.025))
    def local(x,y,z):return origin+Vector((x-.18*z,y,z))
    sections=[(-.27,.012,.009),(-.25,.015,.011),(-.19,.011,.010),(-.10,.013,.011),(-.025,.014,.012),(.027,.011,.010)]
    sides=10;vertices=[]
    for z,rx,ry in sections:
        for i in range(sides):
            angle=i/sides*math.tau;vertices.append(local(rx*math.cos(angle),ry*math.sin(angle),z))
    faces=[(r*sides+i,r*sides+(i+1)%sides,(r+1)*sides+(i+1)%sides,(r+1)*sides+i)
           for r in range(len(sections)-1) for i in range(sides)]
    faces.extend([tuple(reversed(range(sides))),tuple((len(sections)-1)*sides+i for i in range(sides))])
    handle=make('artisan_hammer_shaped_ash_handle',vertices,faces,materials['wood'],'hips')
    for face in handle.data.polygons:
        for loop in face.loop_indices:
            index=handle.data.loops[loop].vertex_index
            handle.data.uv_layers.active.data[loop].uv=((index%sides)/sides,(index//sides)/(len(sections)-1))
    sub=handle.modifiers.new('Handle_hand_finish','SUBSURF');sub.levels=sub.render_levels=1
    # Eight-sided forged sections taper from a broad striking face to a narrow
    # cross-peen. These profiles also give the head visible bevels and a shoulder.
    sections=[(-.083,.009,.021),(-.075,.012,.024),(-.030,.019,.023),(-.020,.025,.024),
              (.032,.024,.024),(.060,.022,.022),(.070,.022,.022),(.075,.018,.018)]
    vertices=[]
    for x,depth,height in sections:
        for yy,zz in [(-.7,-1),(.7,-1),(1,-.7),(1,.7),(.7,1),(-.7,1),(-1,.7),(-1,-.7)]:
            vertices.append(local(x,yy*depth,zz*height+.015))
    faces=[(r*8+i,r*8+(i+1)%8,(r+1)*8+(i+1)%8,(r+1)*8+i)
           for r in range(len(sections)-1) for i in range(8)]
    faces.extend([tuple(reversed(range(8))),tuple((len(sections)-1)*8+i for i in range(8))])
    head=make('artisan_forged_cross_peen_head',vertices,faces,materials['iron'],'hips')
    for face in head.data.polygons:face.use_smooth=False
    # A stitched leather loop carries the shaft below the head, with its rear
    # fixing sunk into the waist belt instead of hovering beside it.
    verts=[];count=24
    for z in [-.039,-.062]:
        for i in range(count):
            a=i/count*math.tau;verts.append(local(.020*math.cos(a),.018*math.sin(a),z))
    loop=make('artisan_hammer_retaining_loop',verts,[(i,(i+1)%count,count+(i+1)%count,count+i) for i in range(count)],leather,'hips')
    solid=loop.modifiers.new('Thick_belt_loop','SOLIDIFY');solid.thickness=.003
    for dx in [-.013,.013]:
        sweep('hammer_loop_attachment',[local(dx,.016,-.055),Vector((.25+dx,-.125,waist-.008))],[.008,.008],leather,'hips',8)
