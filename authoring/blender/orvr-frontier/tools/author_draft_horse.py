"""Original heavy draft-horse anatomy, fitted harness and weighted motion master.

The source is a set of deliberately shaped anatomical sections, inset facial
patches and explicit leather paths. It imports no body geometry or primitives.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import build_collection as build
import quadruped_rig as rigging

ASSET='frontier_draft_horse'
# Each section is (Y, dorsal Z, ventral Z, half breadth). Deliberate withers,
# croup, belly tuck, shoulder, throatlatch, cheek and tapered muzzle are retained.
BODY=[(1.14,1.43,1.11,.15),(1.04,1.60,.94,.28),(.84,1.67,.85,.38),(.53,1.63,.76,.41),
      (.12,1.60,.73,.43),(-.27,1.63,.79,.41),(-.58,1.75,.88,.36),(-.80,1.97,1.08,.285),
      (-.99,2.19,1.42,.215),(-1.13,2.28,1.70,.172),(-1.28,2.20,1.73,.165),
      (-1.43,2.025,1.58,.147),(-1.64,1.83,1.465,.125),(-1.81,1.735,1.435,.135),(-1.91,1.695,1.465,.12)]
# A dorsal keel and full rib/flank profile, rather than an elliptical torso.
SECTION=[(0,1),(.42,.97),(.79,.81),(.96,.58),(1,.25),(.94,-.14),(.75,-.59),(.38,-.91),
         (0,-1),(-.38,-.91),(-.75,-.59),(-.94,-.14),(-1,.25),(-.96,.58),(-.79,.81),(-.42,.97)]
FRONT=[(-.60,1.64,.125,.22),(-.62,1.26,.145,.18),(-.65,1.04,.108,.14),(-.72,.91,.081,.108),
       (-.77,.78,.081,.105),(-.78,.67,.07,.080),(-.78,.42,.062,.068),(-.78,.25,.093,.084),
       (-.85,.14,.083,.084),(-.90,.10,.083,.097)]
HIND=[(.72,1.64,.15,.22),(.64,1.27,.18,.24),(.48,1.06,.15,.17),(.73,.86,.093,.15),
      (.94,.63,.081,.112),(.97,.53,.075,.097),(.90,.35,.065,.075),(.87,.23,.091,.082),
      (.80,.13,.087,.090),(.77,.10,.086,.10)]


def mesh(name,vertices,faces,material):
    data=bpy.data.meshes.new(name+'.authored_cage');data.from_pydata(vertices,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    data.materials.append(material)
    for face in data.polygons:face.use_smooth=True
    obj['source_policy']='Original individually shaped anatomical sections and explicit fitted construction paths; no primitive mesh'
    return obj


def loft(name,rings,material,cap=True,closed=False):
    count=len(rings[0]);vertices=[p for row in rings for p in row]
    faces=[[row*count+i,row*count+(i+1)%count,(row+1)*count+(i+1)%count,(row+1)*count+i]
           for row in range(len(rings)-1) for i in range(count)]
    if closed:faces += [[len(vertices)-count+i,len(vertices)-count+(i+1)%count,(i+1)%count,i] for i in range(count)]
    if cap:faces += [list(reversed(range(count))),list(range(len(vertices)-count,len(vertices)))]
    return mesh(name,vertices,faces,material)


def smooth(obj,levels=2):
    mod=obj.modifiers.new('retained_anatomical_surface','SUBSURF');mod.levels=levels;mod.render_levels=levels
    return obj


def material(name,color,roughness=.65,metallic=0):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=roughness;shader.inputs['Metallic'].default_value=metallic
    mat.diffuse_color=(*color,1)
    return mat


def horse_coat():
    mat=material('draft.bay_coat',(.16,.058,.026),.72);tree=mat.node_tree;shader=tree.nodes.get('Principled BSDF')
    coords=tree.nodes.new('ShaderNodeTexCoord');noise=tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=7.2;noise.inputs['Detail'].default_value=3.2
    tree.links.new(coords.outputs['Object'],noise.inputs['Vector'])
    ramp=tree.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.1;ramp.color_ramp.elements[0].color=(.043,.013,.005,1)
    ramp.color_ramp.elements[1].position=.85;ramp.color_ramp.elements[1].color=(.065,.023,.009,1)
    tree.links.new(noise.outputs['Fac'],ramp.inputs['Fac'])
    markings=tree.nodes.new('ShaderNodeVertexColor');markings.layer_name='coat_markings'
    hair_scale=tree.nodes.new('ShaderNodeVectorMath');hair_scale.operation='MULTIPLY';hair_scale.inputs[1].default_value=(120,13,170)
    tree.links.new(coords.outputs['Object'],hair_scale.inputs[0])
    hair_noise=tree.nodes.new('ShaderNodeTexNoise');hair_noise.inputs['Scale'].default_value=1;hair_noise.inputs['Detail'].default_value=2.0
    tree.links.new(hair_scale.outputs['Vector'],hair_noise.inputs['Vector'])
    hair_tone=tree.nodes.new('ShaderNodeMapRange');hair_tone.inputs['To Min'].default_value=.80;hair_tone.inputs['To Max'].default_value=1.09
    tree.links.new(hair_noise.outputs['Fac'],hair_tone.inputs['Value'])
    multiply=tree.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
    tree.links.new(markings.outputs['Color'],multiply.inputs[1]);tree.links.new(hair_tone.outputs['Result'],multiply.inputs[2])
    tree.links.new(multiply.outputs[0],shader.inputs['Base Color'])
    coat_sheen=tree.nodes.new('ShaderNodeMapRange');coat_sheen.inputs['To Min'].default_value=.52;coat_sheen.inputs['To Max'].default_value=.75
    tree.links.new(hair_noise.outputs['Fac'],coat_sheen.inputs['Value']);tree.links.new(coat_sheen.outputs['Result'],shader.inputs['Roughness'])
    grain=tree.nodes.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=430;grain.inputs['Roughness'].default_value=.62
    tree.links.new(coords.outputs['Object'],grain.inputs['Vector'])
    bump=tree.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00065;bump.inputs['Strength'].default_value=.3
    tree.links.new(grain.outputs['Fac'],bump.inputs['Height']);tree.links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    return mat


def tube(name,points,material,radius=.016):
    section=[(1,0),(.71,.71),(0,1),(-.71,.71),(-1,0),(-.71,-.71),(0,-1),(.71,-.71)]
    closed=points[0]==points[-1]
    if closed:points=points[:-1]
    rings=[]
    for index,p in enumerate(points):
        tangent=(Vector(points[(index+1)%len(points) if closed else min(index+1,len(points)-1)])-Vector(points[(index-1)%len(points) if closed else max(0,index-1)])).normalized()
        axis=Vector((0,0,1)) if abs(tangent.z)<.8 else Vector((0,1,0))
        u=tangent.cross(axis).normalized();v=tangent.cross(u).normalized()
        rings.append([Vector(p)+radius*(a*u+b*v) for a,b in section])
    return smooth(loft(name,rings,material,cap=not closed,closed=closed),1)


def strap(name,points,material,width=.05,broad_axis=None):
    """Retained leather mid-surface receives smooth fitted curvature and thickness."""
    vertices=[]
    for i,p in enumerate(points):
        tangent=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized()
        axis=Vector(broad_axis) if broad_axis else Vector((0,0,1)) if abs(tangent.z)<.8 else Vector((1,0,0))
        broad=(axis-tangent*axis.dot(tangent)).normalized()
        vertices.extend([Vector(p)-broad*width/2,Vector(p)+broad*width/2])
    obj=smooth(mesh(name,vertices,[[i,i+1,i+3,i+2] for i in range(0,len(vertices)-2,2)],material),2)
    solid=obj.modifiers.new('retained_leather_thickness','SOLIDIFY');solid.thickness=.008;solid.offset=0
    return obj


def anatomy():
    coat=horse_coat();hoof=material('draft.horn_hoof',(.055,.047,.039),.57)
    dark=material('draft.muzzle_skin',(.032,.025,.022),.69);hair=material('draft.black_mane',(.004,.003,.002),.79)
    eye=material('draft.brown_eye',(.009,.004,.002),.24);lid=material('draft.lid_skin',(.033,.016,.008),.70)
    leather=material('draft.worn_harness',(.029,.014,.006),.65);padding=material('draft.collar_padding',(.053,.027,.012),.82)
    iron=material('draft.harness_iron',(.12,.125,.13),.38,.87);brass=material('draft.buckles',(.32,.21,.073),.41,.84)
    for mat in (leather,padding):
        tree=mat.node_tree;shader=tree.nodes.get('Principled BSDF');grain=tree.nodes.new('ShaderNodeTexNoise')
        grain.inputs['Scale'].default_value=190;grain.inputs['Detail'].default_value=2.5
        bump=tree.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00055;bump.inputs['Strength'].default_value=.35
        tree.links.new(grain.outputs['Fac'],bump.inputs['Height']);tree.links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    objects=[]
    rings=[[(sx*breadth,y,(top+bottom)/2+sz*(top-bottom)/2) for sx,sz in SECTION] for y,top,bottom,breadth in BODY]
    body=smooth(loft('draft_continuous_body_neck_head',rings,coat),2);body['skin_region']='torso';objects.append(body)
    for side in (-1,1):
        for front,stations in [(True,FRONT),(False,HIND)]:
            name=('front' if front else 'hind')+('_L' if side<0 else '_R')
            rings=[]
            for y,z,rx,ry in stations:
                x=side*((.315 if front else .33)-(.105 if front else .085)*max(0,(z-1.12)/.5))
                rings.append([(x+sx*rx,y+sy*ry,z) for sx,sy in SECTION])
            leg=smooth(loft('draft_'+name+'_anatomy',rings,coat),2);leg['skin_region']=name;objects.append(leg)
            y=stations[-1][0]
            # The horn capsule flares toward its toe, with an inclined coronet,
            # rounded heel bulbs and a separate slightly hollow sole.
            outline=[(0,-1),(.65,-.91),(1,-.48),(1,.30),(.72,.80),(.29,.92),(-.29,.92),(-.72,.80),(-1,.30),(-1,-.48),(-.65,-.91)]
            rings=[[(side*(.315 if front else .33)+sx*rx,y+sy*ry+dy,z) for sx,sy in outline]
                   for z,rx,ry,dy in [(0.018,.107,.142,-.026),(.035,.113,.143,-.028),(.11,.102,.126,-.01),(.17,.076,.095,.012)]]
            foot=smooth(loft('draft_'+name+'_hoof',rings,hoof),1);foot['skin_region']=name;objects.append(foot)
        # Original folded ear cups; each has a concave interior and pinched tip.
        ear_points=[(side*.072,-1.09,2.15),(side*.15,-1.045,2.22),(side*.19,-1.035,2.36),
                    (side*.16,-1.06,2.45),(side*.105,-1.095,2.38),(side*.055,-1.125,2.23),(side*.118,-1.095,2.28),
                    (side*.08,-1.04,2.15),(side*.155,-.992,2.23),(side*.192,-1.00,2.36),
                    (side*.16,-1.04,2.45),(side*.106,-1.052,2.38),(side*.06,-1.075,2.23)]
        faces=[[i,(i+1)%6,6] for i in range(6)]+[[7,12,11,10,9,8]]+[[i,(i+1)%6,(i+1)%6+7,i+7] for i in range(6)]
        ear=smooth(mesh('draft_ear_'+str(side),ear_points,faces,coat),2);ear['skin_region']='ear_L' if side<0 else 'ear_R';objects.append(ear)
        for prefix,y,z,width,height,mat in [('eye',-1.335,1.958,.072,.048,eye),('nostril',-1.818,1.568,.067,.044,dark)]:
            outline=[(-1,0),(-.63,.67),(0,.95),(.65,.56),(1,-.11),(.48,-.72),(-.35,-.85)]
            x=side*(.161 if prefix=='eye' else .124)
            vertices=[(x,y+a*width,z+b*height) for a,b in outline]+[(x+side*.016,y,z)]
            patch=smooth(mesh(f'draft_{prefix}_{side}',vertices,[[i,(i+1)%7,7] for i in range(7)],mat),2)
            solid=patch.modifiers.new('tissue_thickness','SOLIDIFY');solid.thickness=.006
            patch['skin_region']='head';objects.append(patch)
            rim=tube(f'draft_{prefix}_fold_{side}',[(x+side*.004,y+a*width,z+b*height) for a,b in outline+[outline[0]]],lid,.004 if prefix=='eye' else .006)
            rim['skin_region']='head';objects.append(rim)
    mouth=tube('draft_lower_lip',[(-.103,-1.81,1.52),(-.08,-1.865,1.51),(0,-1.885,1.508),(.08,-1.865,1.51),(.103,-1.81,1.52)],dark,.010)
    mouth['skin_region']='head';objects.append(mouth)
    # Combed mane locks are tapered, cambered hair surfaces with thickness; they
    # follow the neck's descending crest instead of a single opaque wedge.
    crest=[(-1.12,2.25),(-1.02,2.21),(-.91,2.12),(-.80,1.98),(-.69,1.85),(-.58,1.76)]
    mane_stations=[(a[0]+(b[0]-a[0])*t/5,a[1]+(b[1]-a[1])*t/5) for a,b in zip(crest,crest[1:]) for t in range(5)]
    for i,(y,z) in enumerate(mane_stations):
        length=.35+.040*math.sin(i*1.8)
        vertices=[(.008,y-.052,z),(.06,y-.052,z+.015),(.11,y-.028,z+.004),(.21,y+.024,z-.12),
                  (.255,y+.082,z-length+.035),(.245,y+.105,z-length),(.20,y+.086,z-length+.01),(.085,y+.048,z-.13)]
        vertices=[(x,y,z+.018) for x,y,z in vertices]
        lock=smooth(mesh('draft_mane_lock_'+str(i),vertices,[[0,1,2,3,4,5,6,7]],hair),2)
        solid=lock.modifiers.new('hair_lock_thickness','SOLIDIFY');solid.thickness=.006;lock['skin_region']='neck';objects.append(lock)
    for i in range(6):
        x=(i-2.5)*.026
        points=[(x-.024,-1.125,2.25),(x+.026,-1.12,2.25),(x+.034,-1.245,2.19),
                (x+.018,-1.38,2.08),(x-.005,-1.445,2.025),(x-.014,-1.385,2.08),(x-.032,-1.25,2.18)]
        forelock=smooth(mesh('draft_forelock_'+str(i),points,[[0,1,2,3,4,5,6]],hair),2)
        solid=forelock.modifiers.new('forelock_thickness','SOLIDIFY');solid.thickness=.006;forelock['skin_region']='head';objects.append(forelock)
    tail=tube('draft_tail_dock',[(0,1.04,1.49),(.01,1.20,1.36),(.02,1.29,1.12),(.015,1.33,.93)],coat,.045)
    tail['skin_region']='tail';objects.append(tail)
    tail_sections=[(1.37,1.21,.052,.024),(1.15,1.30,.088,.036),(.90,1.37,.106,.043),
        (.62,1.405,.111,.047),(.39,1.42,.090,.035),(.245,1.413,.061,.023)]
    rings=[[(sx*rx,y+sy*ry,z) for sx,sy in SECTION] for z,y,rx,ry in tail_sections]
    curtain=smooth(loft('draft_tail_hair_curtain',rings,hair),2);curtain['skin_region']='tail';objects.append(curtain)
    for i,offset in enumerate([-.10,-.082,-.064,-.046,-.028,-.01,.008,.026,.044,.062,.08,.098]):
        layer=(i%3)*.012
        lock=tube('draft_tail_lock_'+str(i),[(offset*.35,1.17+layer,1.40),(offset*.8,1.29+layer,1.10),(offset,1.37+layer,.83),
             (offset*1.15,1.40+layer,.58),(offset*.7,1.41+layer,.31),(offset*.4,1.40+layer,.20+abs(offset))],hair,.019)
        lock['skin_region']='tail';objects.append(lock)
    # Padded collar bears at the shoulders; hames and trace rings attach to it.
    collar=[(0,-.77,2.005),(.22,-.79,1.90),(.34,-.81,1.71),(.365,-.84,1.46),(.315,-.895,1.24),
            (.19,-.94,1.10),(0,-.96,1.07),(-.19,-.94,1.10),(-.315,-.895,1.24),(-.365,-.84,1.46),
            (-.34,-.81,1.71),(-.22,-.79,1.90),(0,-.77,2.005)]
    padded=tube('draft_padded_working_collar',collar,padding,.047);padded['skin_region']='chest';objects.append(padded)
    for side in (-1,1):
        hame=tube('draft_hame_'+str(side),[(side*.17,-.855,1.95),(side*.30,-.89,1.77),(side*.38,-.905,1.51),
             (side*.34,-.955,1.27),(side*.20,-1.015,1.115)],leather,.024);hame['skin_region']='chest';objects.append(hame)
        trace=strap('draft_trace_'+str(side),[(side*.40,-.92,1.33),(side*.48,-.46,1.16),(side*.53,.04,1.02),(side*.61,.28,.98)],leather,.06)
        trace['skin_region']='spine';objects.append(trace)
        ring=tube('draft_trace_ring_'+str(side),[(side*.43,-.86,1.36),(side*.48,-.86,1.39),(side*.52,-.86,1.35),
             (side*.50,-.86,1.30),(side*.45,-.86,1.29),(side*.43,-.86,1.36)],iron,.011);ring['skin_region']='chest';objects.append(ring)
        cheek=strap('draft_bridle_cheek_'+str(side),[(side*.115,-1.12,2.12),(side*.18,-1.26,1.965),(side*.18,-1.49,1.73),(side*.138,-1.76,1.54)],leather,.025)
        cheek['skin_region']='head';objects.append(cheek)
        shaft_loop=tube('draft_shaft_tug_'+str(side),[(side*.61,.20,.99),(side*.69,.23,.99),(side*.715,.28,.99),
            (side*.69,.34,.99),(side*.61,.36,.99),(side*.565,.30,.99),(side*.57,.245,.99),(side*.61,.20,.99)],leather,.016)
        shaft_loop['skin_region']='spine';objects.append(shaft_loop)
        tug=strap('draft_tug_support_'+str(side),[(side*.28,-.08,1.53),(side*.46,.0,1.39),(side*.52,.15,1.20),(side*.61,.28,.99)],leather,.048)
        tug['skin_region']='spine';objects.append(tug)
    saddle=strap('draft_harness_saddle',[(-.43,-.08,1.32),(-.365,-.08,1.50),(-.19,-.08,1.615),(0,-.08,1.64),
        (.19,-.08,1.615),(.365,-.08,1.50),(.43,-.08,1.32)],leather,.15,(0,1,0))
    saddle['skin_region']='spine';objects.append(saddle)
    girth=strap('draft_girth',[(-.43,-.08,1.32),(-.445,-.08,1.11),(-.38,-.08,.88),(-.20,-.08,.735),(0,-.08,.71),
        (.20,-.08,.735),(.38,-.08,.88),(.445,-.08,1.11),(.43,-.08,1.32)],leather,.07,(0,1,0))
    girth['skin_region']='spine';objects.append(girth)
    breeching=strap('draft_breeching',[(-.58,.25,1.04),(-.47,.72,1.05),(-.37,1.03,1.10),(-.18,1.19,1.13),
        (0,1.22,1.14),(.18,1.19,1.13),(.37,1.03,1.10),(.47,.72,1.05),(.58,.25,1.04)],leather,.065)
    breeching['skin_region']='pelvis';objects.append(breeching)
    for side in (-1,1):
        hip=strap('draft_hip_strap_'+str(side),[(side*.29,-.08,1.54),(side*.31,.30,1.56),(side*.32,.72,1.55),(side*.39,1.035,1.17)],leather,.033)
        hip['skin_region']='pelvis';objects.append(hip)
        for label,x,y,z in [('girth',.448,-.08,1.29),('tug',.552,.19,1.105),('trace',.535,.045,1.055)]:
            outline=[(side*x,y-.027,z-.044),(side*x,y+.021,z-.044),(side*x,y+.03,z-.030),
                (side*x,y+.03,z+.031),(side*x,y+.018,z+.045),(side*x,y-.018,z+.045),
                (side*x,y-.03,z+.028),(side*x,y-.03,z-.03),(side*x,y-.027,z-.044)]
            buckle=tube('draft_'+label+'_buckle_'+str(side),outline,brass,.0065);buckle['skin_region']='spine';objects.append(buckle)
            tongue=tube('draft_'+label+'_buckle_pin_'+str(side),[(side*(x+.004),y,z-.04),(side*(x+.005),y,z),
                (side*(x+.008),y+.016,z+.033)],iron,.0035);tongue['skin_region']='spine';objects.append(tongue)
    nose=strap('draft_noseband',[(-.133,-1.70,1.63),(-.09,-1.755,1.71),(0,-1.77,1.73),(.09,-1.755,1.71),(.133,-1.70,1.63)],leather,.04,(0,1,0))
    nose['skin_region']='head';objects.append(nose)
    # Hardware references remain explicitly named for the caravan's fitted shafts.
    for side in (-1,1):
        obj=bpy.data.objects.new('hitch_shaft_'+('left' if side<0 else 'right'),None);bpy.context.scene.collection.objects.link(obj)
        obj.location=(side*.61,.28,.98);obj['contract']='metres, Blender Z-up; external wagon shaft end, source wagon origin offset Y=-3.75'
    # Unite the original overlapping shoulder/thigh construction patches into
    # one deforming skin. The explicit control cages stay editable in the master.
    patches=[obj for obj in objects if obj==body or obj.name.endswith('_anatomy')]
    joined=build.evaluated_join(patches,'draft_continuous_skin')
    bpy.context.view_layer.objects.active=joined
    remesh=joined.modifiers.new('continuous_anatomical_skin','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.012
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    relax=joined.modifiers.new('skin_transition_relaxation','SMOOTH');relax.factor=.65;relax.iterations=9
    bpy.ops.object.modifier_apply(modifier=relax.name)
    for face in joined.data.polygons:face.use_smooth=True
    for vertex in joined.data.vertices:
        x,y,z=vertex.co
        # Retained anatomical landmark adjustments: cheek mass, eye socket and
        # the shallow jaw groove beneath the cheek. Symmetric, localized edits.
        if y < -.95 and abs(x)>.045:
            cheek=.014*math.exp(-((y+1.32)/.16)**2-((z-1.82)/.12)**2)
            socket=.007*math.exp(-((y+1.33)/.10)**2-((z-1.963)/.06)**2)
            jaw=.008*math.exp(-((y+1.17)/.09)**2-((z-1.75)/.13)**2)
            vertex.co.x+=(1 if x>0 else -1)*(cheek-socket-jaw)
    for obj in patches:obj.hide_render=True;obj.hide_set(True)
    objects=[obj for obj in objects if obj not in patches]+[joined]
    joined['skin_region']='continuous_body';joined['source_policy']='Continuous remesh of original anatomical control cages retained in this master'
    bpy.context.view_layer.update()
    # Fit facial tissue to the actual finished anatomical skin, retaining the
    # raised cornea and eyelid thickness instead of hiding the eye inside it.
    surface=joined.evaluated_get(bpy.context.evaluated_depsgraph_get())
    for obj in objects:
        if obj.name.startswith(('draft_mane_lock_','draft_forelock_','draft_bridle_cheek_','draft_hip_strap_')) or obj.name in ('draft_harness_saddle','draft_girth','draft_noseband'):
            wrap=obj.modifiers.new('fitted_finished_surface','SHRINKWRAP');wrap.target=joined
            wrap.wrap_method='NEAREST_SURFACEPOINT';wrap.wrap_mode='ABOVE_SURFACE';wrap.offset=.009
            solid_index=next((i for i,modifier in enumerate(obj.modifiers) if modifier.type=='SOLIDIFY'),len(obj.modifiers)-1)
            obj.modifiers.move(len(obj.modifiers)-1,solid_index)
        if obj.name in ('draft_harness_saddle','draft_girth') or obj.name.startswith('draft_hip_strap_'):
            for vertex in obj.data.vertices:
                center=vertex.co
                origin=Vector((0,center.y,1.16));radial=Vector((center.x,0,center.z-1.16)).normalized()
                found,location,_,_=surface.ray_cast(origin+radial*2,-radial)
                if found:
                    vertex.co=location+radial*.018
        if obj.name=='draft_padded_working_collar' or obj.name.startswith('draft_hame_'):
            for start in range(0,len(obj.data.vertices),8):
                ring=list(obj.data.vertices)[start:start+8]
                center=sum((vertex.co for vertex in ring),Vector())/len(ring)
                origin=Vector((0,center.y,1.47));radial=Vector((center.x,0,center.z-1.47)).normalized()
                found,location,_,_=surface.ray_cast(origin+radial*2,-radial)
                if found:
                    radius=.047 if obj.name=='draft_padded_working_collar' else .024
                    delta=location+radial*(radius+.012)-center
                    for vertex in ring:vertex.co+=delta
        if obj.name.startswith(('draft_eye_','draft_nostril_','draft_bridle_cheek_')):
            side=-1 if obj.name.endswith('-1') else 1
            for vertex in obj.data.vertices:
                found,location,_,_=surface.ray_cast(Vector((side*3,vertex.co.y,vertex.co.z)),Vector((-side,0,0)))
                if found:
                    lift=.005 if '_fold_' in obj.name else .010 if 'bridle' in obj.name else (.016 if 'eye' in obj.name else .001) if vertex.index==7 else .006
                    vertex.co.x=location.x+side*lift
        if obj.name=='draft_lower_lip':
            for vertex in obj.data.vertices:
                found,location,_,_=surface.ray_cast(Vector((vertex.co.x,-3,vertex.co.z)),Vector((0,1,0)))
                if found and abs(location.y-vertex.co.y)<.18:vertex.co.y=location.y-.006
    for obj in objects:
        if coat in list(obj.data.materials):
            colors=obj.data.color_attributes.new(name='coat_markings',type='FLOAT_COLOR',domain='POINT')
            for vertex,color in zip(obj.data.vertices,colors.data):
                x,y,z=vertex.co
                shade=.92+.08*math.sin(y*3+z*2)
                c=[.054*shade,.018*shade,.0065*shade]
                dark_mix=max(max(0,min(1,(.51-z)/.075)),max(0,min(1,(-1.68-y)/.12)))
                c=[v*(1-.70*dark_mix) for v in c]
                # One narrow irregular forehead stripe and one front-left sock.
                if y<-1.19 and y>-1.75 and z>1.65:
                    stripe=max(0,min(1,(.025+.006*math.sin(y*17)-abs(x))/.014))
                    c=[v*(1-stripe)+target*stripe for v,target in zip(c,(.40,.355,.27))]
                if x<-.2 and -.99<y<-.52 and z<.29+.015*math.sin(y*16):c=[.35,.31,.245]
                color.color=(*c,1)
    return objects


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true')
    parser.add_argument('--no-render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objects=anatomy()
    for image in bpy.data.images:
        if image.source=='FILE':image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'masters'/f'{ASSET}_anatomy.blend'))
    if args.no_render:return
    build.set_view(objects,ROOT/'review'/f'{ASSET}_anatomy.png')
    scene=bpy.context.scene;camera=scene.camera;centre=Vector((0,-.25,1.18))
    camera.location=centre+Vector((7,0,0));camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=4.15;scene.render.filepath=str(ROOT/'review'/f'{ASSET}_profile.png');bpy.ops.render.render(write_still=True)
    print('DRAFT_HORSE_ANATOMY_REVIEW_PENDING',flush=True)


if __name__=='__main__':main()
