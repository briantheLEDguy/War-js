"""Crownwatch furnishing masters and three true LODs, authored in Blender Z-up.

The camera-facing side is Blender -Y / glTF +Z. Every object is grounded and
scaled to its declared envelope. The retained masters keep separate carved,
forged, folded and assembled components; only delivery meshes are joined.
"""
import bpy
import json
import math
import hashlib
import sys
import numpy as np
from pathlib import Path
from mathutils import Vector

WORK = Path(__file__).resolve().parents[1]
for folder in ['sources', 'runtime', 'review', 'textures']:
    (WORK / folder).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
M = {}


def image_file(name, rgb, noncolor=False):
    p = WORK / 'textures' / (name + '.png')
    if not p.exists():
        h, w = rgb.shape[:2]
        im = bpy.data.images.new(name, width=w, height=h, alpha=True)
        rgba = np.ones((h, w, 4), dtype=np.float32)
        rgba[:, :, :3] = rgb
        im.pixels.foreach_set(rgba.ravel())
        im.filepath_raw = str(p)
        im.file_format = 'PNG'
        im.save()
        bpy.data.images.remove(im)
    im = bpy.data.images.load(str(p), check_existing=True)
    if noncolor:
        im.colorspace_settings.name = 'Non-Color'
    return im


def surface(name, color, metallic, roughness, textured=True):
    mat = bpy.data.materials.new('aegis_citadel_' + name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if textured:
        n = 2048
        y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
        rng = np.random.default_rng(100 + len(M))
        grit = rng.normal(0, .027, (n, n)).astype(np.float32)
        if name == 'oak':
            grain = np.sin(x*1450 + 10*np.sin(y*18) + 4*np.sin(y*67))
            h = .50 + .10*grain + .045*np.sin(x*307+y*2) + grit
        elif name == 'wine':
            h = .5 + .10*np.sin(x*1800)*np.sin(y*1800) + .05*np.sin(x*800) + grit*.2
        elif name == 'stone':
            h = .5 + .13*np.sin(x*39+2*np.sin(y*23))*np.sin(y*47) + grit
        else:
            h = .5 + .025*np.sin(y*1600+x*24) + .07*np.sin(x*29)*np.sin(y*41) + grit
        shade = np.clip(.77 + h*.37, .65, 1.08)
        rgb = np.stack([np.clip(shade*c, 0, 1) for c in color], -1)
        base = nodes.new('ShaderNodeTexImage')
        base.image = image_file(name+'_baseColor', rgb)
        links.new(base.outputs['Color'], bsdf.inputs['Base Color'])
        rough = nodes.new('ShaderNodeTexImage')
        r = np.clip(roughness+(h-.5)*.25, .03, .98)
        rough.image = image_file(name+'_roughness', np.stack([r, r, r], -1), True)
        links.new(rough.outputs['Color'], bsdf.inputs['Roughness'])
        dy, dx = np.gradient(h)
        normal = np.stack([-dx*2, -dy*2, np.ones_like(h)], -1)
        normal /= np.linalg.norm(normal, axis=2)[:, :, None]
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = image_file(name+'_normal', normal*.5+.5, True)
        nm = nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = .30
        links.new(tex.outputs['Color'], nm.inputs['Color'])
        links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    M[name] = mat
    return mat


for row in [('stone', (.32,.35,.34),0,.83), ('oak',(.19,.08,.03),0,.58),
            ('iron',(.045,.065,.07),.78,.37), ('brass',(.57,.34,.12),.72,.30),
            ('wine',(.30,.026,.048),0,.79)]:
    surface(*row)
surface('ivory',(.72,.63,.44),0,.54,False)
surface('teal',(.025,.18,.17),.35,.36,False)
surface('glow',(1,.33,.045),0,.55,False)
bs = M['glow'].node_tree.nodes.get('Principled BSDF')
bs.inputs['Emission Color'].default_value = (1,.20,.025,1)
bs.inputs['Emission Strength'].default_value = 2
surface('glass',(.24,.36,.34),.12,.10,False)
bs = M['glass'].node_tree.nodes.get('Principled BSDF')
bs.inputs['Alpha'].default_value = .14
M['glass'].surface_render_method = 'DITHERED'


def finish(ob, name, mat, bevel=0):
    ob.name = name
    ob.data.materials.append(M[mat])
    if bevel:
        mod = ob.modifiers.new('hand_finished_edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    return ob


def box(name, pos, size, mat='oak', bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    ob = bpy.context.object
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(ob, name, mat, bevel)


def cyl(name, pos, radius, depth, mat='brass', r2=None, sides=12, bevel=.008):
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=radius,
        radius2=radius if r2 is None else r2, depth=depth, location=pos)
    ob=bpy.context.object
    for polygon in ob.data.polygons:
        polygon.use_smooth=len(polygon.vertices)==4
    return finish(ob, name, mat, bevel)


def ball(name, pos, radius, mat='brass', scale=(1,1,1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=radius, location=pos)
    ob=bpy.context.object
    ob.scale=scale
    for polygon in ob.data.polygons:polygon.use_smooth=True
    return finish(ob,name,mat)


def mesh(name, verts, faces, mat, bevel=0):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces)
    data.update()
    ob=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(ob)
    return finish(ob,name,mat,bevel)


def path(name, points, radius=.025, mat='brass'):
    curve=bpy.data.curves.new(name,'CURVE')
    curve.dimensions='3D'
    curve.resolution_u=1
    curve.bevel_depth=radius
    curve.bevel_resolution=1
    s=curve.splines.new('POLY')
    s.points.add(len(points)-1)
    for p,v in zip(s.points,points): p.co=(*v,1)
    ob=bpy.data.objects.new(name,curve)
    bpy.context.collection.objects.link(ob)
    curve.materials.append(M[mat])
    return ob


def rod(name, a, b, radius=.06, mat='iron', r2=None):
    a,b=Vector(a),Vector(b)
    ob=cyl(name,(a+b)/2,radius,(b-a).length,mat,r2)
    ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return ob


def ring(name,pos,radius,tube=.025,mat='brass',vertical=False,steps=24,start=0,end=math.tau):
    x,y,z=pos
    return path(name,[(x+radius*math.cos(t),y if vertical else y+radius*math.sin(t),
        z+radius*math.sin(t) if vertical else z)
        for t in [start+(end-start)*i/steps for i in range(steps+1)]],tube,mat)


def shield(name,x,y,z,w=1,h=1.5,mat='iron',crest=True):
    # Convex forged shield: actual pitched face, pointed lower edge, raised rim.
    edge=[(-.5,.48),(.5,.48),(.48,-.13),(0,-.55),(-.48,-.13)]
    verts=[(x+a*w,y,z+b*h) for a,b in edge]+[(x,y-.12*w,z)]
    ob=mesh(name,verts,[(i,(i+1)%5,5) for i in range(5)],mat)
    solid=ob.modifiers.new('forged_plate_thickness','SOLIDIFY');solid.thickness=.035*w
    path(name+'_rolled_rim',[(x+a*w,y-.014,z+b*h) for a,b in edge+[edge[0]]],.035*w,'brass')
    if crest:
        # Original three peoples: mountain, upright hearth, bifurcated leaf.
        for i,side in enumerate([-1,0,1]):
            px=x+side*.25*w
            if side==-1:
                path('mountain_oath',[(px-.10*w,y-.15*w,z),(px,y-.15*w,z+.17*h),(px+.10*w,y-.15*w,z)],.025*w,'ivory')
            elif side==0:
                box('hearth_oath',(px,y-.14*w,z+.06*h),(.07*w,.035*w,.30*h),'ivory',.008)
            else:
                path('leaf_oath',[(px-.09*w,y-.15*w,z+.20*h),(px,y-.15*w,z+.05*h),(px+.09*w,y-.15*w,z+.20*h)],.022*w,'ivory')
    return ob


def sword(x,y,z,size=1):
    # Diamond-section blade and fuller; down-facing tip below the guard.
    w=.20*size; h=2.0*size
    mesh('tempered_diamond_blade',[(x-w,y,z),(x,y-.05*size,z),(x+w,y,z),(x,y+.05*size,z),
        (x,y,z-h)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(0,3,2,1)],'iron')
    path('blade_fuller',[(x,y-.054*size,z-.12*size),(x,y-.025*size,z-h*.77)],.012*size,'brass')
    path('upswept_crossguard',[(x-.46*size,y,z-.04*size),(x-.30*size,y,z+.10*size),
        (x+.30*size,y,z+.10*size),(x+.46*size,y,z-.04*size)],.065*size,'brass')
    cyl('leather_grip',(x,y,z+.34*size),.075*size,.53*size,'oak')
    for i in range(6): ring('grip_binding',(x,y,z+(.12+i*.08)*size),.078*size,.008*size,'brass',steps=12)
    ball('pommel',(x,y,z+.67*size),.14*size)


def cloth(name, center, width, height, mat='wine', vertical=False, folds=5, drape=.10):
    x,y,z=center; nx=28;ny=12
    verts=[];faces=[]
    for j in range(ny+1):
        v=j/ny
        for i in range(nx+1):
            u=i/nx;wav=math.sin(u*math.tau*folds)*drape
            verts.append((x+(u-.5)*width,y+wav if vertical else y+(v-.5)*height,
                z+(v-.5)*height if vertical else z+wav+drape*.5*math.sin(v*math.tau)))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    ob=mesh(name,verts,faces,mat)
    for polygon in ob.data.polygons:polygon.use_smooth=True
    so=ob.modifiers.new('woven_edge','SOLIDIFY');so.thickness=.014
    return ob


def scroll(x,y,z,scale=1,open=False):
    if open:
        box('unfurled_parchment',(x,y,z),(.9*scale,.65*scale,.014),'ivory',.012)
        for s in [-1,1]:
            ob=cyl('scroll_roll',(x+s*.46*scale,y,z+.07*scale),.09*scale,.70*scale,'ivory')
            ob.rotation_euler.x=math.pi/2
        for i in range(5):
            box('ink_ledger_line',(x,y+(.2-i*.09)*scale,z+.010),(.54*scale,.014*scale,.004),'iron',0)
    else:
        ob=cyl('sealed_scroll',(x,y,z),.11*scale,.8*scale,'ivory')
        ob.rotation_euler.y=math.pi/2
        box('scroll_ribbon',(x,y,z),(.075*scale,.235*scale,.235*scale),'wine',.007)


def chest(x,y,z,w=1.7,d=1.1,h=1.0):
    box('treasury_chest_body',(x,y,z+h*.45),(w,d,h*.9),'oak',.035)
    # Curved stave lid, rather than a solid box cap.
    for i in range(7):
        angle=math.pi*(i+.5)/7
        zz=z+h*.82+math.sin(angle)*h*.25
        yy=y+math.cos(angle)*d*.45
        ob=box('arched_lid_stave',(x,yy,zz),(w,d*.22,h*.07),'oak',.012)
        ob.rotation_euler.x=angle-math.pi/2
    for side in [-1,1]:
        xx=x+side*w*.34
        box('chest_iron_strap',(xx,y-d*.51,z+h*.45),(.10,.06,h*.9),'iron',.01)
        path('arched_strap',[(xx,y+math.cos(t)*d*.49,z+h*.82+math.sin(t)*h*.28)
            for t in [math.pi*i/12 for i in range(13)]],.045,'iron')
        for zz in [.17,.48,.77]:ball('strap_rivet',(xx,y-d*.55,z+h*zz),.035)
    box('lockplate',(x,y-d*.54,z+h*.62),(.26,.07,.32),'brass',.025)
    ring('lock_ring',(x,y-d*.61,z+h*.64),.075,.022,'iron',True)


def barrel(x,y,z,r=.52,h=1.25):
    for i in range(12):
        a=math.tau*i/12
        verts=[]
        for k,(zz,rr) in enumerate([(0,r*.8),(.15*h,r*.97),(.5*h,r),(h*.85,r*.97),(h,r*.8)]):
            for da in [-.248,.248]:verts.append((x+rr*math.cos(a+da),y+rr*math.sin(a+da),z+zz))
        mesh('curved_oak_stave',verts,[(k*2,k*2+1,k*2+3,k*2+2) for k in range(4)],'oak')
    for zz,rr in [(.12*h,r*.96),(.3*h,r),(.74*h,r),(h*.9,r*.96)]:
        ring('forged_barrel_hoop',(x,y,z+zz),rr,.036,'iron',steps=24)
    cyl('barrel_lid',(x,y,z+h-.018),r*.81,.035,'oak',sides=16)
    cyl('barrel_bung',(x+r*.35,y,z+h+.015),r*.09,.04,'oak')


def table_frame(width,depth,height=1.1,mat='oak'):
    for x in [-width*.4,width*.4]:
        for y in [-depth*.34,depth*.34]:
            rod('splayed_table_leg',(x*1.08,y*1.12,.07),(x,y,height),.10,mat,.07)
    for i in range(6):
        box('tabletop_plank',(0,(i-2.5)*depth/6,height),(width,depth/6-.016,.14),mat,.025)
    rod('stretcher',(-width*.42,0,.35),(width*.42,0,.35),.11,'oak')


def throne():
    for i in range(4):
        box('ceremonial_dais',(0,i*.35,.1125+i*.225),(10-i*.7,8-i*.70,.225),'stone',.055)
    box('carved_oak_seat',(0,1.5,2.0),(3.5,2.2,.6),'oak',.12)
    box('wine_seat_cushion',(0,1.30,2.38),(3.15,1.85,.22),'wine',.13)
    box('high_throne_back',(0,2.5,4.05),(3.9,.5,4.5),'oak',.10)
    box('tufted_back_cloth',(0,2.18,4.15),(3.35,.16,3.35),'wine',.09)
    for z in [3.1,3.75,4.4,5.05]:
        for x in [-1.15,-.58,0,.58,1.15]:ball('backrest_tuft',(x,2.06,z),.055)
    for side in [-1,1]:
        x=side*2.1
        for y in [.65,2.6]:
            cyl('throne_leg',(x,y,1.45),.32,1.1,'oak',.23,sides=8)
            for z in [1.0,1.8]:cyl('gilded_leg_collar',(x,y,z),.35,.12)
        box('carved_arm',(x,1.5,2.88),(.52,2.55,.32),'oak',.12)
        ball('sentinel_arm_knuckle',(x,.30,2.95),.39,'brass',(1,1.2,.85))
        shield('arm_shield',x,.03,2.97,.42,.55,'iron')
        cyl('canopy_column',(side*3.3,2.65,4.8),.25,7.8,'stone',.19,sides=12)
        for i in range(8):
            a=i*math.pi/4
            rod('column_gilt_flute',(side*3.3+.22*math.cos(a),2.65+.22*math.sin(a),1.3),
                (side*3.3+.20*math.cos(a),2.65+.20*math.sin(a),8.4),.018,'brass')
        for z in [1,1.3,8.2,8.5]:cyl('column_capital',(side*3.3,2.65,z),.42,.16,'brass',sides=8)
        path('winged_canopy_ridge',[(side*.25,2.45,7.6),(side*1.6,2.45,8.2),
            (side*3.5,2.45,9.8),(side*4.1,2.45,8.8)],.11,'brass')
        for i in range(12):
            t=i/11;x0=side*(.6+3.1*t);zt=7.7+1.8*t
            tip=(x0+side*(.35+.5*t),2.15,zt-.95-1.6*t)
            verts=[(x0-.17,2.38,zt),(x0+.17,2.38,zt),(tip[0],tip[1],tip[2]),(x0,2.14,zt-.2)]
            mesh('carved_canopy_feather',verts,[(0,1,3),(1,2,3),(2,0,3)],'brass')
    shield('sovereigns_aegis',0,2.03,6.8,2.4,2.5,'iron')
    ring('oath_halo',(0,2.2,7.8),1.35,.07,'brass',True)
    for a in [i*math.pi/8 for i in range(9)]:
        rod('halo_ray',(1.30*math.cos(a),2.2,7.8+1.30*math.sin(a)),
            (1.85*math.cos(a),2.2,7.8+1.85*math.sin(a)),.045,'brass',.012)
    # Three carved back panels echo the united Empire, Dwarf and High Elf oath.
    for x in [-2.9,0,2.9]:
        shield('dais_oath_relief',x,-3.35,.65,.62,.52,'iron')


def oath_statue():
    for z,r,d in [(.2,2,.4),(.48,1.72,.17),(.9,1.48,.70),(1.30,1.65,.15)]:
        cyl('octagonal_oath_plinth',(0,0,z),r,d,'stone',sides=8)
    # Tapered sabatons, greaves and overlapping armour create a readable sentinel.
    for s in [-1,1]:
        box('sabatons',(s*.48,-.30,1.55),(.75,1.32,.40),'iron',.14)
        rod('greave',(s*.48,0,1.75),(s*.48,.02,3.12),.31,'iron',.25)
        ball('knee_cop',(s*.48,-.22,3.18),.36,'brass',(1,.55,1.15))
        rod('cuisses',(s*.48,.02,3.30),(s*.37,0,4.45),.35,'iron',.45)
    for i in range(4):
        cyl('overlapping_faulds',(0,0,3.95+i*.19),1.02-i*.06,.25,'iron',.85-i*.06,sides=8)
    mesh('breastplate',[(-.83,-.30,4.7),(.83,-.30,4.7),(-1.08,-.38,5.65),(1.08,-.38,5.65),
        (0,-.72,5.12),(-.85,.43,4.7),(.85,.43,4.7),(-1.1,.45,5.65),(1.1,.45,5.65)],
        [(0,1,4),(1,3,4),(3,2,4),(2,0,4),(5,7,8,6),(0,5,6,1),(2,3,8,7),(0,2,7,5),(1,6,8,3)],'iron',.04)
    shield('breast_oath',0,-.74,5.18,.85,.8,'brass',True)
    for s in [-1,1]:
        for i in range(3):
            ball('lamellar_pauldron',(s*(1.08+i*.08),0,5.47-i*.14),.52,'iron',(1,.96,.44))
        hand_height=4.55 if s>0 else 4.15
        rod('arm_vambrace',(s*1.27,-.02,5.18),(s*1.35,-.53,hand_height+.10),.24,'iron',.20)
        ball('gauntlet',(s*1.35,-.62,hand_height),.28,'brass',(.75,.85,1.1))
    cyl('gorget',(0,0,5.92),.45,.32,'brass',.35)
    ball('closed_helmet',(0,0,6.5),.67,'iron',(.82,.8,1.05))
    box('visored_face',(0,-.51,6.42),(.66,.15,.53),'iron',.055)
    for s in [-1,1]:box('visor_eye_slit',(s*.19,-.60,6.56),(.27,.035,.055),'stone',.01)
    rod('helmet_nasal',(0,-.61,6.75),(0,-.61,6.12),.045,'brass')
    for i in range(9):
        y=-.36+i*.09
        mesh('gilded_crest_fin',[(-.05,y,6.98),(.05,y,6.98),(.04,y,7.8-.35*abs(y)),(-.04,y,7.8-.35*abs(y))],[(0,1,2,3)],'brass')
    cloth('sentinels_folded_cloak',(0,.56,3.9),2.45,4.1,'wine',True,7,.10)
    shield('sentinels_great_shield',-1.15,-.85,3.75,1.7,2.7,'iron')
    sword(1.34,-.66,4.18,1.32)


def war_table():
    table_frame(6,4,1.18)
    box('map_sand_tray',(0,0,1.31),(5.6,3.6,.14),'brass',.025)
    box('campaign_parchment',(0,0,1.41),(5.3,3.3,.04),'ivory',.02)
    # Hand-carved terrain, settlements, bridge, military standards and route cord.
    for i in range(7):
        x=-1.9+i*.55;y=.65+.22*math.sin(i)
        cyl('map_mountain',(x,y,1.64),.35,.47,'stone',.03,sides=5)
    path('blue_river',[(-2.3,-.5,1.45),(-1.4,-.18,1.45),(-.4,-.6,1.45),(.6,-.16,1.45),(2.2,-.55,1.45)],.06,'teal')
    for x,y in [(-1.8,-1),(.15,.4),(1.7,-.8)]:
        box('miniature_keep',(x,y,1.60),(.30,.30,.3),'stone',.008)
        for dx in [-.2,.2]:cyl('miniature_tower',(x+dx,y,1.66),.065,.4,'stone',sides=6)
    for i in range(8):
        x=-2+i*.56;y=-.9 if i%2 else -.25
        cyl('regiment_token',(x,y,1.49),.13,.07,'wine' if i%2 else 'brass',sides=8)
        rod('standard_pin',(x,y,1.52),(x,y,1.92),.012,'iron')
        box('miniature_standard',(x+.10,y,1.85),(.17,.012,.13),'wine' if i%2 else 'ivory',0)
    scroll(-1.9,1.2,1.53,.75,True)
    scroll(2,1.17,1.55,.8)
    ring('map_compass',(1.9,-1.25,1.48),.20,.02,'brass')


def arms_rack():
    for x in [-2.35,2.35]:
        box('armoury_upright',(x,0,1.6),(.20,.45,3.2),'oak',.045)
        box('rack_foot',(x,0,.10),(.6,1.8,.2),'oak',.04)
        for z in [.45,2.9]:ball('forged_bolt',(x,-.26,z),.05)
    for z in [.4,2.3,3.05]:box('weapon_rail',(0,0,z),(4.9,.18,.22),'oak',.025)
    for i in range(7):
        x=-1.85+i*.61
        rod('ash_spear_shaft',(x,.22,.22),(x,.22,3.0),.032,'oak')
        mesh('leaf_spearhead',[(x,.22,3.5),(x-.13,.22,3.06),(x,.15,3.17),(x+.13,.22,3.06),(x,.29,3.17)],
            [(0,1,2),(0,2,3),(0,3,4),(0,4,1),(1,4,3,2)],'iron')
    for x in [-1.5,0,1.5]:shield('stacked_oath_shield',x,-.28,1.25,1.10,1.65,'iron')
    for x in [-.85,.85]:
        ball('spare_helmet',(x,-.08,2.65),.30,'iron',(1,.9,.85))
        box('helm_faceguard',(x,-.29,2.55),(.36,.12,.23),'brass',.025)


def provision_rack():
    for x in [-2.35,2.35]:
        for y in [-.75,.75]:box('stores_upright',(x,y,1.5),(.15,.15,3),'oak',.025)
    for z in [.12,1.52,2.78]:
        for y in [-.6,-.3,0,.3,.6]:box('shelf_plank',(0,y,z),(5,.27,.13),'oak',.02)
    for x in [-1.6,-.4]:barrel(x,0,.20,.50,1.25)
    for x,y,z in [(1.0,0,.70),(1.82,0,.63),(-1.65,0,2.1),(-.7,0,2.12)]:
        ball('tied_grain_sack',(x,y,z),.58,'ivory',(.78,.95,1))
        cyl('sack_neck',(x,y,z+.46),.13,.20,'ivory',.08)
        ring('sack_rope',(x,y,z+.44),.16,.022,'oak')
    for x in [.45,1.5]:
        for z in [1.82,2.24]:
            ob=cyl('rolled_wool_blanket',(x,0,z),.22,1.22,'wine',sides=14)
            ob.rotation_euler.x=math.pi/2
            ring('blanket_binding',(x,-.62,z),.23,.015,'ivory',True)
    scroll(0,-.81,2.81,.68,True)


def bunk():
    for x in [-1.3,1.3]:
        for y in [-2.24,2.24]:
            cyl('turned_bunk_post',(x,y,1.4),.12,2.8,'oak',sides=8)
            ball('bedpost_finial',(x,y,2.87),.14,'brass')
    for z in [.65,2.02]:
        for y in [-2.15,2.15]:box('bed_end_board',(0,y,z+.15),(2.70,.15,.45),'oak',.05)
        for x in [-1.26,1.26]:box('side_rail',(x,0,z),(.16,4.3,.25),'oak',.025)
        box('straw_mattress',(0,0,z+.12),(2.35,4.04,.27),'ivory',.10)
        cloth('folded_regimental_blanket',(0,-.35,z+.36),2.3,3.05,'wine',False,4,.06)
        box('bed_pillow',(0,1.43,z+.32),(1.45,.67,.18),'ivory',.11)
    for x in [.65,1.20]:rod('ladder_stile',(x,-2.42,.10),(x,-2.28,2.4),.045,'oak')
    for z in [.3,.7,1.1,1.5,1.9]:rod('ladder_rung',(.65,-2.40,z),(1.20,-2.40,z),.045,'oak')
    chest(-.3,-1.2,.03,1.2,.8,.42)


def hearth():
    box('hearthstone',(0,0,.15),(6,3,.3),'stone',.10)
    for side in [-1,1]:
        for row in range(6):
            box('fireplace_ashlar',(side*2.50,.1,.57+row*.53),(.95,2.1,.49),'stone',.045)
    box('fireback',(0,1.15,1.65),(4.2,.20,2.6),'iron',.04)
    box('mantel',(0,0,3.5),(5.9,2.7,.37),'stone',.09)
    mesh('tapered_smoke_hood',[(-2.7,-1.18,3.7),(2.7,-1.18,3.7),(2.7,1.15,3.7),(-2.7,1.15,3.7),
        (-1.35,-.40,5.85),(1.35,-.40,5.85),(1.35,1.15,5.85),(-1.35,1.15,5.85)],
        [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],'stone',.06)
    for x in [-1.6,-.8,0,.8,1.6]:
        rod('iron_grate_bar',(x,-.7,.45),(x,.85,.45),.065,'iron')
        rod('firewood',(x*.75,-.38,.58),(x*.75+.45,.35,.68),.15,'oak')
        ball('ember',(x*.82,-.1,.54),.17,'glow',(1.4,1,.45))
    for x in [-1.85,1.85]:rod('andirons',(x,-.8,.32),(x,-.8,1.18),.07,'iron')
    rod('cooking_bar',(-2.2,0,2.8),(2.2,0,2.8),.09,'iron')
    rod('kettle_chain',(0,0,2.8),(0,0,1.9),.03,'iron')
    ball('hanging_cauldron',(0,0,1.5),.63,'iron',(1,1,.8))
    ring('cauldron_lip',(0,0,1.75),.50,.07,'iron')
    ring('cauldron_handle',(0,0,1.9),.36,.025,'iron',True)
    shield('hearth_relief',0,-.85,4.40,1.15,1.3,'iron')


def feast_table():
    table_frame(7,1.8,1.08)
    for y in [-1.24,1.24]:
        box('trestle_bench_seat',(0,y,.56),(6.8,.46,.14),'oak',.04)
        for x in [-2.7,2.7]:box('bench_trestle',(x,y,.27),(.25,.54,.54),'oak',.035)
    cloth('wine_table_runner',(0,0,1.18),6.2,.42,'wine',False,2,.008)
    for x in [-2.6,-1.3,0,1.3,2.6]:
        for y in [-.60,.60]:
            cyl('pewter_plate',(x,y,1.19),.27,.034,'iron',sides=16)
            ring('plate_rim',(x,y,1.22),.24,.015,'brass',steps=16)
            cyl('earthen_cup',(x+.36,y*.80,1.35),.11,.29,'ivory',.13)
            ring('cup_handle',(x+.46,y*.80,1.34),.07,.014,'brass',True)
    for x in [-1.7,1.7]:
        ball('round_bread',(x,0,1.29),.28,'ivory',(1.5,.75,.43))
        for dx in [-.13,0,.13]:box('bread_score',(x+dx,0,1.405),(.025,.30,.012),'oak',.01)
    ball('communal_jug',(0,0,1.4),.21,'ivory',(1,1,1.25))
    cyl('jug_neck',(0,0,1.63),.10,.20,'ivory',.12)


def archive():
    for x in [-2.42,2.42]:box('archive_end',(x,0,2.4),(.16,1.5,4.8),'oak',.035)
    box('archive_back',(0,.67,2.4),(4.8,.16,4.8),'oak',.025)
    for z in [.12,1.15,2.15,3.15,4.2,4.9]:box('bookcase_shelf',(0,0,z),(5,1.5,.14),'oak',.025)
    for row in range(3):
        z=1.24+row*1.02
        if row==1:
            for x in [-1.8,-.9,0,.9,1.8]:
                box('scroll_pigeonhole',(x,.05,z+.36),(.08,1.35,.77),'oak',.012)
                for j in range(3):scroll(x+.16,-.05+j*.3,z+.17,.7)
        else:
            for i in range(15):
                x=-2.18+i*.31;h=.54+.28*((i*7)%5)/4
                mat=['wine','iron','teal','oak'][i%4]
                box('bound_codex',(x,-.07,z+h/2),(.24,1.0,h),mat,.018)
                for zz in [.10,h-.1]:box('gilt_book_band',(x,-.59,z+zz),(.245,.025,.035),'brass',.006)
    for x in [-1.75,-.58,.58,1.75]:
        box('locked_record_drawer',(x,-.10,.64),(1.09,1.20,.87),'oak',.025)
        box('drawer_label',(x,-.72,.77),(.52,.027,.16),'ivory',.006)
        ring('drawer_pull',(x,-.76,.51),.09,.02,'brass',True)
    for x in [-1.55,0,1.55]:shield('archive_crown',x,-.75,4.54,.72,.6,'iron')


def counting_desk():
    table_frame(4,2.5,1.10)
    for x in [-1.50,1.50]:
        box('desk_drawer_cabinet',(x,.1,.69),(.67,1.65,.66),'oak',.035)
        for z in [.48,.78]:
            box('drawer_front',(x,-.75,z),(.62,.07,.26),'oak',.022)
            ring('drawer_handle',(x,-.81,z),.07,.018,'brass',True)
    scroll(-.6,-.08,1.2,1.1,True)
    box('ledger_cover',(1.12,.25,1.25),(.78,1.04,.16),'wine',.025)
    for x in [.78,1.46]:box('ledger_metal_corner',(x,-.18,1.35),(.10,.18,.035),'brass',.012)
    rod('balance_pillar',(-1.22,.42,1.2),(-1.22,.42,1.96),.042,'brass')
    rod('balance_beam',(-1.81,.42,1.80),(-.63,.42,1.80),.035,'brass')
    for x in [-1.72,-.72]:
        for y in [.28,.57]:rod('scale_chain',(x,.42,1.78),(x,y,1.42),.012,'brass')
        cyl('scale_pan',(x,.42,1.41),.22,.035,'brass',sides=12)
    box('coin_counting_tray',(.72,-.72,1.22),(1.52,.49,.15),'oak',.015)
    for i in range(6):
        for j in range(1+(i%3)):
            cyl('counted_coin_stack',(.10+i*.24,-.74,1.32+j*.036),.065,.026,'brass',sides=10,bevel=0)
    cyl('wax_seal',(.35,.4,1.22),.15,.05,'wine',sides=12)
    rod('seal_stamp',(.34,.4,1.25),(.34,.4,1.5),.04,'oak')


def treasury():
    box('treasury_floor_pallet',(0,0,.10),(5,4,.2),'oak',.035)
    chest(-1.45,.8,.20,1.7,1.2,1.5)
    chest(.60,1.0,.20,1.9,1.25,1.35)
    chest(-1.2,-.88,.20,1.65,1.2,.85)
    # Secure open-front display for bullion, behind visibly locked iron bars.
    box('strongcase_back',(1.52,.10,1.95),(1.68,.14,2.75),'iron',.04)
    for z in [.25,1.22,2.20,3.25]:box('bullion_shelf',(1.52,-.42,z),(1.75,1.3,.12),'iron',.025)
    for x in [.72,2.32]:box('case_stile',(x,-.98,1.76),(.12,.12,3.04),'iron',.02)
    for x in [.92,1.3,1.7,2.1]:rod('security_bar',(x,-1.03,.30),(x,-1.03,3.24),.025,'iron')
    for z in [.4,1.37,2.35]:
        for x in [1.03,1.6,2.14]:
            box('cast_gold_ingot',(x,-.38,z),(.44,.77,.20),'brass',.06)
            box('mint_stamp',(x,-.39,z+.112),(.12,.23,.012),'iron',.008)
    box('strongcase_lock',(1.5,-1.10,1.66),(.3,.12,.36),'brass',.03)
    for i in range(32):
        a=i*2.3999;r=.53*math.sqrt((i%11)/11)
        cyl('loose_treasury_coins',(.30+r*math.cos(a),-1.27+r*math.sin(a),.235+(i//11)*.032),
            .075,.026,'brass',sides=10,bevel=0)
    scroll(-1.45,.78,1.96,.75)


def reliquary():
    for z,r,h,mat in [(.15,1.5,.3,'stone'),(.45,1.22,.3,'brass'),(.9,.95,.65,'stone'),
                       (1.30,1.20,.15,'brass'),(3.75,1.3,.18,'brass')]:
        cyl('reliquary_octagonal_base',(0,0,z),r,h,mat,sides=8)
    for i in range(8):
        a=math.tau*i/8;x,y=1.04*math.cos(a),1.04*math.sin(a)
        rod('gothic_display_mullion',(x,y,1.34),(x,y,3.72),.042,'iron')
        ball('mullion_jewel',(x,y,3.66),.085,'brass')
        b=a+math.pi/4
        mesh('leaded_glass_pane',[(x,y,1.42),(1.04*math.cos(b),1.04*math.sin(b),1.42),
            (1.04*math.cos(b),1.04*math.sin(b),3.55),(x,y,3.55)],[(0,1,2,3)],'glass')
        path('canopy_rib',[(x,y,3.85),(x*.72,y*.72,4.36),(0,0,4.83)],.05,'brass')
    cyl('relic_mount',(0,0,1.66),.42,.56,'stone',.28,sides=8)
    shield('sunshield_of_the_oath',0,-.02,2.78,1.22,1.65,'brass')
    ring('sunshield_halo',(0,.12,2.92),.82,.035,'brass',True)
    ball('reliquary_finial',(0,0,4.91),.10,'brass')
    box('relic_inscription',(0,-1.06,1.12),(.87,.055,.23),'iron',.018)


def chandelier():
    for radius,z in [(3.65,.45),(2.35,1.52)]:
        for dz in [-.09,.09]:ring('forged_chandelier_ring',(0,0,z+dz),radius,.055,'iron',steps=48)
        for i in range(16):
            a=math.tau*i/16;x,y=radius*math.cos(a),radius*math.sin(a)
            box('ring_gilt_staple',(x,y,z),(.12,.12,.27),'brass',.02)
            cyl('candle_cup',(x,y,z+.20),.17,.10,'brass',.22)
            cyl('beeswax_candle',(x,y,z+.45),.065,.48,'ivory',.055)
            ball('candle_flame',(x,y,z+.73),.074,'glow',(.55,.55,1.65))
            if i%2==0:
                rod('gothic_chandelier_spoke',(x*.97,y*.97,z),(0,0,2.5),.034,'iron')
    for i in range(4):
        a=i*math.pi/2+math.pi/4
        x,y=2.0*math.cos(a),2.0*math.sin(a)
        path('suspension_chain',[(x,y,1.5),(x*.5,y*.5,2.45),(0,0,2.88)],.037,'iron')
        for j in range(4):
            t=j/4
            ring('chain_link',(x*(1-t),y*(1-t),1.5+t*1.35),.08,.018,'brass',True,steps=12)
    cyl('central_hub',(0,0,1.72),.30,1.1,'iron',.14,sides=8)
    ball('pendant_amber',(0,0,.71),.24,'brass',(.8,.8,1.5))
    ring('ceiling_eye',(0,0,2.89),.10,.025,'iron',True)


def tapestry():
    cloth('woven_oath_banner',(0,0,3.92),4.55,7.5,'wine',True,7,.085)
    for x in [-2.1,2.1]:
        path('gilt_woven_border',[(x,-.11,z) for z in [.25+i*.25 for i in range(30)]],.045,'brass')
        for i in range(16):
            z=.50+i*.43
            path('embroidered_diamond',[(x,-.13,z-.12),(x+.09,-.13,z),(x,-.13,z+.12),(x-.09,-.13,z),(x,-.13,z-.12)],.012,'ivory')
    for z in [.33,7.51]:rod('border_seam',(-2.1,-.12,z),(2.1,-.12,z),.045,'brass')
    shield('embroidered_aegis',0,-.14,4.15,2.9,3.45,'iron')
    # One shield and three radiant emblems, readable without borrowed heraldry.
    ring('embroidered_oath_sun',(0,-.18,6.4),.54,.043,'brass',True)
    for i in range(12):
        a=math.tau*i/12
        rod('stitched_sunray',(.66*math.cos(a),-.18,6.4+.66*math.sin(a)),
            (.86*math.cos(a),-.18,6.4+.86*math.sin(a)),.026,'ivory')
    for s in [-1,1]:
        path('oak_leaf_spray',[(s*.2,-.17,1.7),(s*.9,-.17,2.15),(s*1.5,-.17,3.0)],.03,'brass')
        for i in range(6):
            x=s*(.35+i*.2);z=1.8+i*.19
            ball('embroidered_leaf',(x,-.16,z),.15,'brass',(1,.16,.43))
    rod('bronze_banner_hanger',(-2.48,.02,7.88),(2.48,.02,7.88),.06,'brass')
    for x in [-2.35,2.35]:ball('hanger_finial',(x,.02,7.88),.13)
    for x in [-1.75,-.9,0,.9,1.75]:
        path('banner_hanging_loop',[(x,0,7.6),(x,-.03,7.96),(x,.10,7.90)],.035,'wine')
    for i in range(27):
        x=-2.05+i*.157
        rod('banner_fringe',(x,0,.22),(x+.02,0,.02),.015,'brass')


BUILDERS = {'throne':throne,'oath_statue':oath_statue,'war_table':war_table,
    'arms_rack':arms_rack,'provision_rack':provision_rack,'bunk':bunk,'hearth':hearth,
    'feast_table':feast_table,'archive':archive,'counting_desk':counting_desk,
    'treasury':treasury,'reliquary':reliquary,'chandelier':chandelier,'tapestry':tapestry}
ENVELOPES = {'throne':(10,8,10),'oath_statue':(4,4,8),'war_table':(6,4,2),
    'arms_rack':(5,2,3.5),'provision_rack':(5,2,3),'bunk':(3,5,3),'hearth':(6,3,6),
    'feast_table':(7,3,1.7),'archive':(5,1.5,5),'counting_desk':(4,2.5,2),
    'treasury':(5,4,3.5),'reliquary':(3,3,5),'chandelier':(8,8,3),'tapestry':(5,.4,8)}
selection = next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--assets=')),list(BUILDERS))
report_file=WORK/'build-report.json'
report=json.loads(report_file.read_text()) if report_file.exists() else []
for kind in selection:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    BUILDERS[kind]()
    # The declared envelope is an upper bound; do not distort a carefully carved
    # silhouette to hit it. Uniformly shrink any protrusion and ground the result.
    deps=bpy.context.evaluated_depsgraph_get()
    coords=[ob.matrix_world@Vector(c) for ob in bpy.context.scene.objects if ob.type in ('MESH','CURVE')
        for c in ob.evaluated_get(deps).bound_box]
    lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    target=ENVELOPES[kind]
    # Planar tapestries use less than40cm depth; decorative relief is scaled in Y.
    scale=[min(1,target[i]/(hi[i]-lo[i])) for i in range(3)]
    if kind!='tapestry':scale=[min(scale)]*3
    for ob in bpy.context.scene.objects:
        ob.location.x*=scale[0];ob.location.y*=scale[1]
        ob.location.z=(ob.location.z-lo.z)*scale[2]
        ob.scale.x*=scale[0];ob.scale.y*=scale[1];ob.scale.z*=scale[2]
    bpy.context.scene['asset_kind']='citadel_'+kind
    bpy.context.scene['delivery_envelope_width_depth_height']=list(target)
    bpy.data.libraries.write(str(WORK/'sources'/f'citadel_{kind}.blend'),{bpy.context.scene},fake_user=True,compress=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active=next(iter(bpy.context.selected_objects))
    bpy.ops.object.convert(target='MESH');bpy.ops.object.join()
    source=bpy.context.object;source.name='aegis_citadel_'+kind
    bpy.context.scene.cursor.location=(0,0,0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    # Smart UV islands provide consistent mapped PBR on carved/curved subparts.
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.01)
    bpy.ops.object.mode_set(mode='OBJECT')
    source.data.calc_loop_triangles()
    base_ratio=min(1,29000/max(1,len(source.data.loop_triangles)))
    lods=[]
    for level,ratio in enumerate([base_ratio,base_ratio*.52,base_ratio*.24]):
        ob=source.copy();ob.data=source.data.copy();bpy.context.collection.objects.link(ob)
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
        if ratio<1:
            mod=ob.modifiers.new('distance_reduction','DECIMATE');mod.ratio=ratio
            bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=ob.modifiers.new('delivery_triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
        # Remove orphan material slots left by joining independently authored parts.
        bpy.ops.object.material_slot_remove_unused()
        ob.data.calc_loop_triangles()
        model=f'prop_aegis_citadel_{kind}'+(f'_lod{level}' if level else '')+'.glb'
        file=WORK/'runtime'/model
        bpy.ops.export_scene.gltf(filepath=str(file),export_format='GLB',use_selection=True,
            export_yup=True,export_texcoords=True,export_normals=True,export_tangents=True)
        lods.append({'level':level,'model':model,'triangles':len(ob.data.loop_triangles),
            'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
        bpy.data.objects.remove(ob,do_unlink=True)
    item={'kind':'citadel_'+kind,'envelope':dict(zip(['width','depth','height'],target)),
        'sourceTriangles':len(source.data.loop_triangles),'lods':lods}
    report=[a for a in report if a['kind']!=item['kind']]+[item]
    report_file.write_text(json.dumps(report,indent=2)+'\n')
    print('CITADEL_DECOR_COMPLETE',kind,lods[0]['triangles'],flush=True)
