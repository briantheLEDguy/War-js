"""Working farmer construction: fitted braces, a seed pouch and pruning sheath.

Each surface is an authored pattern or continuous swept cross-section. Braces
inherit the supporting shirt field; compact equipment is suspended at the belt.
"""
import math
import bpy
from mathutils import Vector
from surface_bindings import ClothSurface, bind_detail


def dress_farmer(make, sweep, material, rig, materials):
    shirt=bpy.data.objects['shirt_continuous_tailored_surface']
    thickness=[mod for mod in shirt.modifiers if mod.type=='SOLIDIFY' and mod.show_viewport]
    try:
        for mod in thickness:mod.show_viewport=False
        bpy.context.view_layer.update()
        support=ClothSurface(shirt)
    finally:
        for mod in thickness:mod.show_viewport=True
        bpy.context.view_layer.update()
    canvas=material('farmer_brace_herringbone',(.19,.215,.145),.94,textile=True)
    leather=materials['leather'];seam=materials['seam']

    def fitted(p,front):
        p=Vector(p)
        if p.y<-.035:
            ray=support.tree.ray_cast(Vector((p.x,-2,p.z)),Vector((0,1,0)))
        elif p.y>.07:
            ray=support.tree.ray_cast(Vector((p.x,2,p.z)),Vector((0,-1,0)))
        else:
            ray=support.tree.ray_cast(Vector((p.x,p.y,3)),Vector((0,0,-1)))
        hit,normal,triangle,distance=ray if ray[0] is not None else support.tree.find_nearest(p)
        return hit+normal*.009

    # Front and back edges travel over the same shoulder shell. The cut pattern
    # is thickened inward, so the finished cloth remains a supporting surface.
    for side in (-1,1):
        stations=[(side*.125,-.21,1.04),(side*.135,-.20,1.15),
                  (side*.145,-.18,1.30),(side*.150,-.11,1.46),
                  (side*.160,-.035,1.54),(side*.155,.045,1.54),
                  (side*.130,.135,1.45),(side*.10,.165,1.30),
                  (side*.075,.17,1.16),(side*.06,.165,1.04)]
        path=[]
        for a,b in zip(stations,stations[1:]):
            path.extend(Vector(a).lerp(Vector(b),i/8) for i in range(8))
        path.append(Vector(stations[-1]));vertices=[]
        for p in path:
            for sign in (-1,1):vertices.append(fitted(p+Vector((sign*.017,0,0)),p.y<0))
        faces=[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(path)-1)]
        strap=make('farmer_fitted_brace_'+str(side),vertices,faces,canvas,'hips')
        bind_detail(strap,[support]);solid=strap.modifiers.new('Bound_canvas_thickness','SOLIDIFY')
        solid.thickness=.003;solid.offset=0
        for edge in (0,1):
            points=[vertices[i*2+edge] for i in range(len(path))]
            binding=sweep('farmer_brace_bound_edge',points,[.0016]*len(points),seam,'hips',6)
            bind_detail(binding,[support])
        # Forged slide follows the chest plane at its actual cloth location.
        p=fitted((side*.14,-.20,1.19),True)
        for a,b in [((-.021,0,-.019),(.021,0,-.019)),((-.021,0,.019),(.021,0,.019)),
                    ((-.021,0,-.019),(-.021,0,.019)),((.021,0,-.019),(.021,0,.019)),
                    ((-.021,0,0),(.021,0,0))]:
            obj=sweep('farmer_brace_iron_slide',[p+Vector(a)+Vector((0,-.003,0)),p+Vector(b)+Vector((0,-.003,0))],[.0022,.0022],materials['iron'],'hips',6)
            bind_detail(obj,[support])

    # A gusseted canvas seed pouch lies behind the right hip. Profile stations
    # carry a fuller rounded bottom and a narrower leather-bound folded mouth.
    belt_support=ClothSurface(bpy.data.objects['work_belt'])
    def belt_back(x):
        hit=belt_support.tree.ray_cast(Vector((x,2,1.02)),Vector((0,-1,0)))[0]
        if hit is None:raise RuntimeError('Equipment hanger has no supporting belt')
        return hit.y
    center=Vector((-.155,belt_back(-.155)+.025,.985));sections=[(0,.069,.024),(-.025,.080,.042),
        (-.065,.089,.051),(-.11,.086,.049),(-.153,.070,.038),(-.175,.040,.022)]
    vertices=[];count=32
    for z,width,depth in sections:
        for i in range(count):
            angle=i/count*math.tau
            vertices.append(center+Vector((width*math.sin(angle),depth*math.cos(angle),z+.004*math.sin(angle*3))))
    faces=[(r*count+i,r*count+(i+1)%count,(r+1)*count+(i+1)%count,(r+1)*count+i)
           for r in range(len(sections)-1) for i in range(count)]
    faces.append(tuple(reversed([(len(sections)-1)*count+i for i in range(count)])))
    pouch=make('farmer_sewn_seed_pouch',vertices,faces,canvas,'hips')
    sub=pouch.modifiers.new('Soft_filled_gusset','SUBSURF');sub.levels=sub.render_levels=1
    solid=pouch.modifiers.new('Canvas_thickness','SOLIDIFY');solid.thickness=.003
    for sign in (-1,1):
        points=[center+Vector((sign*w,0,z)) for z,w,d in sections]
        sweep('farmer_seed_pouch_side_binding',points,[.0024]*len(points),leather,'hips',6)
    mouth=[center+Vector((.069*math.sin(i/count*math.tau),.024*math.cos(i/count*math.tau),.003+.004*math.sin(i/count*math.tau*3))) for i in range(count+1)]
    sweep('farmer_seed_pouch_drawcord',mouth,[.0021]*len(mouth),seam,'hips',6)
    for x in (-.035,.035):
        sweep('farmer_seed_pouch_tie',[center+Vector((x,.028,.002)),center+Vector((x*.8,.046,-.028)),center+Vector((x*.55,.039,-.058))],[.0022,.0024,.0018],seam,'hips',6)
    # Each flat hanger wraps its own actual section of the curved belt.
    # Reusing the pouch center's depth leaves the outer hanger unsupported.
    for x in (-.035,.035):
        px=center.x+x;by=belt_back(px)
        points=[Vector((px,y,z)) for y,z in [(center.y-.025,.973),
            (by-.009,.993),(by-.009,1.047),(by+.006,1.051),
            (by+.012,1.014),(center.y+.030,.973)]]
        vertices=[]
        for i,point in enumerate(points):
            tangent=(points[(i+1)%len(points)]-points[(i-1)%len(points)]).normalized()
            normal=tangent.cross(Vector((1,0,0))).normalized()
            for width,depth in [(-.007,-.002),(.007,-.002),(.007,.002),(-.007,.002)]:
                vertices.append(point+Vector((width,0,0))+normal*depth)
        faces=[(i*4+j,i*4+(j+1)%4,((i+1)%len(points))*4+(j+1)%4,((i+1)%len(points))*4+j)
               for i in range(len(points)) for j in range(4)]
        make('farmer_pouch_fitted_flat_hanger',vertices,faces,leather,'hips')

    # Curved pruning knife is carried sheathed behind the opposite hip. A shaped
    # wood handle, peened tang, bolster and wet-formed sheath identify its role.
    origin=Vector((.16,belt_back(.16)+.014,.985));axis=Vector((.28,.12,-1)).normalized()
    across=Vector((1,0,.28)).normalized();depth=axis.cross(across).normalized()
    def frame(t,x,y):return origin+axis*t+across*x+depth*y
    profile=[(-.013,-.006),(-.018,0),(-.014,.007),(0,.010),(.014,.007),(.018,0),(.013,-.006),(0,-.009)]
    def loft(name,stations,mat):
        verts=[frame(t,x*width,y*thick) for t,width,thick in stations for x,y in profile]
        n=len(profile);fs=[(r*n+i,r*n+(i+1)%n,(r+1)*n+(i+1)%n,(r+1)*n+i) for r in range(len(stations)-1) for i in range(n)]
        fs.extend([tuple(reversed(range(n))),tuple((len(stations)-1)*n+i for i in range(n))])
        obj=make(name,verts,fs,mat,'hips');sub=obj.modifiers.new('Rounded_pattern_edges','SUBSURF');sub.levels=sub.render_levels=1
        return obj
    loft('farmer_pruning_knife_ash_handle',[(-.088,.72,.75),(-.079,1.03,1),(-.025,1.05,1),(-.017,.75,.78)],materials['wood'])
    loft('farmer_pruning_knife_bolster',[(-.02,1.2,1.25),(-.014,1.2,1.25)],materials['iron'])
    loft('farmer_pruning_knife_formed_sheath',[(-.012,1.28,1.3),(.007,1.32,1.30),(.08,1.25,1.22),(.145,.79,.8),(.163,.1,.3)],leather)
    hanger=[Vector((.16,belt_back(.16)+offset,z)) for offset,z in [(-.002,.993),(-.002,1.045),(.018,1.052),(.032,1.019),(.014,.978),(-.002,.993)]]
    sweep('farmer_knife_belt_hanger',hanger,[.006]*len(hanger),leather,'hips',6)
    for sign in (-1,1):
        points=[frame(t,sign*w*.018,.003) for t,w,d in [(.0,1.32,1),(.04,1.31,1),(.08,1.25,1),(.12,1,1),(.15,.5,1)]]
        sweep('farmer_sheath_saddle_seam',points,[.0013]*len(points),seam,'hips',5)
