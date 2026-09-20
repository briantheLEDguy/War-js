"""A stitched, belt-supported peat knife sheath and its fitted ash grip."""
import math
import bpy
from mathutils import Vector
from surface_bindings import ClothSurface,bind_detail

def equip(make,sweep,materials,waist):
    belt=bpy.data.objects['work_belt'];surface=ClothSurface(belt)
    anchor,normal,_,_=surface.tree.find_nearest(Vector((-.24,.13,waist)))
    # The nearest triangle can be the inward winding of the leather profile.
    # The mount belongs outside the waist; use the radial outward planar normal.
    normal=Vector((normal.x,normal.y,0)).normalized()
    if normal.dot(Vector((anchor.x,anchor.y,0)))<0:normal=-normal
    anchor+=normal*.010
    # A rear-quarter suspension keeps the sheathed edge behind the forearm and
    # clear of the raised knee. Its shaped tip curves back rather than into thigh.
    origin=anchor+normal*.015
    across=Vector((normal.y,-normal.x,0)).normalized()
    def point(width,depth,z):
        # Dense source run probes require 20mm additional tip ease. The 35mm
        # addition retains a clearance margin after the two runtime reductions.
        return origin+across*width+normal*(depth+.065*max(0,-z/.28))+Vector((0,0,z))
    def profile(name,sections,mat):
        vertices=[];count=10
        for z,width,depth in sections:
            for index in range(count):
                a=index/count*math.tau
                vertices.append(point(math.cos(a)*width,math.sin(a)*depth,z))
        faces=[(r*count+i,r*count+(i+1)%count,(r+1)*count+(i+1)%count,(r+1)*count+i)
               for r in range(len(sections)-1) for i in range(count)]
        faces.extend([tuple(reversed(range(count))),tuple((len(sections)-1)*count+i for i in range(count))])
        obj=make(name,vertices,faces,mat,'hips')
        for f in obj.data.polygons:
            for loop in f.loop_indices:
                i=obj.data.loops[loop].vertex_index
                obj.data.uv_layers.active.data[loop].uv=((i%count)/count,(i//count)/(len(sections)-1))
        return obj
    sheath=profile('peat_knife_closed_wet_leather_sheath',[
        (-.29,.005,.003),(-.283,.012,.006),(-.25,.026,.010),(-.16,.034,.013),
        (-.07,.037,.014),(-.032,.039,.015),(-.020,.041,.016)],materials['leather'])
    bevel=sheath.modifiers.new('Turned_closed_leather_edges','SUBSURF');bevel.levels=bevel.render_levels=1
    grip=profile('peat_knife_shaped_ash_grip',[
        (-.020,.018,.010),(-.011,.020,.012),(.020,.018,.013),(.065,.020,.015),(.095,.024,.014),(.105,.020,.012)],materials['wood'])
    bevel=grip.modifiers.new('Carved_palm_finish','SUBSURF');bevel.levels=bevel.render_levels=1
    profile('peat_knife_ferrule',[(-.024,.022,.014),(-.021,.024,.016),(-.010,.024,.016),(-.007,.022,.014)],materials['iron'])
    # Double stitch lines are fitted to the evaluated leather surface, with
    # every short span closed so the GLB never relies on open line geometry.
    bpy.context.view_layer.update();support=ClothSurface(sheath)
    for side in (-1,1):
        for i in range(31):
            z=-.268+i*.0076;width=(.032 if z>-.23 else .020)*side
            samples=[]
            for end in (0,.0042):
                probe=point(width,.022,z+end);hit,n,_,_=support.tree.find_nearest(probe)
                samples.append(hit+n*.0011)
            stitch=sweep('peat_sheath_saddle_stitch',samples,[.0007,.0007],materials['seam'],'hips',5)
    # A wide folded hanger loops around the real belt and seats against sheath.
    bottom=point(0,-.002,-.07)
    stations=[anchor+Vector((0,0,.023)),anchor-normal*.006,anchor+Vector((0,0,-.03)),bottom]
    vertices=[p+across*w for p in stations for w in (-.014,.014)]
    strap=make('peat_knife_folded_belt_hanger',vertices,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(3)],materials['leather'],'hips')
    thickness=strap.modifiers.new('Folded_hanger_thickness','SOLIDIFY');thickness.thickness=.004
    sub=strap.modifiers.new('Rounded_leather_bend','SUBSURF');sub.levels=sub.render_levels=1
