import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fauna import ROOT

base = ROOT/'review/candidates/buck_differential'
bpy.ops.wm.open_mainfile(filepath=str(base/'frontier_sunmeadow_roe_deer_buck.blend'))
for action in bpy.data.actions:
    print('ACTION_SLOTS', action.name, [(s.identifier, s.target_id_type, s.name_display) for s in action.slots], flush=True)
for obj in bpy.data.objects:
    if obj.type != 'MESH' or not obj.data.shape_keys:
        continue
    print('SHAPE_DATABLOCK', obj.name, obj.data.shape_keys.name, [(t.name, len(t.strips)) for t in obj.data.shape_keys.animation_data.nla_tracks], flush=True)
    level = next(i for i in range(3) if f'_LOD{i}' in obj.name)
    np.save(base/f'lod{level}_rest.npy', np.array([v.co[:] for v in obj.data.vertices]))
