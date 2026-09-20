"""Measure retained arm surfaces in rest and literal animation poses."""
import bpy
import json
import math
import sys
import hashlib
import struct
import gzip
import numpy as np
from pathlib import Path
from mathutils import Vector

WORK = Path(__file__).resolve().parents[1]
lod = next((int(a.split('=',1)[1]) for a in sys.argv if a.startswith('--lod=')), None)
SOURCE = WORK / (f'runtime/frontier_sunmeadow_empire_herbalist_lod{lod}.glb' if lod is not None
                 else 'sources/frontier_sunmeadow_empire_herbalist.blend')
override=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--source=')),None)
if override:SOURCE=Path(override).resolve()
if lod is None: bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
body = max((o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_render),key=lambda o:len(o.data.vertices)) if lod is not None else bpy.data.objects['empire_herbalist_exposed_anatomy']
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

def section(vertices, edges, bone, fraction):
    axis = (bone.tail - bone.head).normalized()
    origin = bone.head.lerp(bone.tail, fraction)
    x = bone.matrix.to_3x3().col[0].normalized()
    y = axis.cross(x).normalized()
    p, q = vertices[edges[:,0]], vertices[edges[:,1]]
    da, db = (p-np.array(origin))@np.array(axis), (q-np.array(origin))@np.array(axis)
    selected = da*db < 0
    hit = p[selected]+(q[selected]-p[selected])*(da[selected]/(da[selected]-db[selected]))[:,None]-np.array(origin)
    hit = hit[np.linalg.norm(hit,axis=1)<.16]
    points = np.stack((hit@np.array(x),hit@np.array(y)),axis=1)
    if len(points) == 0: return {'hits': 0}
    angles = sorted(math.atan2(y, x) for x, y in points)
    gaps = [b-a for a,b in zip(angles, angles[1:]+[angles[0]+math.tau])]
    ordered=points[np.argsort(np.arctan2(points[:,1],points[:,0]))]
    area=abs(np.sum(ordered[:,0]*np.roll(ordered[:,1],-1)-ordered[:,1]*np.roll(ordered[:,0],-1)))/2
    return {'hits': len(points), 'area':float(area), 'span': [float(np.ptp(points[:,i])) for i in range(2)],
            'largestAngularGapDegrees': math.degrees(max(gaps)),
            'radiusMin': min(math.hypot(*p) for p in points), 'radiusMax': max(math.hypot(*p) for p in points)}

records = []
skin_faces = [face for face in body.data.polygons if '.body' in body.data.materials[face.material_index].name]
skin_edges = {tuple(sorted((a,b))) for face in skin_faces for a,b in zip(tuple(face.vertices),tuple(face.vertices[1:])+tuple(face.vertices[:1]))}
edges = np.array(sorted(skin_edges),dtype=int)
foundation=WORK.parents[2]/'authoring/blender/frontier-population/foundations/civic_humanoid_v2_f.quad-surface.json.gz'
reference=json.loads(gzip.decompress(foundation.read_bytes()))
reference_points=np.array(reference['vertices'])*(1.86/1.76)
reference_edges=np.array(sorted({tuple(sorted((a,b))) for face in reference['faces'] for a,b in zip(face,face[1:]+face[:1])}),dtype=int)
reference_sections={f'forearm_{side}_{t}':section(reference_points,reference_edges,rig.pose.bones['forearm_'+side],t)
                    for side in ['L','R'] for t in [.52,.6,.75,.9]}
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
reference_span_ratios=[a/b for name,measurement in reference_sections.items() for a,b in zip(baseline[name]['span'],measurement['span'])]
for record in records[1:]:
    for name,measurement in record['sections'].items():
        ratios.append(measurement['area']/baseline[name]['area'])
report = {'source':str(SOURCE.relative_to(WORK)),'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'importedTriangles':imported_triangles,'sampleCount':len(records),'minimumAreaRatio':min(ratios),'maximumAreaRatio':max(ratios),
          'largestAngularGapDegrees':max(s['largestAngularGapDegrees'] for r in records for s in r['sections'].values()),'records':records}
report['femaleFoundation']={'path':foundation.relative_to(WORK.parents[2]).as_posix(),'sha256':hashlib.sha256(foundation.read_bytes()).hexdigest(),
                           'authoringScale':1.86/1.76,'sections':reference_sections,
                           'minimumReferenceSpanRatio':min(reference_span_ratios),'maximumReferenceSpanRatio':max(reference_span_ratios)}
out = WORK / 'review' / next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report=')), 'arm-volume-inspection.json')
out.write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='records'}))
if report['minimumAreaRatio'] < .80 or report['maximumAreaRatio'] > 1.20:
    raise RuntimeError('Exposed arm volume changes by more than 20 percent during locomotion')
if report['largestAngularGapDegrees'] > 75:
    raise RuntimeError('Exposed arm cross-section has missing circumference')
if min(reference_span_ratios)<.9 or max(reference_span_ratios)>1.1:
    raise RuntimeError('Exposed arm thickness differs more than ten percent from its actual female anatomical foundation')
