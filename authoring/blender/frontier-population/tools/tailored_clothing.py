"""Cut garment profiles, fitted footwear, work details and groom construction.

Profiles are authored in the retained anatomical rest pose, then follow the same
regional proportion map as the skeleton. No primitive modeling operators.
"""
import math
from mathutils import Vector
from surface_garments import garments
from authored_artisan_head import build_head, build_beard
from mathutils.bvhtree import BVHTree
import bpy


def tailor(kind, race, body, rig, make, sweep, morph, materials):
    shape=lambda p: morph(p,race)
    cloth=materials['cloth']; wool=materials['trousers']; leather=materials['leather']
    seam=materials['seam']; hair=materials['hair']; brass=materials['brass']
    made=[]

    def piping(name,points,radius=.0025,mat=seam,bone=None):
        return sweep(name,[shape(p) for p in points],[radius]*len(points),mat,bone,6)

    family='mire_brutish_v1_m' if race=='greenskin' else 'civic_humanoid_v2_f' if kind in ('empire_herbalist','dark_elf_supply_officer') else 'civic_humanoid_v2_m'
    garments(family,race,make,morph,materials)
    for side in [-1,1]:
        # Boot uppers are separately shaped around ankle, heel, vamp and toe box.
        x=side*.216
        outline=[(-.063,.049),(-.071,.017),(-.070,-.071),(-.068,-.165),(-.057,-.224),
                 (-.029,-.247),(.022,-.248),(.057,-.228),(.073,-.172),(.072,-.064),(.066,.020),(.055,.049)]
        verts=[]
        sections=[(.018,1,.0),(.032,1.025,.0),(.054,1,.0),(.071,.95,.0),(.112,.88,.02)]
        for z,scale,dy in sections:
            for px,py in outline:verts.append(shape((x+px*scale,py*scale+dy,z)))
        # The vamp rises back to the ankle without shaping individual toes.
        for z,rx,ry,cy in [(.155,.066,.065,-.013),(.215,.067,.061,-.008),(.285,.069,.06,-.008),(.304,.072,.063,-.008)]:
            for px,py in outline:
                a=math.atan2(py+.06,px)
                verts.append(shape((x+rx*math.cos(a),cy+ry*math.sin(a),z)))
        faces=[(r*12+i,r*12+(i+1)%12,(r+1)*12+(i+1)%12,(r+1)*12+i) for r in range(8) for i in range(12)]
        faces.append(tuple(reversed(range(12))))
        bone_side='L' if side>0 else 'R'
        boot_weights=[]
        for p in verts:
            t=max(0,min(1,(p.z-shape((0,0,.12)).z)/(shape((0,0,.27)).z-shape((0,0,.12)).z)))
            t=t*t*(3-2*t)
            boot_weights.append([('foot_'+bone_side,1-t),('shin_'+bone_side,t)])
        boot=make('fitted_boot_'+str(side),verts,faces,leather,custom_weights=boot_weights)
        smooth=boot.modifiers.new('Boot_last_finish','SUBSURF');smooth.levels=2;smooth.render_levels=2
        solid=boot.modifiers.new('Boot_upper_thickness','SOLIDIFY');solid.thickness=.006
        piping('welt_stitch_'+str(side),[(x+px*1.02,py*1.02,.047) for px,py in outline+[outline[0]]],.002,materials['seam'])
        for z in [.18,.21,.24,.27]:
            for direction in [-1,1]:
                piping('crossed_boot_lace',[(x+direction*.032,-.071,z),(x-direction*.028,-.074,z+.018)],.0023,leather)
    # Sew closures onto the evaluated shirt, so the placket cannot float through
    # a beard or apron when the torso proportions change.
    bpy.context.view_layer.update()
    shirt=next(o for o in bpy.context.scene.objects if 'shirt_continuous_tailored_surface' in o.name)
    tree=BVHTree.FromObject(shirt,bpy.context.evaluated_depsgraph_get())
    def on_shirt(x,z,offset=.003):
        p=shape((x,0,z));hit=tree.ray_cast(Vector((p.x,-2,p.z)),Vector((0,1,0)))[0]
        if hit is None:hit=tree.find_nearest(Vector((p.x,-.10,p.z)))[0]
        return hit+Vector((0,-offset,0))
    for side in [-1,1]:
        points=[on_shirt(side*.014,z) for z in [1.30,1.38,1.46,1.52,1.565]]
        sweep('fitted_shirt_placket',points,[.004]*len(points),cloth)
    for z in [1.40,1.45,1.50]:
        for side in [-1,1]:
            sweep('fitted_placket_lace',[on_shirt(side*.018,z,.006),on_shirt(-side*.018,z+.022,.006)],[.0018,.0018],leather)

    if race=='dwarf':
        groom,head_shape,head_tree=build_head(make,morph,race)
        build_beard(make,head_shape,groom,head_tree)

    # Remove only covered anatomy; anatomical hand groups cannot become trouser fabric.
    covered=set()
    for face in body.data.polygons:
        p=sum((body.data.vertices[i].co for i in face.vertices),Vector())/len(face.vertices)
        if race=='dwarf' and p.z>shape((0,0,1.555)).z:
            covered.add(face.index);continue
        influence={}
        for index in face.vertices:
            for entry in body.data.vertices[index].groups:
                name=body.vertex_groups[entry.group].name
                influence[name]=influence.get(name,0)+entry.weight
        dominant=max(influence,key=influence.get)
        if any(part in dominant for part in ['index','middle','ring','pinky','thumb','hand']):continue
        if any(part in dominant for part in ['thigh','shin','foot','toe','hips']):covered.add(face.index);continue
        if 'forearm' in dominant or 'upper_arm' in dominant:
            side='L' if dominant.endswith('_L') else 'R'
            bone=rig.data.bones['forearm_'+side]; axis=bone.tail_local-bone.head_local
            # Retain overlap under the sleeve: a centroid cut can remove a face
            # whose distal corners are still outside the garment cuff.
            furthest=max((body.data.vertices[i].co-bone.head_local).dot(axis)/axis.length_squared for i in face.vertices)
            if furthest<.30:covered.add(face.index)
        elif p.z<shape((0,0,1.573)).z:covered.add(face.index)
    return covered
