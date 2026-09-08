"""Inspect the actual wagon, horse, reins and published equipped avatar GLBs."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_collection as build

ROOT = build.ROOT
PROJECT = ROOT.parents[2]
PUBLIC = PROJECT / 'public/assets/models'


def imported(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.context.scene.objects if obj not in before]


def active(objects, name):
    found = False
    for obj in objects:
        if not obj.animation_data: continue
        obj.animation_data.action = None
        for track in obj.animation_data.nla_tracks:
            track.mute = track.name != name
            found |= not track.mute
    if not found: raise ValueError(f'Missing literal clip: {name}')


def root_offset(objects, offset):
    for obj in objects:
        if obj.parent not in objects: obj.location += Vector(offset)


def snapshots(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    result = []
    for obj in objects:
        if obj.type != 'MESH' or obj.hide_render or not obj.visible_get(): continue
        evaluated = obj.evaluated_get(graph)
        mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=graph)
        for vertex in mesh.vertices: vertex.co = obj.matrix_world @ vertex.co
        proof = bpy.data.objects.new('review.'+obj.name, mesh)
        bpy.context.scene.collection.objects.link(proof)
        result.append(proof)
    return result


def clear_review_lights():
    for obj in list(bpy.context.scene.objects):
        if obj.type in {'LIGHT','CAMERA'}: bpy.data.objects.remove(obj, do_unlink=True)


def equipped_actor(catalog, load):
    body_record = catalog['characterProfiles']['civic_battle_prelate_m']
    body = load(PUBLIC/body_record['model'], body_record['modelSha256'])
    rig = next(obj for obj in body if obj.type == 'ARMATURE')
    rig['review_idle_action'] = next(track for track in rig.animation_data.nla_tracks if track.name == 'idle').strips[0].action.name
    rig.animation_data_clear()
    for bone in rig.pose.bones: bone.matrix_basis = Matrix.Identity(4)
    hidden = set()
    equipment = []
    for key in sorted(catalog['equipment']):
        if not key.startswith('novitiate_civic_battle_prelate_'): continue
        definition = catalog['equipment'][key]['variants']['m']
        if definition['approvalState'] != 'approved': raise ValueError('Unreviewed equipment in caravan proof')
        objects = load(PUBLIC/definition['model'], definition['modelSha256'])
        overlay_rig = next(obj for obj in objects if obj.type == 'ARMATURE')
        for name in overlay_rig.data.bones:
            if name.name not in rig.data.bones: raise ValueError('Equipment skeleton mismatch')
        for obj in objects:
            if obj.type != 'MESH' or obj.hide_render: continue
            matrix = obj.matrix_world.copy()
            obj.parent = rig
            obj.matrix_world = matrix
            for modifier in obj.modifiers:
                if modifier.type == 'ARMATURE': modifier.object = rig
            equipment.append(obj)
        hidden.update(definition.get('coveredRegions', []))
        bpy.data.objects.remove(overlay_rig, do_unlink=True)
    for obj in body:
        if obj.get('bodyRegion') in hidden:
            obj.hide_render = True
            obj.hide_set(True)
    return rig, body, equipment, hidden


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    catalog = json.loads((PUBLIC / 'asset-index.json').read_text())
    inputs = []
    def load(path, expected=None):
        actual = build.sha(path)
        if expected and actual != expected: raise ValueError(f'Published hash changed: {path.name}')
        inputs.append({'path':str(path.relative_to(PROJECT)), 'sha256':actual})
        return imported(path)
    rig, body, equipment, hidden = equipped_actor(catalog, load)
    pack = load(ROOT/'runtime/frontier_teamster_animations.glb')
    pack_rig = next(obj for obj in pack if obj.type == 'ARMATURE')
    driver_track = next(track for track in pack_rig.animation_data.nla_tracks if track.name == 'driver_seated')
    action = driver_track.strips[0].action
    rest_error = max(abs(value) for bone in pack_rig.data.bones
                     for row in rig.data.bones[bone.name].matrix_local-bone.matrix_local for value in row)
    if rest_error > .001: raise ValueError(f'Animation bind pose differs from approved body: {rest_error}')
    rig.animation_data_create()
    rig.animation_data.action = action
    if action.slots: rig.animation_data.action_slot = action.slots[0]
    bpy.data.objects.remove(pack_rig, do_unlink=True)
    pose = json.loads((ROOT/'review/frontier_teamster_animations_build.json').read_text())
    origin = pose['avatar_origin_wagon_local_gltf']
    root_offset(body, (origin[0], -origin[2], origin[1]))
    wagon = load(ROOT/'runtime/frontier_supply_wagon_lod0.glb')
    active(wagon, 'caravan_roll')
    horse = load(ROOT/'runtime/frontier_draft_horse_lod0.glb')
    active(horse, 'idle')
    root_offset(horse, (0,-3.75,0))
    reins = load(ROOT/'runtime/frontier_caravan_reins_lod0.glb')
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    driver = snapshots(body+equipment)
    other = snapshots(wagon+horse+reins)
    for obj in body+equipment+wagon+horse+reins:
        if obj.type == 'MESH': obj.hide_render = True; obj.hide_set(True)
    images = []
    for name, framed in [('frontier_caravan_assembled', driver+other), ('frontier_caravan_driver_close', driver)]:
        clear_review_lights()
        output = ROOT/'review'/f'{name}.png'
        build.set_view(framed, output)
        images.append({'path':str(output.relative_to(ROOT)), 'sha256':build.sha(output)})
    (ROOT/'review/frontier_caravan_assembly.json').write_text(json.dumps({
        'status':'pending_visual_review','inputs':inputs,'images':images,
        'canonical_rest_matrix_max_error':rest_error, 'hidden_body_regions':sorted(hidden),
        'method':'Literal published GLBs, canonical rest-matrix comparison, skeleton rebinding and actual exported driver pose'},indent=2)+'\n')


if __name__ == '__main__': main()
