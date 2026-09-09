"""Close, literal exported-bird review; stage geometry is never exported."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from imported_actions import activate_imported_clip


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def render(folder, lod, state, view):
    model = ROOT / folder / f'frontier_sunmeadow_skylark_lod{lod}.glb'
    digest = sha(model)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(model))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    clip, _, phase = state.partition('@')
    action = activate_imported_clip(rig, meshes, clip)
    if action:
        first, last = action.frame_range
        frame = first + float(phase or 0) * (last - first)
        bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new('neutral_review_world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .21, .24, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .55
    ground = bpy.data.meshes.new('review_stage_only')
    ground.from_pydata([(-2, -2, -.0002), (2, -2, -.0002), (2, 2, -.0002), (-2, 2, -.0002)], [], [(0, 1, 2, 3)])
    stage = bpy.data.objects.new('review_stage_only', ground)
    scene.collection.objects.link(stage)
    material = bpy.data.materials.new('neutral_stage')
    material.diffuse_color = (.35, .38, .40, 1)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.35, .38, .40, 1)
    shader.inputs['Roughness'].default_value = .9
    ground.materials.append(material)
    for name, position, energy, size in [('key', (.5, -.7, 1), 35, .7), ('fill', (-.6, -.4, .5), 12, .6), ('rim', (.2, .6, .8), 25, .5)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = energy, 'DISK', size
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = position
        light.rotation_euler = (Vector((0, 0, .1)) - light.location).to_track_quat('-Z', 'Y').to_euler()
    camera = bpy.data.objects.new('review_camera', bpy.data.cameras.new('review_camera'))
    scene.collection.objects.link(camera)
    center = Vector((0, .01, .24 if clip == 'fly' and folder == 'runtime' else .09))
    direction = Vector((1, 0, .15) if view == 'profile' else (0, -1, .2) if view == 'front' else (1, -1.3, .55))
    camera.location = center + direction * .7
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    span = .46 if clip == 'fly' or folder == 'baseline' else .28
    camera.data.ortho_scale = span
    camera.data.clip_start = .001
    scene.camera = camera
    output = ROOT / 'review' / f'{folder}_lod{lod}_{state.replace("@", "_").replace(".", "p")}_{view}.png'
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    if sha(model) != digest:
        raise RuntimeError('Model changed during render')
    receipt = {'status': 'pending_visual_review', 'model': model.relative_to(ROOT).as_posix(), 'modelSha256': digest,
               'imageSha256': sha(output), 'toolSha256': sha(__file__), 'actionHelperSha256': sha(ROOT / 'tools/imported_actions.py'),
               'lod': lod, 'state': state, 'view': view, 'camera': {'orthoSpanM': span, 'position': list(camera.location), 'target': list(center)}}
    output.with_suffix('.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', choices=['baseline', 'runtime'], default='baseline')
    parser.add_argument('--lod', type=int, choices=[0, 1, 2], default=0)
    parser.add_argument('--states', default='idle@0,hop@0.5,fly@0.25,fly@0.75')
    parser.add_argument('--views', default='quarter')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    for state in args.states.split(','):
        for view in args.views.split(','):
            render(args.folder, args.lod, state, view)
