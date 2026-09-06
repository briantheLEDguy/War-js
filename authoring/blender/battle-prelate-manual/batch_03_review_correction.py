"""Undo shoulder transforms rejected during visual review; retain cloth edits."""
import bpy
import json
from pathlib import Path
from mathutils import Matrix

root = Path(__file__).resolve().parent
report_path = root / 'batch_02_report.json'
report = json.loads(report_path.read_text(encoding='utf-8'))
rejected = {'BP_Shoulders_Pauldrons_High', 'BP_Shoulders_Lamellae_High'}
for edit in report['edits']:
    if edit['object'] in rejected:
        bpy.data.objects[edit['object']].matrix_world = Matrix(edit['previous_matrix'])
        edit['review'] = 'reverted: shoulder pieces detached from the body'
    else:
        edit['review'] = 'retained in rough study; no final quality approval'
report['retained_transform_count'] = 3
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
bpy.context.view_layer.update()
bpy.context.scene['bp_batch_03_reviewed'] = True
bpy.context.area.type = 'VIEW_3D'
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'battle_prelate_batch_study.blend'))
