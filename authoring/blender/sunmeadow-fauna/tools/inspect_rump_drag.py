"""Measure caudal skin displacement in pelvis space on the actual base GLB."""
import json
import argparse
import math
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fauna import ROOT, resolve
from imported_actions import activate_imported_clip

parser = argparse.ArgumentParser(); parser.add_argument('--candidate-dir')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
delivery = ROOT/args.candidate_dir if args.candidate_dir else ROOT/'runtime'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(delivery/'frontier_sunmeadow_roe_deer_buck_lod0.glb'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
scale = resolve('roe_deer_buck')['scale']
rest = np.array([v.co[:] for v in obj.data.vertices])/scale
selected = (rest[:, 1]>.36)&(rest[:, 2]>.42)&(rest[:, 2]<.68)
records = []
for phase in [.125, .375, .625, .875]:
    action = activate_imported_clip(rig, [obj], 'run')
    first, last = action.frame_range; frame = first+(last-first)*phase
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame)); bpy.context.view_layer.update()
    inverse = (rig.pose.bones['pelvis'].matrix@rig.data.bones['pelvis'].matrix_local.inverted()).inverted()
    points = np.array([(inverse@v.co)[:] for v in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices])/scale
    delta = points-rest; indices = np.flatnonzero(selected); lowest = indices[np.argmin(delta[selected, 2])]
    record = {'phase': phase, 'samples': int(selected.sum()), 'mean_pelvis_relative_delta_m': (delta[selected].mean(axis=0)*scale).tolist(), 'lowest_delta_m': (delta[lowest]*scale).tolist(), 'rest': rest[lowest].tolist(), 'weights': {obj.vertex_groups[g.group].name: g.weight for g in obj.data.vertices[int(lowest)].groups}}
    records.append(record)
((delivery if args.candidate_dir else ROOT/'review')/'buck_rump_drag.json').write_text(json.dumps(records, indent=2)+'\n')
print(json.dumps(records, indent=2), flush=True)
