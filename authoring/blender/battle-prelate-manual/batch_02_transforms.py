"""Apply five explicit object transforms; no generated or edited mesh data."""
import bpy
import hashlib
import json
from array import array
from pathlib import Path
from mathutils import Matrix, Vector

root = Path(__file__).resolve().parent
assert Path(bpy.data.filepath).parent == root
assert bpy.context.scene.get('bp_batch_01_applied')
assert not bpy.context.scene.get('bp_batch_02_applied')

def geometry_signature():
    result = {}
    for mesh in bpy.data.meshes:
        positions = array('f', [0.0]) * (3 * len(mesh.vertices))
        mesh.vertices.foreach_get('co', positions)
        indices = array('i', [0]) * len(mesh.loops)
        mesh.loops.foreach_get('vertex_index', indices)
        result[mesh.name] = hashlib.sha256(positions.tobytes() + indices.tobytes()).hexdigest()
    return result

before = geometry_signature()
objects_before = set(bpy.data.objects.keys())
edits = [
    ('BP_Shoulders_Pauldrons_High', (0, -0.01, 1.38), (1.25, 1.4, 1.5), (0, 0, 0.085)),
    ('BP_Shoulders_Lamellae_High', (0, -0.01, 1.38), (1.12, 1.25, 1.1), (0, 0, 0.06)),
    ('BP_Tabard_PrayerApron_High', (0, -0.04, 1.035), (1.2, 1, 1.18), (0, -0.008, 0)),
    ('BP_Back_CoatTails_High', (0, 0.14, 1.04), (1.17, 1, 1.22), (0, 0.012, 0)),
    ('BP_Waist_BeltFauld_High', (0, -0.02, 1.0), (1.16, 1.2, 1.1), (0, 0, 0.012)),
]
log = []
for name, pivot, scale, offset in edits:
    obj = bpy.data.objects[name]
    previous = obj.matrix_world.copy()
    transform = Matrix.Translation(Vector(pivot) + Vector(offset)) @ Matrix.Diagonal((*scale, 1)) @ Matrix.Translation(-Vector(pivot))
    obj.matrix_world = transform @ previous
    log.append({'object': name, 'pivot': pivot, 'scale': scale, 'offset': offset,
                'previous_matrix': [list(row) for row in previous],
                'new_matrix': [list(row) for row in obj.matrix_world]})

bpy.context.view_layer.update()
assert before == geometry_signature(), 'Mesh data unexpectedly changed.'
assert objects_before == set(bpy.data.objects.keys()), 'Objects unexpectedly created.'
bpy.context.scene['bp_batch_02_applied'] = True
(root / 'batch_02_report.json').write_text(json.dumps({'edits': log, 'mesh_data_unchanged': True,
    'object_count_unchanged': True}, indent=2), encoding='utf-8')
bpy.context.area.type = 'VIEW_3D'
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'battle_prelate_batch_study.blend'))
print('BATCH 02 COMPLETE: five object transforms; mesh data unchanged.')
