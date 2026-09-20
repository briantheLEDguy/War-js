"""Measure retained arm surfaces in rest and literal animation poses."""
import bpy
import json
import math
import sys
import hashlib
import struct
import numpy as np
from pathlib import Path
from mathutils import Vector

WORK = Path(__file__).resolve().parents[1]
lod = next((int(a.split('=',1)[1]) for a in sys.argv if a.startswith('--lod=')), None)
SOURCE = WORK / (f'runtime/frontier_cinderfen_dark_elf_supply_officer_lod{lod}.glb' if lod is not None
                 else 'sources/frontier_cinderfen_dark_elf_supply_officer.blend')
override=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--source=')),None)
if override:SOURCE=Path(override).resolve()
if lod is None: bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
body = max((o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_render),key=lambda o:len(o.data.vertices)) if lod is not None else bpy.data.objects['dark_elf_supply_officer_exposed_anatomy']
body.data.calc_loop_triangles();imported_triangles=len(body.data.loop_triangles)
if lod is not None:
    raw=SOURCE.read_bytes();document=json.loads(raw[20:20+int.from_bytes(raw[12:16],'little')])
    expected=sum(document['accessors'][primitive['indices']]['count']//3 for mesh in document['meshes'] for primitive in mesh['primitives'])
    if imported_triangles!=expected:raise RuntimeError('Volume inspection imported a different mesh than the hashed GLB')
actions = {action.name:action for action in bpy.data.actions}
for track in rig.animation_data.nla_tracks: track.mute = True
rig.animation_data.action = None
for bone in rig.pose.bones: bone.matrix_basis.identity()
bpy.context.view_layer.update()

sys.path.insert(0,str(WORK/'tools'))
from arm_sections import section

records = []
skin_faces = [face for face in body.data.polygons if '.body' in body.data.materials[face.material_index].name]
skin_edges = {tuple(sorted((a,b))) for face in skin_faces for a,b in zip(tuple(face.vertices),tuple(face.vertices[1:])+tuple(face.vertices[:1]))}
edges = np.array(sorted(skin_edges),dtype=int)
samples = [('rest',0),('idle',0),('idle',1),('walk',0),('walk',.25),('walk',.5),('run',0),('run',1/6),('run',1/3)]
if lod is None and '--dense' in sys.argv:
    samples=[('rest',0)]+[(clip,half_frame/60) for clip,duration in [('idle',60),('walk',30),('run',20)] for half_frame in range(duration*2+1)]
if lod is not None:
    binary=SOURCE.read_bytes();length=int.from_bytes(binary[12:16],'little')
    document=json.loads(binary[20:20+length]);data=binary[28+length:]
    samples=[('rest',0)]
    for animation in document['animations']:
        if animation['name'] not in ('idle','walk','run'): continue
        times=set()
        for sampler in animation['samplers']:
            accessor=document['accessors'][sampler['input']];view=document['bufferViews'][accessor['bufferView']]
            offset=view.get('byteOffset',0)+accessor.get('byteOffset',0)
            times.update(round(struct.unpack_from('<f',data,offset+i*view.get('byteStride',4))[0],8) for i in range(accessor['count']))
        keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]))
        samples.extend((animation['name'],seconds) for seconds in sorted(times))
for clip, seconds in samples:
    action = None if clip == 'rest' else next(a for name,a in actions.items() if name==clip or name.endswith('_'+clip))
    rig.animation_data.action = action
    if rig.animation_data.action and rig.animation_data.action.slots:
        rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    for bone in rig.pose.bones: bone.matrix_basis.identity()
    frame=seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base+(1 if lod is not None else 0)
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    transform=rig.matrix_world.inverted()@body.matrix_world
    points = np.array([tuple(transform@v.co) for v in evaluated.data.vertices])
    records.append({'clip': clip, 'seconds': seconds, 'sections': {
        f'{part}_{side}_{t}': section(points,edges,rig.pose.bones[part+'_'+side],t)
        for side in ['L','R'] for part, fractions in [('forearm',[.52,.6,.75,.9]),('hand',[.3,.6])]
        for t in fractions}})
baseline=records[0]['sections'];ratios=[]
for record in records[1:]:
    for name,measurement in record['sections'].items():
        ratios.append(measurement['area']/baseline[name]['area'])
reference_path=WORK/'review/female-arm-foundation.json'
reference=json.loads(reference_path.read_text())
foundation=WORK.parents[2]/reference['source']
if hashlib.sha256(foundation.read_bytes()).hexdigest()!=reference['sourceSha256']:raise RuntimeError('Female anatomy baseline is stale')
span_ratios=[measurement['span'][axis]/reference['sections'][name]['span'][axis] for record in records for name,measurement in record['sections'].items() for axis in range(2)]
report = {'source':str(SOURCE.relative_to(WORK)),'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'foundationReportSha256':hashlib.sha256(reference_path.read_bytes()).hexdigest(),'minimumFoundationSpanRatio':min(span_ratios),'maximumFoundationSpanRatio':max(span_ratios),'importedTriangles':imported_triangles,'sampleCount':len(records),'minimumAreaRatio':min(ratios),'maximumAreaRatio':max(ratios),
          'largestAngularGapDegrees':max(s['largestAngularGapDegrees'] for r in records for s in r['sections'].values()),'records':records}
out = WORK / 'review' / next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report=')), 'arm-volume-inspection.json')
out.write_text(json.dumps(report,separators=(',',':')))
print(json.dumps({k:v for k,v in report.items() if k!='records'}))
if report['minimumAreaRatio'] < .80 or report['maximumAreaRatio'] > 1.20:
    raise RuntimeError('Exposed arm volume changes by more than 20 percent during locomotion')
if report['largestAngularGapDegrees'] > 75:
    raise RuntimeError('Exposed arm cross-section has missing circumference')
if report['minimumFoundationSpanRatio']<.90 or report['maximumFoundationSpanRatio']>1.10:
    raise RuntimeError('Exposed arm section differs from retained female anatomy by more than 10 percent')
