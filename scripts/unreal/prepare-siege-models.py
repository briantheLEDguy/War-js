"""Build unadmitted Chaos caster adaptations from retained authored sources.

Writes only private siege artifacts. Equipped native review and admission are
separate; these meshes never replace a missing combatant at runtime.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/unreal/siege/animation'
MODELS = OUT / 'models'
SOURCE = ROOT / 'public/assets/models/chr_riftspire_chaos.glb'
BASE = ROOT / 'artifacts/unreal/animation-replacement'
STAFF = BASE / 'models/EmberStaff/EmberStaff.glb'
for required in (SOURCE, STAFF, BASE/'sources.json', BASE/'models/civic_ember_arcanist_m/civic_ember_arcanist_m.glb'):
    if not required.is_file(): raise RuntimeError('Required retained source is missing: '+str(required))
MODELS.mkdir(parents=True, exist_ok=True)


def imported(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before]


def material(name, color, metallic=0):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    shader = result.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = .78 if not metallic else .38
    return result


def remove_baked_equipment(obj):
    # This retained mesh joins equipment into the body. Remove whole disconnected
    # hand-bound islands outside the measured gauntlet bounds, preserving fingers.
    adjacent = {v.index: set() for v in obj.data.vertices}
    for edge in obj.data.edges:
        a, b = edge.vertices
        adjacent[a].add(b); adjacent[b].add(a)
    unseen, removed, old_tabard = set(adjacent), set(), set()
    while unseen:
        stack = [unseen.pop()]; island = set(stack)
        while stack:
            for vertex in adjacent[stack.pop()] & unseen:
                unseen.remove(vertex); island.add(vertex); stack.append(vertex)
        groups = {obj.vertex_groups[g.group].name for i in island
                  for g in obj.data.vertices[i].groups if g.weight > .1}
        points = [obj.matrix_world @ obj.data.vertices[i].co for i in island]
        # Keep the fitted armor silhouette; remove hanging cloth and trim
        # whose pelvis/thigh skinning intersects in the supplied casting poses.
        if ('hips' in groups and groups & {'thigh_L','thigh_R'}
            and groups <= {'hips','thigh_L','thigh_R'}
            and min(p.z for p in points) < .9 and max(p.z for p in points) < 1.18
            and max(abs(p.x) for p in points) < .3
            and (max(p.y for p in points) < -.13 or min(p.y for p in points) > .09)):
            old_tabard.update(island)
        if groups in ({'hand_L'}, {'hand_R'}) and any(p.z < 1.04 or p.z > 1.19 or abs(p.x) > .61 for p in points):
            removed.update(island)
    if len(removed) != 141:
        raise RuntimeError('Retained Chaos equipment topology changed; remeasure before adapting')
    if len(old_tabard) != 646:
        raise RuntimeError('Retained Chaos tabard topology changed; remeasure before adapting: '+str(len(old_tabard)))
    removed.update(old_tabard)
    mesh = bmesh.new(); mesh.from_mesh(obj.data); mesh.verts.ensure_lookup_table()
    bmesh.ops.delete(mesh, geom=[mesh.verts[i] for i in removed], context='VERTS')
    mesh.to_mesh(obj.data); mesh.free(); obj.data.update()


def export(name, objects):
    directory = MODELS/name; directory.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.hide_set(False); obj.select_set(True)
    bpy.context.view_layer.objects.active = next(o for o in objects if o.type == 'MESH')
    glb = directory/(name+'.glb'); fbx = directory/(name+'.fbx')
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True, export_animations=False)
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH','ARMATURE','EMPTY'},
        axis_forward='-Y', axis_up='Z', global_scale=1., apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
        add_leaf_bones=False, use_armature_deform_only=False, use_triangles=True, bake_anim=False)
    return dict(source=glb.relative_to(ROOT).as_posix(), fbx=fbx.relative_to(ROOT).as_posix(),
        sourceSha256=hashlib.sha256(glb.read_bytes()).hexdigest(), fbxSha256=hashlib.sha256(fbx.read_bytes()).hexdigest(), animations=[])


def render(profile):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 640; scene.render.resolution_y = 800; scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new('SiegeSourceReviewWorld'); scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.045,.04,.035,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .5
    for location, energy, size in (((-3,-4,5),750,4),((3,-1,3),500,3),((0,3,4),850,3)):
        data=bpy.data.lights.new('ReviewLight','AREA'); data.energy=energy; data.shape='DISK'; data.size=size
        light=bpy.data.objects.new('ReviewLight',data); scene.collection.objects.link(light); light.location=location
        light.rotation_euler=(Vector((0,0,1.1))-light.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('ReviewCamera'); camera=bpy.data.objects.new('ReviewCamera',data); scene.collection.objects.link(camera)
    camera.location=(0,-6,1.5); camera.rotation_euler=(Vector((0,0,1.1))-camera.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO'; data.ortho_scale=2.8; scene.camera=camera
    scene.render.filepath=str(OUT/(profile+'-source.png'))
    bpy.ops.render.render(write_still=True)


receipts = {}
for profile, color in (('riven_ruin_oracle_m',(.18,.018,.028)), ('riven_void_magister_m',(.055,.025,.14))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    old_body = imported(BASE/'models/civic_ember_arcanist_m/civic_ember_arcanist_m.glb')
    old_rig = next(o for o in old_body if o.type == 'ARMATURE')
    old_palm = old_rig.matrix_world @ old_rig.data.bones['hand_R'].head_local
    for obj in old_body: bpy.data.objects.remove(obj, do_unlink=True)
    body = imported(SOURCE)
    rig = next(o for o in body if o.type == 'ARMATURE')
    for obj in body:
        obj.animation_data_clear()
        if obj.type == 'ARMATURE':
            obj.data.pose_position = 'REST'
            for bone in obj.pose.bones: bone.matrix_basis = Matrix.Identity(4)
        elif obj.type == 'MESH':
            if any(mod.type == 'ARMATURE' for mod in obj.modifiers): remove_baked_equipment(obj)
            for slot in obj.material_slots:
                if slot.material and 'crimson' in slot.material.name:
                    slot.material = material(profile+'_vestment', color)
    weapon = [o for o in imported(STAFF) if o.type == 'MESH']
    delta = rig.matrix_world @ rig.data.bones['hand_R'].head_local - old_palm
    for obj in weapon:
        obj.location += delta
        obj.animation_data_clear()
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    bpy.context.view_layer.update()
    receipt = export(profile,body)
    receipt['weapon'] = export(profile+'_ritual_staff',weapon)
    receipt['adaptedFrom'] = dict(path=SOURCE.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    receipt['rig'] = dict(bones=len(rig.data.bones), worldScale=list(rig.scale), rightPalm=list(rig.matrix_world@rig.data.bones['hand_R'].head_local))
    receipt['artApproval'] = False
    receipts[profile] = receipt
    render(profile)
shutil.copyfile(BASE/'sources.json',OUT/'sources.json')
bpy.ops.wm.read_factory_settings(use_empty=True)
idol_source = ROOT/'public/assets/models/prop_riftspire_altar.glb'
idol = imported(idol_source)
meshes = [o for o in idol if o.type == 'MESH']
points = [o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
center = Vector(((low.x+high.x)/2, (low.y+high.y)/2, low.z))
scale = .9/max(high.x-low.x, high.y-low.y)
# Preserve the authored altar silhouette/materials; make a portable 90 cm idol.
for obj in meshes:
    transform = obj.matrix_world.copy()
    obj.parent = None; obj.matrix_world = Matrix.Identity(4)
    for vertex in obj.data.vertices: vertex.co = (transform @ vertex.co-center)*scale
    obj.animation_data_clear()
receipts['WarpIdol'] = export('WarpIdol', meshes)
receipts['WarpIdol']['adaptedFrom'] = dict(path=idol_source.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(idol_source.read_bytes()).hexdigest())
render('WarpIdol')
(OUT/'model-sources.json').write_text(json.dumps(dict(schemaVersion=1,profiles=receipts),indent=2)+'\n',encoding='utf-8')
print('WAR_SIEGE_SOURCE_MODELS=2; native equipment review and admission are still required')
