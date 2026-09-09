import math
import json
import hashlib
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reimport_review import ROOT
from imported_actions import activate_imported_clip

base = ROOT/'review/candidates/buck_differential'
bpy.ops.wm.read_factory_settings(use_empty=True)
model = base/'frontier_sunmeadow_roe_deer_buck_lod0.glb'
payload = model.read_bytes(); length = int.from_bytes(payload[12:16], 'little')
doc = json.loads(payload[20:20+length]); binary = payload[28+length:]
def dense_scalar(index):
    accessor = doc['accessors'][index]
    if accessor['type'] != 'SCALAR' or accessor['componentType'] != 5126 or 'sparse' in accessor:
        raise RuntimeError('Expected dense scalar animation samples')
    view = doc['bufferViews'][accessor['bufferView']]
    return np.ndarray((accessor['count'],), dtype='<f4', buffer=binary, offset=view.get('byteOffset', 0)+accessor.get('byteOffset', 0), strides=(view.get('byteStride', 4),))
bpy.ops.import_scene.gltf(filepath=str(model))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.data.shape_keys)
action = activate_imported_clip(rig, [mesh], 'run')
first, last = action.frame_range; frame = first+(last-first)*.125
bpy.context.scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame)); bpy.context.view_layer.update()
animation = next(a for a in doc['animations'] if a['name'] == 'run')
channel = next(c for c in animation['channels'] if c['target']['path'] == 'weights')
sampler = animation['samplers'][channel['sampler']]
if sampler.get('interpolation', 'LINEAR') != 'LINEAR': raise RuntimeError('Expected portable linear sample interpolation')
times = dense_scalar(sampler['input']); values = dense_scalar(sampler['output']).reshape(len(times), -1)
seconds = times[0]+(times[-1]-times[0])*.125
expected = np.array([np.interp(seconds, times, values[:, i]) for i in range(values.shape[1])])
actual = np.array([k.value for k in mesh.data.shape_keys.key_blocks[1:]])
error = float(np.abs(expected-actual).max())
report = {'model_sha256': hashlib.sha256(payload).hexdigest(), 'helper_sha256': hashlib.sha256((ROOT/'tools/imported_actions.py').read_bytes()).hexdigest(), 'phase': .125, 'maximum_weight_error': error, 'expected_signed_range': [float(expected.min()), float(expected.max())], 'modes': len(expected), 'passed': error < 5e-5}
(base/'literal_weight_inspection.json').write_text(json.dumps(report, indent=2)+'\n')
print('LITERAL_WEIGHT_COMPARISON', report, flush=True)
if error >= 5e-5: raise RuntimeError('Imported review does not match actual glTF weights')
