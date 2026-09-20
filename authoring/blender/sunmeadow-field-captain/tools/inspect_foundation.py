"""Retain measured male anatomy before clothing or exposed-face deletion."""
import bpy,hashlib,json,gzip
from pathlib import Path
from mathutils import Vector
import numpy as np

WORK=Path(__file__).resolve().parents[1]
source=WORK/'foundations/body_civic_humanoid_v2_m.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
rig.animation_data_clear();rig.data.pose_position='REST'
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for obj in [rig,*meshes]:obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
scale=1.0
morph=lambda p:Vector((p[0]*scale,p[1]*scale,p[2]*scale))
for obj in meshes:
    for vertex in obj.data.vertices:vertex.co=morph(vertex.co)
bpy.ops.object.mode_set(mode='EDIT')
for bone in rig.data.edit_bones:bone.head=morph(bone.head);bone.tail=morph(bone.tail)
bpy.ops.object.mode_set(mode='OBJECT')
body=max(meshes,key=lambda o:len(o.data.vertices))
body.data.update()
bones={b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'length':b.length} for b in rig.data.bones}
points=np.array([tuple(v.co) for v in body.data.vertices])
quad=WORK/'foundations/civic_humanoid_v2_m.quad-surface.json.gz'
report={'status':'measured','foundationFamily':'civic_humanoid_v2_m','bodyVariant':'m','source':source.relative_to(WORK).as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'quadSurface':{'path':quad.relative_to(WORK).as_posix(),'sha256':hashlib.sha256(quad.read_bytes()).hexdigest()},'authoringScale':scale,'morphScale':[1,1,1],'boundsZUp':{'min':points.min(axis=0).tolist(),'max':points.max(axis=0).tolist()},'bones':bones,'vertices':len(points),'polygons':len(body.data.polygons),'note':'Reference retains male limb sections; captain arm gate transforms the literal male quad surface identically before comparison. No dwarf or Greenskin arm threshold.'}
(WORK/'review/male-foundation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='bones'}))
