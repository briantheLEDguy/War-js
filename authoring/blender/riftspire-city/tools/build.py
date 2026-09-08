"""Riftspire's carved basalt and suspended timber kit. Blender Z-up, fronts -Y.

Detailed sources retain bevels; runtime meshes have shared 2K PBR and three LODs.
Run Blender -b --python-exit-code 1 --python this_file -- --assets=house_1,bridge,hut,palace
"""
import bpy, bmesh, math, json, sys, hashlib, random
from pathlib import Path
from mathutils import Vector
import numpy as np

WORK=Path(__file__).resolve().parents[1]
ROOT=WORK.parents[2]
RESIDENCES=json.loads((ROOT/'scripts/campaign/riftspire-residence-profiles.json').read_text())
sys.path.insert(0,str(WORK/'tools'))
from district_details import DETAIL_KINDS, build_detail
sys.path.insert(0,str(ROOT/'authoring/blender/aegis-city/tools'))
from city_materials import surface
bpy.ops.wm.read_factory_settings(use_empty=True)
for folder in ['sources','runtime','review','textures']: (WORK/folder).mkdir(exist_ok=True)
M={}
for name, source, color, metal in [
    ('basalt','stone',(.22,.235,.25),0),('trim','limestone',(.37,.355,.34),0),
    ('timber','oak',(.20,.125,.075),0),('slate','slate',(.08,.105,.13),0),
    ('iron','iron',(.075,.09,.10),.8),('cloth','canvas_red',(.20,.075,.19),0),
    ('rock','granite',(.255,.27,.285),0)]:
    mat=bpy.data.materials.new('riftspire_'+name); mat.use_nodes=True
    nodes,links=mat.node_tree.nodes,mat.node_tree.links; p=nodes.get('Principled BSDF')
    maps=None
    for channel in ['baseColor','orm','normal']:
        file=WORK/'textures'/f'{name}_{channel}.png'
        if file.exists(): im=bpy.data.images.load(str(file),check_existing=True)
        else:
            if maps is None: maps=surface(source,color,metal,2048)[:3]
            values=maps[['baseColor','orm','normal'].index(channel)]
            im=bpy.data.images.new(file.stem,width=2048,height=2048,alpha=True)
            im.colorspace_settings.name='sRGB' if channel=='baseColor' else 'Non-Color'
            im.pixels.foreach_set(values.astype(np.float32).ravel());im.filepath_raw=str(file);im.file_format='PNG';im.save()
        if channel!='baseColor': im.colorspace_settings.name='Non-Color'
        t=nodes.new('ShaderNodeTexImage');t.image=im
        if channel=='baseColor':links.new(t.outputs['Color'],p.inputs['Base Color'])
        elif channel=='orm':
            split=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs['Color'],split.inputs[0])
            links.new(split.outputs['Green'],p.inputs['Roughness']);links.new(split.outputs['Blue'],p.inputs['Metallic'])
        else:
            nm=nodes.new('ShaderNodeNormalMap');links.new(t.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],p.inputs['Normal'])
    M[name]=mat
for name,col,emission in [('glass',(.5,.22,.06),1.4),('rune',(.22,.05,.4),.7)]:
    mat=bpy.data.materials.new('riftspire_'+name);mat.use_nodes=True;p=mat.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*col,1);p.inputs['Emission Color'].default_value=(*col,1);p.inputs['Emission Strength'].default_value=emission;M[name]=mat

def mesh(name,verts,faces,mat='basalt',bevel=0):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);data.materials.append(M[mat])
    uv=data.uv_layers.new(name='UVMap')
    for f in data.polygons:
        axis=max(range(3),key=lambda a:abs(f.normal[a]));axes=[a for a in range(3) if a!=axis]
        for li in f.loop_indices:
            v=data.vertices[data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/4,v[axes[1]]/4)
    if bevel:
        mod=ob.modifiers.new('worn_cut_edges','BEVEL');mod.width=bevel;mod.segments=2
    return ob

def box(name,pos,size,mat='basalt',bevel=.04):
    x,y,z=pos;w,d,h=[s/2 for s in size]
    return mesh(name,[(x+a*w,y+b*d,z+c*h) for a,b,c in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]],[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat,bevel)

def beam(name,a,b,w=.18,mat='iron'):
    d=Vector(b)-Vector(a);ob=box(name,(0,0,0),(w,w,d.length),mat,.025)
    ob.location=(Vector(a)+Vector(b))/2;ob.rotation_euler=d.to_track_quat('Z','Y').to_euler();return ob

def tube(name,points,r=.1,mat='iron',sides=6):
    verts=[]
    for i,point in enumerate(points):
        direction=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        q=direction.to_track_quat('Z','Y')
        verts += [tuple(Vector(point)+q@Vector((r*math.cos(j*2*math.pi/sides),r*math.sin(j*2*math.pi/sides),0))) for j in range(sides)]
    faces=[(i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j) for i in range(len(points)-1) for j in range(sides)]
    return mesh(name,verts,faces,mat)

def ring(name,x,y,z,r=.4,mat='iron'):
    return tube(name,[(x+r*math.cos(t),y,z+r*math.sin(t)) for t in np.linspace(0,2*math.pi,17)],.09,mat)

def arch(x,y,z,w=2,h=4,mat='trim'):
    spring=h-w*.7
    for side in [-1,1]:
        box('recessed_arch_jamb',(x+side*w/2,y,z+spring/2),(.32,.55,spring),mat)
        pts=[(x+side*w/2*(1-t),y,z+spring+(h-spring)*(1-(1-t)**1.6)) for t in np.linspace(0,1,9)]
        tube('carved_arch_order',pts,.20,mat)

def window(x,y,z,w=1.6,h=3):
    box('deep_window_recess',(x,y+.15,z+h/2),(w+.25,.25,h+.15),'iron')
    box('amber_glazing',(x,y-.02,z+h*.44),(w-.25,.09,h*.82),'glass',0)
    arch(x,y-.18,z,w,h)
    beam('leaded_mullion',(x,y-.28,z),(x,y-.28,z+h),.1)
    for zz in [.33,.66]:beam('leaded_transom',(x-w/2,y-.28,z+h*zz),(x+w/2,y-.28,z+h*zz),.09)
    box('drip_sill',(x,y-.3,z-.15),(w+.65,.85,.25),'trim')

def roof(w,d,base,h,mat='slate'):
    mesh('steep_split_slate_roof',[(-w/2,-d/2,base),(w/2,-d/2,base),(0,-d/2,base+h),(-w/2,d/2,base),(w/2,d/2,base),(0,d/2,base+h)],[(0,1,2),(5,4,3),(0,2,5,3),(2,1,4,5)],mat)
    for y in [-d/2,d/2]:
        beam('carved_gable_edge',(-w/2,y,base),(0,y,base+h),.24,'trim');beam('carved_gable_edge',(0,y,base+h),(w/2,y,base),.24,'trim')
    beam('roof_ridge',(0,-d/2,base+h),(0,d/2,base+h),.24)
    # Overlapping courses give the slate silhouette real thickness at street distance.
    for side in [-1,1]:
        for row in range(6):
            x0=side*w/2*row/6;x1=side*w/2*(row+1)/6
            for col in range(10):
                y0=-d/2+col*d/10;y1=y0+d/10-.04
                z0=base+h*(1-row/6)+.065;z1=base+h*(1-(row+1)/6)+.065
                mesh('overlapping_slate',[(x0,y0,z0),(x1,y0,z1),(x1,y1,z1),(x0,y1,z0),(x0,y0,z0-.07),(x1,y0,z1-.07),(x1,y1,z1-.07),(x0,y1,z0-.07)],[(0,1,2,3),(1,5,6,2),(3,2,6,7)],mat)

def railing(x1,x2,y,z=0,mat='iron'):
    for x in np.arange(x1,x2+.1,1.4):
        beam('forged_baluster',(x,y,z),(x,y,z+1.3),.12,mat)
        if mat=='iron':ring('forged_scroll',x,y,z+.8,.24)
    for zz in [.2,1.35]:beam('continuous_handrail',(x1,y,z+zz),(x2,y,z+zz),.13,mat)

def lantern(x,y,z):
    box('lantern_backplate',(x,y+.15,z),(.65,.2,1.2),'iron')
    box('warm_lantern',(x,y-.2,z),(.4,.4,.75),'glass',0)
    for dx in [-.26,.26]:beam('lantern_cage',(x+dx,y-.45,z-.5),(x+dx,y-.45,z+.5),.075)
    box('lantern_cap',(x,y-.2,z+.55),(.75,.7,.15),'iron')

def house(index=0,hut=False):
    profile=RESIDENCES[index%8]
    w=profile['width'] if not hut else 8
    d=profile['depth'] if not hut else 7;h=profile['height'] if not hut else 6
    mat='timber' if hut or index==6 else 'basalt'
    box('floor',(0,0,-.2),(w,d,.4),mat)
    for x in [-(w+2.8)/4,(w+2.8)/4]:box('portal_side_wall',(x,-d/2,h/2),((w-2.8)/2,.65,h),mat)
    box('entry_lintel',(0,-d/2,(h+4)/2),(2.8,.65,h-4),mat)
    box('back_wall',(0,d/2,h/2),(w,.65,h),mat)
    for x in [-w/2,w/2]:box('return_wall',(x,0,h/2),(.65,d,h),mat)
    arch(0,-d/2-.38,0,3.1,4.8)
    for x in [-w*.32,w*.32]:
        window(x,-d/2-.39,1.5,1.7,3.1)
        if not hut and h>=10:window(x,-d/2-.39,6.4,1.8,3.1)
        if not hut and h>=15:window(x,-d/2-.39,11.4,1.5,2.8)
    for x in [-w/2+.2,w/2-.2]:
        box('structural_pier',(x,-d/2-.6,h/2),(.7,1.1,h+.7),'trim')
        for zz in [2,h*.55,h]:box('pier_carved_collar',(x,-d/2-.7,zz),(.9,1.3,.3),'iron')
    style='gable' if hut else profile['roof'];rise=4 if hut else profile['rise']
    if style=='double':
        for side in [-1,1]:
            before=set(bpy.context.scene.objects);roof((w+1)/2,d+1,h,rise if side<0 else rise-1)
            for ob in set(bpy.context.scene.objects)-before:ob.location.x+=side*(w+1)/4
    elif style=='shed':
        # A single long sloping roof reads as a workshop, not another gabled house.
        mesh('weathered_lean_roof',[(-w/2-.5,-d/2-.5,h),(w/2+.5,-d/2-.5,h),(-w/2-.5,d/2+.5,h+rise),(w/2+.5,d/2+.5,h+rise)],[(0,1,3,2)],'slate')
        for x in np.linspace(-w/2-.5,w/2+.5,12):beam('raised_roof_seam',(x,-d/2-.5,h),(x,d/2+.5,h+rise),.12,'iron')
        for x in [-w/2,w/2]:mesh('shed_side_infill',[(x,-d/2,h),(x,d/2,h),(x,d/2,h+rise)],[(0,1,2)],'timber')
    elif style=='court':
        box('roofcourt_ceiling',(0,0,h),(w+.6,d+.6,.45),'trim')
        for x in [-w/2,w/2]:box('roofcourt_parapet',(x,0,h+.65),(.45,d,1.3),'basalt')
        railing(-w/2,w/2,-d/2,h+.1)
        for x in [-w*.3,w*.3]:box('roofcourt_storage',(x,1,h+.65),(1.7,2,1),'timber')
    elif style=='offset':
        before=set(bpy.context.scene.objects);roof(w+1,d+1,h,rise)
        # Move the ridge vertices while retaining the eaves and footprint.
        bpy.context.view_layer.update()
        for ob in set(bpy.context.scene.objects)-before:
            inverse=ob.matrix_world.inverted()
            for v in ob.data.vertices:
                world=ob.matrix_world@v.co;world.x+=(world.z-h)/rise*w*.16;v.co=inverse@world
    else:roof(w+1,d+1,h,rise)
    for x in [-w/2+.4,w/2-.4]:
        beam('exposed_tie',(x,-d/2-.75,h-1.2),(-x,-d/2-.75,h-3),.18,'timber')
    if index%3==1 and (hut or h>=10):
        # Projecting upper bay and layered cornice distinguish the workshop frontage.
        box('upper_bay',(w*.30,-d/2-.6,h-3),(3.2,1.5,3),'timber')
        window(w*.30,-d/2-1.4,h-4,2,2.8)
        box('bay_eaves',(w*.30,-d/2-.8,h-1.35),(3.8,2,.35),'slate')
    if index%3==2:
        for x in [-w*.28,w*.28]:
            beam('curved_roof_finial',(x,-d/2,h+1),(x*.8,-d/2,h+4),.22)
    for yy in [-d/2-.85,d/2+.3]:
        box('weathered_eaves',(0,yy,h-.15),(w+1,.4,.4),'timber')
    box('cantilevered_balcony',(0,-d/2-1.1,.1),(w+1,2.3,.35),'timber')
    for x in [-w*.4,w*.4]:beam('balcony_knee_brace',(x,-d/2,-2),(x,-d/2-2,.0),.3)
    railing(-w/2,-1.8,-d/2-2,.3);railing(1.8,w/2,-d/2-2,.3)
    for x in [-1.95,1.95]:lantern(x,-d/2-.7,3.0)
    tube('rainwater_downpipe',[(w/2+.6,1,h),(w/2+.6,1,1),(w/2+.8,-1,.4)],.13)
    if index%2:
        box('patched_cloth_awning',(0,-d/2-1.4,5.2),(w*.6,2,.12),'cloth')
        for x in [-w*.3,w*.3]:beam('awning_bracket',(x,-d/2,4.3),(x,-d/2-2.3,5.2),.13)
    if hut:
        for x in [-3,3]:
            beam('suspension_upright',(x,0,-1),(x,0,9),.3)
            ring('load_bearing_chain_eye',x,0,9,.6)
        for y in [-2,2]:beam('cross_lashing',(-4,y,-.7),(4,y,-.7),.4,'timber')
    else:
        box('chimney',(w*.3,1,h+2),(1.1,1.1,5),'basalt');box('chimney_crown',(w*.3,1,h+4.5),(1.5,1.5,.3),'trim')

def bridge(rope=False):
    w=5 if rope else 18;d=24
    for i in range(30):box('individual_worn_deck',(0,-11.6+i*.8,-.2),(w,.77,.4),'timber' if rope else 'basalt',.025)
    for side in [-1,1]:
        x=side*(w/2-.25)
        for y in range(-12,13,3):
            beam('bridge_rail_post',(x,y,0),(x,y,1.5),.18)
            if not rope:
                box('cut_stone_pier',(x,y,-1.7),(.8,1,3.4),'trim')
                beam('underdeck_diagonal',(x,y,-3),(x,y+3,-.4),.25)
        for z in [.55,1.5]:beam('bridge_handrail',(x,-12,z),(x,12,z),.17,'timber' if rope else 'iron')
        if not rope:
            for y in [-10,10]:lantern(x,y,2.3)
    for y in [-10,0,10]:beam('load_crossbeam',(-w/2,y,-.7),(w/2,y,-.7),.5)

def palace():
    for x in [-20,20]:box('deep_portal_wing',(x,0,18),(26,12,36))
    box('portal_crown',(0,0,27),(14,12,18))
    for order in range(3):arch(0,-6.4-order*.38,0,14+order,23+order*1.1)
    for x in [-30,-20,20,30]:
        box('palace_buttress',(x,-7,20),(2,4,40),'trim')
        for z in [9,23]:window(x+3,-6.45,z,2.5,9)
        for zz,r in [(40,2.1),(45,1.4)]:
            verts=[(x+r*math.cos(i*math.pi/4),-7+r*math.sin(i*math.pi/4),zz) for i in range(8)]+[(x,-7,zz+15)]
            mesh('pier_needle',verts,[(i,(i+1)%8,8) for i in range(8)],'slate')
    for x in [-11,11]:box('hanging_rune_banner',(x,-6.6,26),(4,.15,9),'cloth')
    for side in [-1,1]:beam('rift_sigil',(side*1.1,-6.85,31),(0,-6.85,35),.16,'rune')
    for z in [8,21,35]:
        for x in [-20,20]:box('palace_string_course',(x,-6.8,z),(26,1.8,.6),'trim')
    for x in [-32,-27,-22,-17,-12,12,17,22,27,32]:
        box('parapet_pier',(x,-6.4,38),(1.1,1.5,5),'trim')
        arch(x,-7.1,34,3.6,5.4)
        for zz in [5,17,29]:
            box('buttress_shoulder',(x,-7.4,zz),(1.3,2.5,.5),'trim')
    for x in [-20,20]:
        for y in [-8,-6.8]:railing(x-11,x+11,y,21)
        box('gallery_floor',(x,-7.3,20.8),(25,3,.5),'trim')
        for xx in [-29,-24,-16,-11,11,16,24,29]:
            beam('gallery_corbel',(xx,-6,17),(xx,-8.5,20.5),.55,'trim')
    for x in [-30,-20,20,30]:
        for zz in [12,25,38]:
            box('needle_collar',(x,-7,zz),(3,4.8,.6),'iron')
        for xx in [-.6,.6]:beam('fluted_pier',(x+xx,-9.15,1),(x+xx,-9.15,38),.18,'trim')
    # The central crest is an open belfry, with roof and layered pointed orders.
    for x in [-5,5]:box('crest_pier',(x,0,42),(2,10,12),'trim')
    arch(0,-5.5,36,8,12)
    for x in [-5,5]:beam('crest_roof',(x,-5.5,48),(0,-5.5,59),.35,'trim')
    mesh('crest_roof_slate',[(-7,-6,48),(7,-6,48),(0,-6,60),(-7,6,48),(7,6,48),(0,6,60)],[(0,2,5,3),(2,1,4,5)],'slate')

def hall():
    box('hall_floor',(0,0,-.25),(70,60,.5))
    for x in [-34.5,34.5]:box('hall_side_wall',(x,0,12),(1,60,24))
    for y in [-29.5,29.5]:
        for x in [-20,20]:box('hall_portal_wing',(x,y,12),(30,1,24))
        box('hall_portal_lintel',(0,y,18),(10,1,12))
        arch(0,y-.6,0,10,17)
    box('vaulted_ceiling',(0,0,24),(70,60,1))
    for x in [-26,26]:
        for y in [-20,0,20]:
            box('ribbed_hall_pier',(x,y,11),(1.8,1.8,22),'trim')
            for z in [1,9,20]:box('pier_belt',(x,y,z),(2.2,2.2,.4),'iron')
            beam('vaulting_rib',(x,y,18),(0,y,23),.45,'trim')

def furniture(kind):
    if kind=='throne':
        for i in range(4):box('dais_step',(0,-1+i*.5,.15+i*.25),(10-i*.7,8-i*.7,.3),'trim')
        box('sovereign_seat',(0,0,2.1),(4,3,1));box('carved_high_back',(0,1.6,5),(4,.9,7))
        for x in [-2,2]:box('throne_arm',(x,0,3),(.7,3,.7),'iron');beam('throne_crown',(x,1.6,8),(x*.6,1.6,11),.45,'trim')
        window(0,1,5,1.7,3)
    elif kind=='lantern':lantern(0,0,2.5);beam('lamp_standard',(0,.2,0),(0,.2,3.4),.2)
    elif kind=='banner':
        beam('banner_pole',(0,0,0),(0,0,6),.16);box('frayed_house_banner',(1,0,4),(2,.12,3),'cloth')
        for side in [-1,1]:beam('inlaid_rift_mark',(1+side*.6,-.08,4),(1,-.08,5),.09,'rune')
    else:
        size={'table':(5,2.5,1.2),'archive':(4,1,4),'rack':(4,1.5,3),'altar':(4,2,2),'forge':(4,3,2),'crate':(2,2,2),'bed':(2,4,.7)}[kind]
        w,d,h=size
        for x in [-w/2+.2,w/2-.2]:
            for y in [-d/2+.2,d/2-.2]:box('framed_furniture_leg',(x,y,h/2),(.25,.25,h),'iron')
        for z in ([.3,1.3,2.3,3.3] if kind=='archive' else [h]):
            box('planked_surface',(0,0,z),(w,d,.2),'timber' if kind not in ['forge','altar'] else 'basalt')
            if kind=='archive':
                for x in np.arange(-1.7,1.8,.35):box('bound_volume',(x,0,z+.35),(.28,.65,.55),'cloth')
        if kind in ['forge','altar']:arch(0,-d/2,.4,w*.6,h);box('coals',(0,0,h+.15),(w*.5,d*.5,.15),'glass')
        if kind=='crate':
            for y in [-d/2,d/2]:box('crate_side',(0,y,h/2),(w,.15,h),'timber');beam('crate_diagonal',(-w/2,y,0),(w/2,y,h),.15)
        if kind=='bed':
            box('stuffed_mattress',(0,0,.85),(1.9,3.8,.45),'cloth',.15)
            box('linen_pillow',(0,1.35,1.13),(1.5,.8,.25),'cloth',.12)
            box('carved_bed_head',(0,1.95,1.2),(2.2,.25,2),'timber')
            for y in np.arange(-1.7,.6,.3):beam('blanket_stitch',(-.9,y,1.1),(.9,y,1.1),.035,'trim')
        if kind=='forge':
            box('hearth_back',(0,1.35,2.1),(4,.65,4.2),'basalt')
            box('forge_hood',(0,.2,4),(4.4,3,.5),'iron')
            box('flue',(0,.7,5.5),(1.6,1.6,3),'basalt')
            for x in np.arange(-1.5,1.6,.35):beam('hearth_grate',(x,-1.2,2.2),(x,.8,2.2),.12)
        if kind=='rack':
            box('tool_rack_back',(0,.65,1.6),(4,.2,2.8),'timber')
            for x in [-1.5,-.5,.5,1.5]:
                beam('hanging_tool_haft',(x,.3,.7),(x,.3,2.7),.10,'timber')
                box('hammer_head',(x,.3,2.6),(.55,.35,.3),'iron')
        if kind=='table':
            for x in [-1.5,0,1.5]:
                ring('pewter_mug_rim',x,0,1.7,.18)
                box('serving_board',(x,.1,1.4),(.7,.7,.1),'timber')
            for y in [-1.8,1.8]:
                box('tavern_bench',(0,y,.7),(4.7,.65,.25),'timber')
                for x in [-1.7,1.7]:box('bench_leg',(x,y,.35),(.3,.5,.7),'timber')

def build(kind):
    if kind in DETAIL_KINDS:build_detail(kind,globals())
    elif kind.startswith('house_'):house(int(kind[-1])-1)
    elif kind=='hut':house(1,True)
    elif kind in ['bridge','rope_bridge']:bridge(kind=='rope_bridge')
    elif kind=='palace':palace()
    elif kind=='hall':hall()
    elif kind=='room':house(3)
    elif kind=='chain':
        for i in range(32):
            ob=ring('forged_chain_link',0,0,i*.62,.43)
            if i%2:ob.rotation_euler.z=math.pi/2
    elif kind=='anchor':
        for x in [-2,2]:box('anchor_buttress',(x,0,6),(2,6,12),'trim')
        box('anchor_crosshead',(0,0,12),(8,6,2),'iron');ring('anchor_eye',0,-3.2,12,1.5)
        for x in [-3,3]:beam('tension_brace',(x,2,0),(x,-2,12),.8)
    elif kind=='training_dummy':
        box('effigy_stone_foot',(0,0,.15),(1.2,1.2,.3),'basalt')
        beam('effigy_post',(0,0,.3),(0,0,2.4),.22,'timber')
        beam('effigy_crossbar',(-.85,0,1.8),(.85,0,1.8),.17,'timber')
        for i in range(16):
            a=i*math.pi/8
            beam('bound_straw_rib',(.3*math.sin(a),.25*math.cos(a),1),(.35*math.sin(a),.27*math.cos(a),2),.13,'timber')
        for z in [1.1,1.8]:tube('rope_binding',[(.4*math.sin(a),.32*math.cos(a),z) for a in np.linspace(0,math.pi*2,25)],.035,'cloth')
        box('patched_striking_pad',(0,-.29,1.53),(.63,.12,.75),'cloth')
        for x in [-.23,.23]:
            for z in [1.25,1.5,1.8]:beam('pad_stitches',(x-.04,-.365,z-.03),(x+.04,-.365,z+.03),.012,'trim')
        box('effigy_mask',(0,-.06,2.25),(.42,.38,.42),'iron')
    elif kind=='lift':
        box('lift_deck',(0,0,-.25),(10,10,.5),'timber')
        for x in [-4.6,4.6]:
            for y in [-4.6,4.6]:beam('lift_cage',(x,y,0),(x,y,4),.22)
            beam('cage_top',(x,-4.6,4),(x,4.6,4),.22)
        for y in [-4.7,4.7]:railing(-4.6,-1.5,y);railing(1.5,4.6,y)
        for x in [-4.6,4.6]:beam('cage_roof_brace',(x,0,4),(0,0,4.3),.22)
        ring('hoist_eye',0,0,5,1)
    elif kind=='stairs':
        for i in range(40):box('cut_stair_tread',(0,-9.75+i*.5,-.125+i*.25),(6,.52,.25),'trim')
        for x in [-2.8,2.8]:beam('stair_handrail',(x,-10,1.4),(x,10,11.4),.16)
    elif kind in ['deck','deck_open']:
        box('cut_terrace',(0,0,-.6),(24,18,1.2));box('drainage_edge',(0,-8.7,-.2),(24,.4,.4),'trim')
        if kind=='deck':railing(-12,12,-8.7)
        for x in [-9,0,9]:beam('terrace_corbel',(x,6,-7),(x,-7,-1),.7,'trim')
    elif kind=='lift_landing':
        for x,y,w,d in [(-8.625,0,6.75,24),(8.625,0,6.75,24),(0,-8.625,10.5,6.75),(0,8.625,10.5,6.75)]:
            box('hoist_landing_masonry',(x,y,-.65),(w,d,1.3),'basalt')
        for x in [-11.7,11.7,-5.5,5.5]:
            for y in [-5,0,5]:beam('shaft_guard_post',(x,y,0),(x,y,1.4),.14)
            beam('shaft_guard_rail',(x,-5,1.4),(x,5,1.4),.14)
        for x in [-9,9]:beam('landing_underbrace',(x,-12,-4),(x,12,-1),.7,'iron')
    elif kind=='hub':
        for x,y,w,d in [(-11.625,0,76.75,100),(43.625,0,12.75,100),(32,-27.625,10.5,44.75),(32,27.625,10.5,44.75)]:
            box('suspended_platform',(x,y,-1),(w,d,2),'basalt')
        for x in range(-45,46,15):
            beam('platform_truss',(x,-50,-4),(x,50,-4),.9)
            for y in [-45,45]:beam('load_splay',(x,y,-4),(0,0,-18),.4)
        for y in [-49,49]:railing(-49,-10,y);railing(10,49,y)
        for x in [-49,49]:
            for a,b in [(-49,-10),(10,49)]:
                beam('court_rail',(x,a,1.4),(x,b,1.4),.12)
                for y in range(a,b,3):beam('court_rail_post',(x,y,0),(x,y,1.4),.12)
    elif kind=='rock_infill':
        # Close unoccupied excavations with a fractured, solid basalt face.
        rng=random.Random(4107);verts=[];faces=[];columns=8;rows=10
        for row in range(rows+1):
            for col in range(columns+1):
                x=-10+col*20/columns+(rng.uniform(-.7,.7) if col not in [0,columns] else 0)
                z=row*24/rows+(rng.uniform(-.65,.65) if row not in [0,rows] else 0)
                y=z*.42+1.1*math.sin(col*2.2+row*.7)+rng.uniform(-.6,.6)
                verts.append((x,y,z))
        front=len(verts);verts += [(x,y+3,z) for x,y,z in verts]
        for row in range(rows):
            for col in range(columns):
                a=row*(columns+1)+col;b=a+1;c=a+columns+1;d=c+1
                faces.extend([(a,b,d),(a,d,c),(a+front,d+front,b+front),(a+front,c+front,d+front)])
        border=list(range(columns+1))+[r*(columns+1)+columns for r in range(1,rows+1)]+list(range(rows*(columns+1)+columns-1,rows*(columns+1)-1,-1))+[r*(columns+1) for r in range(rows-1,0,-1)]
        for i,a in enumerate(border):
            b=border[(i+1)%len(border)];faces.append((a,a+front,b+front,b))
        mesh('uncut_fractured_basalt',verts,faces,'rock')
    elif kind.startswith('rock_'):
        # Each sector includes five actual carved openings, not façades on an uncut wall.
        levels=[(420,28),(410,0),(374,-50),(334,-105),(279,-175),(219,-245),(150,-300)]
        for j in range(len(levels)-1):
            r0,z0=levels[j];r1,z1=levels[j+1]
            for row in range(8):
                za=z0+(z1-z0)*row/8;zb=z0+(z1-z0)*(row+1)/8
                ra=r0+(r1-r0)*row/8;rb=r0+(r1-r0)*(row+1)/8
                for col in range(20):
                    aa=(col/20-.5)*math.pi/32;ab=((col+1)/20-.5)*math.pi/32
                    if j==0 and ((kind.endswith('left') and col<7) or (kind.endswith('right') and col>=13)):continue
                    if j==2 and zb< -70 and kind.startswith('rock_palace'):continue
                    if j<5 and zb<z1+20 and abs((aa+ab)*.5*r1)<8:continue
                    def v(r,a,z):
                        envelope=math.sin(math.pi*(z-z0)/(z1-z0))**2
                        fracture=1.2*math.sin(a*64+z*.18)+envelope*(7*math.sin(a*173+z*.081)+4*math.sin(a*287-z*.043))
                        return ((r+fracture)*math.sin(a),(r+fracture)*math.cos(a),z)
                    mesh('chipped_cliff_stratum',[v(ra,aa,za),v(ra,ab,za),v(rb,ab,zb),v(rb,aa,zb)],[(0,2,1),(0,3,2)],'rock')
            if j<5 and not (j==2 and kind.startswith('rock_palace')):
                # Excavations terminate in rock behind the room. They are not
                # unbounded holes through the crater shell at distant LODs.
                top=z1+24; front_top=r1+(r0-r1)*24/(z0-z1); back=r1+36
                box('excavation_back',(0,back,z1+12),(21,1,24),'rock',0)
                box('excavation_floor',(0,(r1+back)/2,z1-.25),(21,back-r1,.5),'rock',0)
                box('excavation_ceiling',(0,(front_top+back)/2,top),(21,back-front_top,.5),'rock',0)
                for x in [-10,10]:
                    verts=[(x+dx,y,z) for dx in [-.4,.4] for y,z in [(r1,z1),(back,z1),(back,top),(front_top,top)]]
                    mesh('excavation_side_reveal',verts,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'rock')
        for ra,za,rb,zb in [(420,28,448,10),(448,10,512,0),(512,0,512,-310)]:
            for i in range(20):
                a=(i/20-.5)*math.pi/32;b=((i+1)/20-.5)*math.pi/32
                mesh('outer_crater_berm',[(ra*math.sin(a),ra*math.cos(a),za),(ra*math.sin(b),ra*math.cos(b),za),(rb*math.sin(b),rb*math.cos(b),zb),(rb*math.sin(a),rb*math.cos(a),zb)],[(0,1,2),(0,2,3)],'rock')
    elif kind=='basin':
        verts=[(0,0,-300)]+[(160*math.sin(a),160*math.cos(a),-300+2*math.sin(a*7)) for a in np.linspace(0,math.pi*2,97)];mesh('crater_basin',verts,[(0,i+1,i) for i in range(1,97)],'rock')
    else:furniture(kind)

KINDS=[*[f'house_{i}' for i in range(1,9)],'hut','bridge','rope_bridge','palace','hall','room','chain','anchor','lift','lift_landing','stairs','deck','deck_open','hub','rock_infill','rock_sector','rock_palace_left','rock_palace_right','rock_gate_left','rock_gate_right','basin','throne','lantern','banner','table','archive','rack','altar','forge','crate','bed','training_dummy']
KINDS += DETAIL_KINDS
requested=next((set(a.split('=',1)[1].split(',')) for a in sys.argv if a.startswith('--assets=')),set(KINDS))
if '--district-details' in sys.argv:requested=set(DETAIL_KINDS)
assert requested<=set(KINDS)
report=json.loads((WORK/'build-report.json').read_text()) if (WORK/'build-report.json').exists() else []
for kind in KINDS:
    if kind not in requested:continue
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);build(kind)
    bpy.data.libraries.write(str(WORK/'sources'/f'{kind}.blend'),{bpy.context.scene},fake_user=True,compress=True)
    bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    for ob in bpy.context.scene.objects:
        for mod in ob.modifiers:
            if mod.type=='BEVEL':mod.segments=1
    bpy.ops.object.convert(target='MESH');bpy.ops.object.join();source=bpy.context.object
    if kind.startswith('rock_'):
        bm=bmesh.new();bm.from_mesh(source.data)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.001)
        bm.to_mesh(source.data);bm.free();source.data.update()
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');source.name='riftspire_'+kind
    source.data.calc_loop_triangles();ratio=min(1,29000/max(1,len(source.data.loop_triangles)));lods=[]
    for level,factor in enumerate([1,.5,.2]):
        ob=source.copy();ob.data=source.data.copy();bpy.context.collection.objects.link(ob)
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
        if ratio*factor<1:
            mod=ob.modifiers.new('runtime_lod','DECIMATE')
            if kind in DETAIL_KINDS or kind.startswith('rock_') or kind in ['stairs','bed','archive','altar','crate','table','rack','forge','lantern','banner','lift','lift_landing','training_dummy','anchor']:
                mod.decimate_type='DISSOLVE';mod.angle_limit=math.radians(5 if level==1 else 15);mod.use_dissolve_boundaries=False
            else:mod.ratio=ratio*factor
            bpy.ops.object.modifier_apply(modifier=mod.name)
        file=WORK/'runtime'/('prop_riftspire_'+kind+(f'_lod{level}' if level else '')+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(file),export_format='GLB',use_selection=True,export_tangents=True)
        data=file.read_bytes();doc=json.loads(data[20:20+int.from_bytes(data[12:16],'little')])
        triangles=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
        lods.append({'level':level,'model':file.name,'triangles':triangles,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
        bpy.data.objects.remove(ob,do_unlink=True)
    report=[a for a in report if a['kind']!=kind]+[{'kind':kind,'lods':lods}]
    (WORK/'build-report.json').write_text(json.dumps(report,indent=2));print('RIFTSPIRE_COMPLETE',kind,flush=True)
