"""Original civic decorations; Blender Z-up, facade faces -Y (glTF +Z).

Independent of the architecture bake: rebuilds only civic sources/exports and
an actual-export review sheet. No downloaded artwork, symbols or textures.
"""
import bpy
import math
import json
import hashlib
from pathlib import Path
from mathutils import Vector

WORK = Path(__file__).resolve().parents[1]
for folder in ['sources', 'runtime', 'review']:
    (WORK / folder).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
M = {}
for name, color, metal, rough in [
    ('iron', (.035, .055, .065), .8, .32),
    ('brass', (.55, .32, .095), .78, .28),
    ('ivory', (.72, .67, .48), .12, .28),
    ('teal', (.025, .19, .18), .28, .24),
    ('wine', (.22, .035, .055), .1, .37),
    ('oak', (.19, .075, .025), 0, .55),
    ('stone', (.40, .43, .40), 0, .8),
    ('glass', (.9, .48, .12), .1, .18),
]:
    mat = bpy.data.materials.new('aegis_civic_' + name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Roughness'].default_value = rough
    if name == 'glass':
        bsdf.inputs['Emission Color'].default_value = (1, .48, .12, 1)
        bsdf.inputs['Emission Strength'].default_value = 2
    M[name] = mat


def finish(ob, name, mat, bevel=0):
    ob.name = name
    ob.data.materials.append(M[mat])
    if bevel:
        mod = ob.modifiers.new('cast_edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    return ob


def box(name, pos, size, mat='brass', bevel=.018):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    ob = bpy.context.object
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(ob, name, mat, bevel)


def cylinder(name, pos, radius, depth, mat='brass', radius2=None, vertices=16):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius,
        radius2=radius if radius2 is None else radius2, depth=depth, location=pos)
    return finish(bpy.context.object, name, mat, .012)


def ball(name, pos, radius, mat='brass', scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=radius, location=pos)
    ob = bpy.context.object
    ob.scale = scale
    return finish(ob, name, mat)


def line(name, points, radius=.025, mat='brass'):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 1
    spline = curve.splines.new('POLY')
    spline.points.add(len(points)-1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1)
    ob = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(ob)
    curve.materials.append(M[mat])
    return ob


def ring(name, pos, radius, tube=.025, mat='brass', vertical=True, start=0, end=2*math.pi):
    x, y, z = pos
    return line(name, [(x+radius*math.cos(t), y if vertical else y+radius*math.sin(t),
        z+radius*math.sin(t) if vertical else z)
        for t in [start+(end-start)*i/32 for i in range(33)]], tube, mat)


def text(body, pos, size=.17, mat='ivory'):
    curve = bpy.data.curves.new('lettering_' + body, 'FONT')
    curve.body = body
    curve.align_x = 'CENTER'
    curve.size = size
    curve.extrude = .002
    curve.resolution_u = 3
    ob = bpy.data.objects.new('lettering_' + body, curve)
    bpy.context.collection.objects.link(ob)
    ob.location = pos
    ob.rotation_euler.x = math.pi/2
    curve.materials.append(M[mat])


def scroll(cx, y, cz, side=1, radius=.35):
    line('rolled_iron_scroll', [(cx+side*radius*(1-i/65)*math.cos(i*.15), y,
        cz+radius*(1-i/65)*math.sin(i*.15)) for i in range(55)], .028, 'iron')


def lantern(x, y, z, size=1):
    # A real six-sided cage with warm emissive panes and a vented copper crown.
    cylinder('amber_panes', (x, y, z), .22*size, .52*size, 'glass', vertices=6)
    for dz in [-.29, .29]:
        cylinder('cage_rim', (x, y, z+dz*size), .29*size, .075*size, 'brass', vertices=6)
    for i in range(6):
        a = i*math.pi/3
        box('cage_mullion', (x+.24*size*math.cos(a), y+.24*size*math.sin(a), z),
            (.035*size, .035*size, .61*size), 'iron', .006)
    cylinder('lantern_roof', (x, y, z+.43*size), .37*size, .25*size, 'teal', .085*size, 6)
    cylinder('vent', (x, y, z+.60*size), .085*size, .12*size, 'iron', vertices=6)
    ball('roof_finial', (x, y, z+.70*size), .07*size)
    cylinder('pendant_drop', (x, y, z-.43*size), .09*size, .2*size, 'brass', .03*size)


def streetlight():
    cylinder('stone_plinth', (0, 0, .12), .47, .24, 'stone', vertices=8)
    cylinder('moulded_foot', (0, 0, .34), .28, .28, 'iron', .18)
    cylinder('fluted_column', (0, 0, 2.22), .105, 3.65, 'iron', .075)
    for z in [.5, .7, 2.85, 3.6, 4.0]:
        cylinder('brass_collar', (0, 0, z), .145, .085)
    for i in range(8):
        a = i*math.pi/4
        line('column_flute', [(.108*math.cos(a), .108*math.sin(a), .75),
            (.085*math.cos(a), .085*math.sin(a), 2.8)], .009)
    for side in [-1, 1]:
        line('swept_arm', [(0, 0, 3.65), (side*.28, 0, 4.15), (side*.7, 0, 4.32),
            (side*1.05, 0, 4.15), (side*1.05, 0, 3.95)], .055, 'iron')
        scroll(side*.42, 0, 3.9, side, .29)
        lantern(side*1.05, 0, 3.25, 1.1)
    cylinder('column_crown', (0, 0, 4.24), .17, .32, 'brass', .025)
    ball('crown_bead', (0, 0, 4.43), .09)
    for y in [-.12, .12]:
        ring('civic_oval', (0, y, 3.16), .22, .018)


def wall_lantern():
    box('wall_backplate', (0, .015, .34), (.24, .10, .7), 'iron')
    for z in [.08, .60]:
        ball('mounting_bolt', (0, -.055, z), .035)
    line('arched_wall_arm', [(0, 0, .57), (0, -.25, .92), (0, -.59, .94), (0, -.73, .78)], .05, 'iron')
    lantern(0, -.73, .13, .88)
    ring('wall_brace', (0, -.31, .43), .20, .025, 'brass', vertical=False)


def sign(kind):
    box('oak_backboard', (0, 0, 2.83), (2.20, .16, 1.52), 'oak', .08)
    box('enameled_face', (0, -.096, 2.83), (2.04, .055, 1.36), 'wine' if kind == 'lantern' else 'teal', .05)
    for x in [-1.04, 1.04]:
        box('vertical_gilt_border', (x, -.137, 2.83), (.045, .035, 1.40))
    for z in [2.14, 3.52]:
        box('horizontal_gilt_border', (0, -.137, z), (2.12, .035, .045))
    for x in [-.94, .94]:
        for z in [2.24, 3.42]:
            ball('board_rosette', (x, -.165, z), .045)
    box('wall_mount', (0, .27, 3.68), (.18, .18, .6), 'iron')
    box('hanging_crossbar', (0, .01, 3.89), (2.40, .12, .12), 'iron')
    for x in [-.77, .77]:
        for z in [3.60, 3.70, 3.80]:
            ring('chain_link', (x, 0, z), .065, .015, 'iron')
        scroll(x*.60, 0, 4.07, 1 if x > 0 else -1, .23)
    # Original trade pictograms: an oil lantern, canal key, leaves and three seals.
    if kind == 'lantern':
        box('pictogram_glass', (0, -.17, 3.02), (.30, .045, .40), 'ivory')
        for x in [-.19, .19]:
            box('pictogram_cage', (x, -.2, 3.03), (.045, .04, .48))
        line('pictogram_cap', [(-.27,-.2,3.29),(0,-.2,3.48),(.27,-.2,3.29)], .038)
        box('pictogram_base', (0,-.2,2.78), (.47,.04,.06))
        label, sub = 'THE SABLE LANTERN', 'ROOMS  /  TABLE'
    elif kind == 'lock':
        ring('key_bow', (-.29,-.20,3.15), .18, .045)
        line('key_stem', [(-.12,-.2,3.15),(.50,-.2,3.15),(.50,-.2,2.94)], .045)
        box('key_tooth', (.30,-.2,3.04), (.07,.05,.18))
        for z in [2.83, 2.91]:
            line('water_line', [(x/10,-.20,z+.018*math.sin(x)) for x in range(-6,7)], .012, 'ivory')
        label, sub = 'THE LOCKKEEPER', 'QUAYSIDE HOUSE'
    elif kind == 'apothecary':
        line('herb_stem', [(0,-.21,2.79),(0,-.21,3.40)], .023)
        for i in range(4):
            side = (-1)**i
            leaf = ball('carved_herb_leaf', (side*.16,-.2,2.91+i*.115), .15, 'ivory', (1.25,.16,.52))
            leaf.rotation_euler.y = -side*.5
        label, sub = 'CINDERLEAF', 'APOTHECARY'
    else:
        for x,z in [(-.3,3.0),(.3,3.0),(0,3.3)]:
            ring('merchant_seal', (x,-.21,z), .15, .025)
            ball('seal_center', (x,-.19,z), .095, 'ivory', (1,.20,1))
        label, sub = 'THREE SEALS', 'EXCHANGE'
    text(label, (0,-.17,2.51), .14)
    text(sub, (0,-.17,2.29), .095, 'brass')
    # Finished reverse face for free-hanging use; storefront placement shows front.
    box('back_inlay', (0,.092,2.83), (1.96,.025,1.26), 'teal')


def relief():
    box('relief_frame', (0,0,1.1), (2.6,.20,2.2), 'stone', .055)
    box('ceramic_field', (0,-.12,1.12), (2.35,.08,1.9), 'teal')
    for x in [-1.21,1.21]:
        box('relief_gilt_side', (x,-.19,1.1), (.055,.06,2.05))
    for z in [.12,2.1]:
        box('relief_gilt_top', (0,-.19,z), (2.46,.06,.055))
    # Canal sunrise: curved horizon and bridge arches, deliberately no heraldry.
    ring('sun_disc', (.48,-.205,1.64), .26, .042, 'brass')
    for i in range(3):
        x = -.72+i*.72
        ring('bridge_arch', (x,-.23,.83), .30, .055, 'ivory', start=0, end=math.pi)
        box('bridge_pier', (x-.32,-.22,.78), (.11,.10,.57), 'ivory')
    box('bridge_deck', (0,-.23,1.23), (2.20,.10,.12), 'ivory')
    for i in range(15):
        box('balustrade', (-1.02+i*.146,-.23,1.38), (.045,.08,.22), 'brass', .006)
    for row in range(4):
        line('inlaid_canal_wave', [(x/20,-.24,.35+row*.095+.027*math.sin(x*.65+row)) for x in range(-20,21)], .015, 'ivory')
    text('THE CITY WE BUILD TOGETHER', (0,-.25,.17), .092)


def bench():
    for x in [-1.12,1.12]:
        for y in [-.32,.32]:
            line('splayed_bench_leg', [(x,y*1.4,.07),(x,y,.52),(x,y,.72)], .065, 'iron')
        ring('cast_bench_end', (x,0,.62), .36, .035, 'brass', vertical=False)
        line('armrest', [(x,-.43,.70),(x,-.43,.89),(x,.38,.89)], .05, 'iron')
    for y in [-.30,-.10,.10,.30]:
        box('oak_seat_slat', (0,y,.53), (2.8,.17,.10), 'oak', .025)
    for z in [.87,1.12,1.37]:
        box('teal_back_slat', (0,.40,z), (2.8,.12,.19), 'teal', .03)
        for x in [-1.1,1.1]:
            ball('slat_rivet', (x,.325,z), .022)
    for x in [-1.1,1.1]:
        box('back_stanchion', (x,.46,.96), (.10,.10,1.05), 'iron')
    box('dedication_plate', (0,.315,1.12), (.74,.045,.16))
    text('A PLACE FOR ALL', (0,.285,1.085), .066, 'iron')


def orrery():
    for z,r,d,mat in [(.12,.87,.24,'stone'),(.31,.73,.15,'brass'),(.83,.53,.93,'stone'),(1.36,.67,.14,'brass')]:
        cylinder('observatory_pedestal', (0,0,z), r,d,mat, vertices=8)
    ball('central_world', (0,0,2.36), .23, 'teal')
    for radius, tilt in [(.75,0),(.86,.9),(.98,-.75)]:
        ob = ring('orbital_instrument', (0,0,0), radius, .035)
        ob.location.z = 2.36
        ob.rotation_euler.z = tilt
    ring('equatorial_instrument', (0,0,2.36), .85, .035, 'brass', vertical=False)
    for i in range(12):
        a=i*math.pi/6
        ball('hour_marker', (.86*math.cos(a),.86*math.sin(a),2.36), .046, 'ivory')
    line('axis', [(0,0,1.40),(0,0,3.48)], .045, 'iron')
    ball('axis_finial', (0,0,3.53), .075)
    box('observatory_plaque', (0,-.505,.93), (.66,.055,.26), 'teal')
    text('COMMON SKY', (0,-.54,.91), .085)


def waymarker():
    cylinder('waymarker_base', (0,0,.1), .38,.2,'stone', vertices=8)
    cylinder('waymarker_post', (0,0,1.68), .085,3.15,'iron')
    for i,(label, mat) in enumerate([('MARKET','teal'),('QUAYS','wine'),('CIVIC HALL','teal')]):
        z=2.90-i*.44
        box('enameled_direction', (0,-.10,z), (1.64,.13,.34), mat, .05)
        for x in [-.77,.77]:
            ball('sign_bolt', (x,-.18,z), .025)
        text(label, (0,-.18,z-.055), .13)
    # Directory labels are neutral: no arrows that could point down a wrong street.
    ring('directory_crest', (0,0,3.42), .18,.028)
    text('BASTION', (0,-.12,1.85), .105, 'brass')


BUILDERS = {'streetlight': streetlight, 'wall_lantern': wall_lantern,
    **{'sign_'+k: (lambda k=k: sign(k)) for k in ['lantern','lock','apothecary','exchange']},
    'relief': relief, 'bench': bench, 'orrery': orrery, 'waymarker': waymarker}
report = []
for kind, build in BUILDERS.items():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    build()
    bpy.data.libraries.write(str(WORK/'sources'/f'civic_{kind}.blend'), {bpy.context.scene}, fake_user=True, compress=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = next(iter(bpy.context.selected_objects))
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    source = bpy.context.object
    source.name = 'aegis_civic_' + kind
    bpy.context.scene.cursor.location = (0,0,0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    # Curves/text gain a UV layer so every primitive remains pipeline-compatible.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    lods = []
    for level, ratio in enumerate([1,.52,.24]):
        ob = source.copy()
        ob.data = source.data.copy()
        bpy.context.collection.objects.link(ob)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        if level:
            mod = ob.modifiers.new('distance_reduction', 'DECIMATE')
            mod.ratio = ratio
            bpy.ops.object.modifier_apply(modifier=mod.name)
        mod = ob.modifiers.new('triangulate', 'TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.data.calc_loop_triangles()
        model = f'prop_aegis_civic_{kind}' + (f'_lod{level}' if level else '') + '.glb'
        file = WORK/'runtime'/model
        bpy.ops.export_scene.gltf(filepath=str(file), export_format='GLB', use_selection=True,
            export_yup=True, export_texcoords=True, export_normals=True)
        lods.append({'level':level, 'model':model, 'triangles':len(ob.data.loop_triangles),
            'bytes':file.stat().st_size, 'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
        bpy.data.objects.remove(ob, do_unlink=True)
    report.append({'kind':'civic_'+kind, 'lods':lods})
    print('CIVIC_ASSET_COMPLETE', kind, flush=True)
(WORK/'civic-build-report.json').write_text(json.dumps(report, indent=2)+'\n')

# Review the actual LOD0 exports, all at the same scale, facing the viewer.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for i, asset in enumerate(report):
    bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/asset['lods'][0]['model']))
    for ob in bpy.context.selected_objects:
        ob.location.x += (i%5)*4.3-8.6
        ob.location.y += (i//5)*6.2
        if asset['kind'] == 'civic_wall_lantern': ob.location.z += 2.7
box('review_floor', (0,3,-.15), (25,17,.2), 'stone')
scene = bpy.context.scene
scene.world = bpy.data.worlds.new('civic_review_daylight')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.35,.42,.5,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
for pos, energy, size in [((1,-8,14),2400,10),((-10,3,10),1800,8)]:
    bpy.ops.object.light_add(type='AREA', location=pos)
    ob=bpy.context.object
    ob.data.energy=energy
    ob.data.shape='DISK'
    ob.data.size=size
    ob.rotation_euler=(Vector((0,2,1.5))-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(5,-23,18))
cam=bpy.context.object
cam.rotation_euler=(Vector((0,3,1.7))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'
cam.data.ortho_scale=25
scene.camera=cam
scene.render.engine='CYCLES'
scene.cycles.samples=24
scene.render.resolution_x=2000
scene.render.resolution_y=1200
scene.render.resolution_percentage=100
scene.render.filepath=str(WORK/'review/civic-exports.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'review/civic-exports.blend'))
