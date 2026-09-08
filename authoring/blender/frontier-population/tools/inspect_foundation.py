"""Inspect retained local humanoid anatomy without modifying the source master."""
import bpy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
source = ROOT / 'artifacts/model-jobs/local-character-batch-20260713-152623/civic_humanoid_v2_m/source.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
report = {'source': str(source.relative_to(ROOT)), 'objects': [], 'images': []}
for ob in bpy.context.scene.objects:
    entry = {'name': ob.name, 'type': ob.type, 'dimensions': list(ob.dimensions), 'location': list(ob.location)}
    if ob.type == 'MESH':
        entry.update(vertices=len(ob.data.vertices), faces=len(ob.data.polygons),
                     materials=[m.name for m in ob.data.materials if m],
                     groups=[g.name for g in ob.vertex_groups], uvLayers=[l.name for l in ob.data.uv_layers])
    if ob.type == 'ARMATURE':
        entry['bones'] = [{'name': b.name, 'head': list(b.head_local), 'tail': list(b.tail_local)} for b in ob.data.bones]
    report['objects'].append(entry)
for image in bpy.data.images:
    report['images'].append({'name': image.name, 'path': image.filepath, 'packed': bool(image.packed_file), 'size': list(image.size)})
(WORK / 'review').mkdir(parents=True, exist_ok=True)
(WORK / 'review/foundation-inspection.json').write_text(json.dumps(report, indent=2))
print(json.dumps({'objects': [(o['name'], o['type'], o.get('vertices')) for o in report['objects']], 'images': report['images']}))
