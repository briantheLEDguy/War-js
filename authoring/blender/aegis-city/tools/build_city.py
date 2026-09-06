"""Original modular Aegis architecture. Run with Blender --background --python.

Retains editable detailed sources; exports three mesh LODs with shared, tiled
PBR maps. Brick normals are baked from a retained relief surface, not invented
from color. Geometry uses Blender Z-up, doors face -Y (glTF +Z).
"""
import bpy
import math
import json
import hashlib
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
OUT = WORK / 'runtime'
TEX = WORK / 'textures'
for folder in [OUT, TEX, WORK / 'review', WORK / 'sources']:
    folder.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

def image(name, values, noncolor=False):
    n = values.shape[0]
    im = bpy.data.images.new(name, width=n, height=n, alpha=True)
    if noncolor:
        im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(values.astype(np.float32).ravel())
    im.update()
    im.filepath_raw = str(TEX / (name + '.png'))
    im.file_format = 'PNG'
    im.save()
    im.pack()
    return im

sys.path.insert(0, str(Path(__file__).resolve().parent))
from city_materials import surface
from city_details import KINDS as DETAIL_KINDS, build_detail
from citadel_assets import KINDS as CITADEL_KINDS, build_citadel_asset


def paint(name, color, metallic=0, n=1024):
    rgba, orm, normals, height = surface(name, color, metallic, n)
    return image(name+'_baseColor', rgba), image(name+'_orm', orm, True), image(name+'_normal', normals, True), height


def material(name,color,metallic=0,n=1024):
    base,orm,normal,height = paint(name,color,metallic,n)
    mat=bpy.data.materials.new('aegis_'+name); mat.use_nodes=True
    nodes=mat.node_tree.nodes; links=mat.node_tree.links
    p=nodes.get('Principled BSDF')
    def tex(im):
        t=nodes.new('ShaderNodeTexImage'); t.image=im; return t
    links.new(tex(base).outputs['Color'],p.inputs['Base Color'])
    packed=tex(orm); split=nodes.new('ShaderNodeSeparateColor')
    links.new(packed.outputs['Color'],split.inputs[0])
    links.new(split.outputs['Green'],p.inputs['Roughness'])
    links.new(split.outputs['Blue'],p.inputs['Metallic'])
    group=bpy.data.node_groups.get('glTF Material Output')
    if not group:
        group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
        group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
    occ=nodes.new('ShaderNodeGroup'); occ.node_tree=group
    links.new(split.outputs['Red'],occ.inputs['Occlusion'])
    nm=nodes.new('ShaderNodeNormalMap'); links.new(tex(normal).outputs['Color'],nm.inputs['Color'])
    links.new(nm.outputs['Normal'],p.inputs['Normal'])
    return mat,height,normal

M={}
reuse_materials = '--reuse-materials' in sys.argv
if reuse_materials:
    assert '--assets=citadel' in sys.argv, 'Retained materials are scoped to --assets=citadel'
    # Partial silhouette rebuilds reuse the approved PBR maps without repainting the city.
    with bpy.data.libraries.load(str(WORK/'sources/citadel.blend'), link=False) as (available, loaded):
        loaded.materials = [name for name in available.materials if name.startswith('aegis_')]
    M.update({mat.name.removeprefix('aegis_'): mat for mat in loaded.materials if mat})
    assert {'stone', 'limestone', 'slate', 'copper', 'oak', 'iron', 'flagstone', 'canvas_red'} <= M.keys()
for name,col,metal in [
    ('brick',(.29,.15,.095),0),('stone',(.27,.285,.27),0),('oak',(.14,.095,.055),0),
    ('slate',(.065,.085,.095),0),('iron',(.055,.065,.07),.85),
    ('plaster_ochre',(.48,.365,.21),0),('plaster_lime',(.49,.49,.405),0),
    ('plaster_sage',(.265,.325,.25),0),('limestone',(.40,.39,.32),0),
    ('terracotta',(.265,.115,.065),0),('copper',(.105,.245,.205),.5),
    ('canvas_red',(.31,.075,.055),0),('canvas_gold',(.46,.33,.125),0),
    ('granite',(.31,.335,.35),0),('foliage',(.10,.205,.07),0),('paving',(.25,.20,.155),0),('flagstone',(.24,.25,.23),0)
]:
    if reuse_materials:
        continue
    M[name], height, normal=material(name,col,metal,2048 if name in ('brick','paving','flagstone') else 1024)
    if name=='brick':
        # Bake the same retained geometric relief used by the source material.
        s=128; verts=[]; faces=[]
        for j in range(s+1):
            for i in range(s+1): verts.append((i/s,j/s,float(height[min(j*16,2047),min(i*16,2047)])))
        for j in range(s):
            for i in range(s):
                k=j*(s+1)+i; faces.append((k,k+1,k+s+2,k+s+1))
        mesh=bpy.data.meshes.new('brick_relief_source'); mesh.from_pydata(verts,[],faces)
        high=bpy.data.objects.new('brick_relief_source',mesh); bpy.context.collection.objects.link(high)
        bpy.ops.mesh.primitive_plane_add(size=1,location=(.5,.5,-.01)); low=bpy.context.object
        low.name='brick_bake_target'; low.data.materials.append(M[name])
        target=M[name].node_tree.nodes.new('ShaderNodeTexImage'); target.image=normal
        M[name].node_tree.nodes.active=target
        bpy.context.scene.render.engine='CYCLES'; bpy.context.scene.cycles.samples=8
        bpy.ops.object.select_all(action='DESELECT'); high.select_set(True); low.select_set(True)
        bpy.context.view_layer.objects.active=low
        bpy.context.scene.render.bake.use_selected_to_active=True
        bpy.context.scene.render.bake.cage_extrusion=.1
        bpy.ops.object.bake(type='NORMAL')
        normal.save(); normal.pack()
        bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'sources'/'brick_relief.blend'))
        bpy.data.objects.remove(high,do_unlink=True); bpy.data.objects.remove(low,do_unlink=True)
M['glow']=bpy.data.materials.new('aegis_amber_glass'); M['glow'].use_nodes=True
p=M['glow'].node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(.6,.24,.05,1)
p.inputs['Emission Color'].default_value=(1,.35,.055,1); p.inputs['Emission Strength'].default_value=1.5

def box(name, pos, size, mat='stone', bevel=.04):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos); ob=bpy.context.object; ob.name=name
    ob.scale=size; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    ob.data.materials.append(M[mat])
    # World-scale box UVs preserve texel density on long modular surfaces.
    uv=ob.data.uv_layers.active
    for poly in ob.data.polygons:
        axis=max(range(3),key=lambda a:abs(poly.normal[a])); axes=[a for a in range(3) if a!=axis]
        for li in poly.loop_indices:
            co=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(co[axes[0]]/4,co[axes[1]]/4)
    mod=ob.modifiers.new('authored_worn_edges','BEVEL'); mod.width=bevel; mod.segments=3
    return ob

def beam(name,a,b,w=.16,mat='oak'):
    d=Vector(b)-Vector(a); ob=box(name,(Vector(a)+Vector(b))/2,(w,w,d.length),mat,.02)
    ob.rotation_euler=d.to_track_quat('Z','Y').to_euler(); return ob

def roof(w,d,h,base,mat='slate',gable='stone'):
    verts=[(-w/2,-d/2,base),(w/2,-d/2,base),(0,-d/2,base+h),(-w/2,d/2,base),(w/2,d/2,base),(0,d/2,base+h)]
    mesh=bpy.data.meshes.new('steep_roof'); mesh.from_pydata(verts,[],[(0,1,2),(5,4,3),(0,2,5,3),(2,1,4,5),(3,4,1,0)])
    ob=bpy.data.objects.new('steep_roof',mesh); bpy.context.collection.objects.link(ob); ob.data.materials.append(M[mat]); ob.data.materials.append(M[gable])
    uv=mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        poly.material_index=1 if poly.index < 2 else 0
        for li in poly.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(co.x/4, (co.z if poly.index < 2 else co.y)/4)
    bpy.context.view_layer.objects.active=ob; ob.select_set(True)
    ob.select_set(False)
    for y in [-d/2,d/2]:
        beam('gable_trim',(-w/2,y,base),(0,y,base+h),.22); beam('gable_trim',(0,y,base+h),(w/2,y,base),.22)

def house(index=0, civic=False):
    w=10 if civic else [8,7,9,8,6,9][index%6]; d=10 if civic else 8
    h=11 if civic else 7+(index%3)*1.2
    facade=['brick','plaster_ochre','plaster_lime','plaster_sage','limestone','plaster_ochre'][index%6]
    if civic: facade='limestone'
    box('masonry_ground_floor',(0,0,2),(w,d,4),'limestone' if index%3==1 or civic else 'stone' if index%3==2 else 'brick')
    box('overhanging_upper_storeys',(0,0,(h+4)/2),(w+.4,d+.4,h-4),facade)
    for x in [-w/2,0,w/2]: box('timber_post',(x,-d/2-.38,h/2),(.24,.26,h),'oak')
    for z in [4,h]: box('timber_floor_rail',(0,-d/2-.4,z),(w+.7,.3,.25),'oak')
    for x in [-w*.28,w*.28]:
        for z in [2.7,h-1.6]:
            box('recessed_window',(x,-d/2-.24,z),(1.35,.12,1.7),'iron')
            box('warm_window',(x,-d/2-.33,z),(1.05,.12,1.42),'glow')
            box('window_mullion',(x,-d/2-.43,z),(.10,.12,1.5),'oak')
            box('stone_sill',(x,-d/2-.45,z-.9),(1.6,.45,.16),'stone')
    box('door_recess',(0,-d/2-.05,1.45),(2.2,.16,2.9),'iron')
    box('oak_door',(0,-d/2-.16,1.4),(1.8,.18,2.8),'oak')
    for side in [-1,1]:
        for yy in [-2,2]:
            box('side_window_recess',(side*(w/2+.27),yy,h-1.6),(.12,1.3,1.7),'iron')
            box('side_window_glass',(side*(w/2+.35),yy,h-1.6),(.08,1.0,1.4),'glow')
            box('side_window_mullion',(side*(w/2+.42),yy,h-1.6),(.08,.10,1.5),'oak')
        box('side_storey_beam',(side*(w/2+.35),0,4),(.25,d+.5,.25),'oak')
    roof(w+1,d+1,[4,3.3,4.8,4.1,5.2,3.6][index%6] if not civic else 6,h,['slate','terracotta','slate','copper','slate','terracotta'][index%6],facade)
    if index%3==1:
        for x in [-w*.28,w*.28]:
            for side in [-1,1]: box('painted_shutter',(x+side*.9,-d/2-.45,h-1.6),(.4,.14,1.65),'plaster_sage')
    if index%3==2:
        box('shop_awning',(0,-d/2-.65,3.5),(w*.6,1.0,.14),'canvas_red' if index%2 else 'canvas_gold')
        for x in [-w*.28,w*.28]: box('window_flowerbox',(x,-d/2-.45,h-2.7),(1.7,.6,.4),'oak')
    if index%2==0:
        box('gabled_dormer',(0,-1.5,h+1.2),(2,1.5,2),facade)
        box('dormer_window',(0,-2.3,h+1.2),(.8,.1,1),'glow')
        before=set(bpy.context.scene.objects);roof(2.4,2,1.2,h+2.2,'slate',facade)
        for ob in set(bpy.context.scene.objects)-before:ob.location.y-=1.5
    box('chimney',(w*.28,1,h+3),(.9,1,5),'brick'); box('chimney_cap',(w*.28,1,h+5.5),(1.2,1.3,.25),'stone')
    if index%2:
        beam('diagonal_brace',(-w/2,-d/2-.3,4.2),(0,-d/2-.3,h-.2),.18)
    if civic:
        for x in [-w/2-.6,w/2+.6]:
            for y in [-3,3]: box('buttress',(x,y,4),(1.2,1.3,8),'stone')

def arch(width=8,depth=3,height=7,mat='stone'):
    for x in [-width/2-.75,width/2+.75]: box('arch_pier',(x,0,height/2),(1.5,depth,height),mat)
    # Pointed arch made of individually beveled voussoirs.
    for side in [-1,1]:
        a=Vector((side*width/2,0,height)); b=Vector((0,0,height+width*.45))
        for i in range(7):
            p=a.lerp(b,(i+.5)/7); ob=box('arch_voussoir',p,(1.0,depth,(b-a).length/7+.03),mat)
            ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()

def wall(entry=False):
    box('wall_core',(0,0,6),(12,3,12),'stone')
    for y in [-1.25,1.25]:
        if entry and y < 0:
            for x in [-4,4]: box('parapet',(x,y,12.6),(4,.5,1.2),'stone')
        else: box('parapet',(0,y,12.6),(12,.5,1.2),'stone')
        for x in [-5,-3,-1,1,3,5]:
            if entry and y < 0 and abs(x)<2: continue
            box('merlon',(x,y,13.65),(1,.65,1),'stone')
    box('wall_belt',(0,0,8),(12.2,3.2,.35),'stone')

def tower():
    for z,w in [(5,9),(11,9.6)]: box('tower_stage',(0,0,z),(w,w,10 if z==5 else 2),'stone')
    for x in [-4,0,4]:
        for y in [-4,4]: box('tower_merlon',(x,y,13),(1.7,1.4,2),'stone')
    for x in [-4,4]: box('tower_side_merlon',(x,0,13),(1.4,1.7,2),'stone')
    for y in [-4.51,4.51]: box('arrow_slit',(0,y,7),(.3,.05,1.9),'iron')

def bridge(w=7):
    box('bridge_deck',(0,0,-.22),(w,12,.44),'paving')
    for x in [-w/2,w/2]:
        box('bridge_parapet',(x,0,.65),(.5,12,1.3),'stone')
        for y in [-5,0,5]: box('bridge_pier',(x,y,-.9),(.8,1.2,3.6),'stone')
    # Recessed archwork visible from the embankment.
    for x in [-w/2,w/2]:
        for i in range(10):
            t=math.pi*(i+.5)/10
            ob=box('bridge_arch_stone',(x,math.cos(t)*4,-2.4+math.sin(t)*1.8),(.55,.8,.45),'stone')
            ob.rotation_euler.x=t

def furnishing(kind):
    if kind=='lantern':
        box('lantern_post',(0,0,2),(.15,.15,4),'iron'); box('lantern_cage',(0,0,3.65),(.6,.6,.9),'iron')
        box('lantern_glass',(0,-.32,3.65),(.42,.06,.65),'glow'); roof(.8,.8,.4,4.1)
    elif kind=='stall':
        box('market_counter',(0,0,1),(3,1.4,1),'oak')
        for x in [-1.4,1.4]: box('stall_post',(x,0,1.8),(.16,.16,3.6),'oak')
        roof(3.8,2.5,.7,3.1)
    elif kind=='sign':
        box('hanging_sign',(0,0,2.8),(1.7,.18,.9),'oak'); box('sign_bracket',(0,0,3.5),(2,.16,.16),'iron')
    elif kind=='altar':
        box('altar',(0,0,.7),(3,1.5,1.4),'stone'); box('altar_top',(0,0,1.5),(3.3,1.8,.25),'stone')
        for x in [-1,1]: box('candle',(x,0,1.9),(.12,.12,.5),'glow')
    else:
        box('table',(0,0,1),(2.8,1.4,.22),'oak')
        for x in [-1.1,1.1]:
            for y in [-.5,.5]: box('table_leg',(x,y,.45),(.18,.18,.9),'oak')
        for y in [-1.1,1.1]: box('bench',(0,y,.55),(2.8,.4,.2),'oak')

def build(kind):
    if kind in CITADEL_KINDS or kind == 'citadel': build_citadel_asset(kind,M,box,roof,arch)
    elif kind in DETAIL_KINDS: build_detail(kind,M,box,beam,roof,house)
    elif kind.startswith('house_'): house(int(kind[-1])-1)
    elif kind in ['tavern_1','tavern_2','shop','apothecary','workshop']: house({'tavern_1':2,'tavern_2':4,'shop':1,'apothecary':3,'workshop':5}[kind]); furnishing('sign')
    elif kind in ['chapel','civic_hall']:
        house(0,True)
        if kind=='chapel':
            box('bell_tower',(0,2,15),(4,4,10),'stone'); roof(4.6,4.6,7,20)
    elif kind in ['wall','wall_entry']: wall(kind=='wall_entry')
    elif kind=='tower': tower()
    elif kind=='gatehouse': arch(10,5,7.5); box('gatehouse_upper',(0,0,11),(14,5,2),'stone')
    elif kind=='water_gate': box('watergate_upper',(0,0,10),(11,3,4)); arch(8,3,4); [box('watergate_bar',(x,0,1),(.18,.22,6),'iron') for x in range(-4,5)]
    elif kind=='portcullis':
        for x in range(-4,5): box('gate_bar',(x,0,4),(.16,.3,8),'iron')
        for z in [1,4,7]: box('gate_crossbar',(0,0,z),(10,.3,.18),'iron')
    elif kind.startswith('bridge'): bridge(8 if kind=='bridge_wide' else 4)
    elif kind=='embankment':
        box('quay_wall',(0,0,-1.5),(8,.8,3),'brick'); box('quay_coping',(0,0,.1),(8,1.1,.2),'stone')
    elif kind=='railing':
        for x in range(-4,5): box('railing_spindle',(x,0,.65),(.09,.09,1.3),'iron')
        for z in [.15,1.3]: box('rail',(0,0,z),(8,.12,.12),'iron')
    elif kind=='stairs':
        for i in range(24): box('stair_tread',(0,-11.5+i,.125*(i+1)),(3,1,.25*(i+1)),'stone')
    elif kind=='quay_stairs':
        for i in range(8): box('quay_step',(0,-3.5+i,-1.5+.2*i),(3,1,.4),'stone')
    elif kind=='arch': arch(4,1.2,3)
    elif kind=='paving': box('brick_paving',(0,0,-.03),(4,4,.06),'paving',.01)
    elif kind=='room':
        box('room_floor',(0,0,-.1),(12,12,.2),'oak')
        for x in [-6,6]: box('room_wall',(x,0,2.5),(.3,12,5),'brick')
        box('room_back',(0,6,2.5),(12,.3,5),'brick')
        for x in [-3.7,3.7]: box('room_entry_wall',(x,-6,2.5),(4.6,.3,5),'brick')
        for y in [-5,0,5]: box('ceiling_beam',(0,y,4.8),(12,.3,.4),'oak')
    else: furnishing(kind)

KINDS=[*[f'house_{i}' for i in range(1,7)],'tavern_1','tavern_2','shop','apothecary','workshop','chapel','civic_hall','wall','tower','gatehouse','water_gate','portcullis','bridge_wide','bridge_narrow','embankment','railing','stairs','quay_stairs','arch','paving','lantern','sign','stall','altar','table','room','citadel','wall_entry'] + DETAIL_KINDS + CITADEL_KINDS
requested=next((set(arg.split('=',1)[1].split(',')) for arg in sys.argv if arg.startswith('--assets=')),set())
assert requested.issubset(set(KINDS)), 'Unknown requested city asset'
report=json.loads((WORK/'build-report.json').read_text()) if requested else []
for kind in KINDS:
    if requested and kind not in requested: continue
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    build(kind)
    bpy.ops.object.select_all(action='SELECT')
    bpy.data.libraries.write(str(WORK/'sources'/f'{kind}.blend'), {bpy.context.scene}, fake_user=True, compress=True)
    # Evaluated source keeps all bevel detail. Runtime reduction is deterministic.
    bpy.context.view_layer.objects.active=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    if kind == 'citadel':
        for ob in bpy.context.scene.objects:
            for mod in ob.modifiers:
                if mod.type == 'BEVEL': mod.segments = 1
    bpy.ops.object.convert(target='MESH'); bpy.ops.object.join(); source=bpy.context.object
    source.name='aegis_'+kind
    bpy.context.scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    lods=[]
    for level,ratio in enumerate([1,.5,.2]):
        ob=source.copy(); ob.data=source.data.copy(); bpy.context.collection.objects.link(ob)
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob
        ob.data.calc_loop_triangles()
        budget_ratio = min(1, 29000 / len(ob.data.loop_triangles)) if kind == 'citadel' else 1
        if level or budget_ratio < 1:
            mod=ob.modifiers.new('runtime_lod','DECIMATE'); mod.ratio=ratio * budget_ratio
            bpy.ops.object.modifier_apply(modifier=mod.name)
        triangulate=ob.modifiers.new('export_triangles','TRIANGULATE'); bpy.ops.object.modifier_apply(modifier=triangulate.name)
        ob.data.calc_loop_triangles(); tris=len(ob.data.loop_triangles)
        name=f'prop_aegis_{kind}'+(f'_lod{level}' if level else '')+'.glb'; dest=OUT/name
        bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_yup=True,export_texcoords=True,export_normals=True,export_tangents=True)
        # The exporter removes degenerate faces left by decimation; report shipped geometry.
        data = dest.read_bytes()
        doc = json.loads(data[20:20 + int.from_bytes(data[12:16], 'little')])
        tris = sum(doc['accessors'][p['indices']]['count'] // 3 for mesh in doc['meshes'] for p in mesh['primitives'])
        lods.append({'level':level,'model':name,'triangles':tris,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
        bpy.data.objects.remove(ob,do_unlink=True)
    report=[asset for asset in report if asset['kind'] != kind]
    report.append({'kind':kind,'lods':lods})
    report.sort(key=lambda asset: KINDS.index(asset['kind']))
    (WORK/'build-report.json').write_text(json.dumps(report,indent=2))
    print('CITY_ASSET_COMPLETE',kind,flush=True)

if requested:
    sys.exit(0)

# Reimport actual exports into a single architectural review stage.
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for i,kind in enumerate(['house_1','house_2','tavern_1','chapel','gatehouse','bridge_wide']):
    bpy.ops.import_scene.gltf(filepath=str(OUT/f'prop_aegis_{kind}.glb'))
    for ob in bpy.context.selected_objects: ob.location.x+=(i%3)*20-20; ob.location.y+=(i//3)*25
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.world=bpy.data.worlds.new('Aegis review world'); scene.world.color=(.65,.65,.65)
bpy.ops.object.light_add(type='AREA',location=(5,-15,40)); bpy.context.object.data.energy=14000; bpy.context.object.data.shape='DISK'; bpy.context.object.data.size=30
bpy.ops.object.camera_add(location=(62,-75,58)); cam=bpy.context.object; cam.rotation_euler=(Vector((0,10,7))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=88; scene.camera=cam
scene.render.resolution_x=1800; scene.render.resolution_y=1300; scene.render.resolution_percentage=100
scene.render.filepath=str(WORK/'review'/'exported-kit.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'aegis_city_review.blend'))
