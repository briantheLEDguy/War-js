"""Render literal candidate GLBs with all imported armature/morph tracks active."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reimport_review import ROOT, setup, sha
from imported_actions import activate_imported_clip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lods', default='0')
    parser.add_argument('--states', default='run@0.125,run@0.625')
    parser.add_argument('--views', default='profile,quarter')
    parser.add_argument('--focus')
    parser.add_argument('--label', default='')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    base = ROOT/'review/candidates/buck_differential'
    records = []
    for level in map(int, args.lods.split(',')):
        model = base/f'frontier_sunmeadow_roe_deer_buck_lod{level}.glb'
        digest = sha(model)
        binary = model.read_bytes(); doc = json.loads(binary[20:20+int.from_bytes(binary[12:16], 'little')])
        for animation in doc['animations']:
            if not any(channel['target']['path'] == 'weights' for channel in animation['channels']):
                raise RuntimeError('Candidate omitted morph animation: '+animation['name'])
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(model))
        rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)]
        activate_imported_clip(rig, meshes, 'rest'); bpy.context.view_layer.update()
        _, camera = setup(meshes, base/'candidate.png', 1000, 20)
        for state in args.states.split(','):
            name, _, phase = state.partition('@')
            action = activate_imported_clip(rig, meshes, name)
            if action:
                first, last = action.frame_range; frame = first+(last-first)*float(phase or 0)
                bpy.context.scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame))
            bpy.context.view_layer.update()
            for view in args.views.split(','):
                direction = Vector((4, 0, .20) if view == 'profile' else (3, -2.1, .5) if view in ['quarter', 'full'] else (-3, -2.1, .5) if view == 'opposite' else (0, -4, .35))
                center = Vector((0, -.17, .64) if view == 'full' else (0, -.02, .47)); span = 1.65 if view == 'full' else 1.18
                if args.focus:
                    values = list(map(float, args.focus.split(',')))
                    if len(values) != 4 or values[3] <= 0: raise ValueError('Focus requires x,y,z,positive span')
                    center = Vector(values[:3]); span = values[3]
                camera.location = center+direction
                camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler(); camera.data.ortho_scale = span
                suffix = '_'+args.label if args.label else ''
                target = base/f'lod{level}_{state.replace("@", "_").replace(".", "p")}_{view}{suffix}.png'
                bpy.context.scene.render.filepath = str(target); bpy.ops.render.render(write_still=True)
                if sha(model) != digest: raise RuntimeError('Candidate changed during review')
                records.append({'level': level, 'state': state, 'view': view, 'focus': args.focus, 'model_sha256': digest, 'image': target.name, 'image_sha256': sha(target), 'reviewer_sha256': sha(__file__), 'action_helper_sha256': sha(ROOT/'tools/imported_actions.py'), 'status': 'pending_visual_review'})
                (base/'render_receipts.json').write_text(json.dumps({'renders': records}, indent=2)+'\n')
                print('CANDIDATE_RENDER', level, state, view, flush=True)


if __name__ == '__main__':
    main()
