"""Anchor arm dimensions to retained female anatomy with the authored racial scale."""
import bpy,hashlib,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1];ROOT=WORK.parents[2]
sys.path.insert(0,str(WORK/'tools'))
from arm_sections import section
source=WORK.parent/'frontier-population/foundations/body_civic_humanoid_v2_f.glb'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data_clear()
body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m and m.name.endswith('.body') for m in o.data.materials))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
scale=(.97,.96,1.045)
for v in body.data.vertices:v.co=Vector([v.co[i]*scale[i] for i in range(3)])
bpy.ops.object.mode_set(mode='EDIT')
for bone in rig.data.edit_bones:
    bone.head=Vector([bone.head[i]*scale[i] for i in range(3)]);bone.tail=Vector([bone.tail[i]*scale[i] for i in range(3)])
bpy.ops.object.mode_set(mode='OBJECT')
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
points=np.array([v.co[:] for v in body.data.vertices]);edges=np.array([tuple(e.vertices) for e in body.data.edges])
sections={f'{part}_{side}_{t}':section(points,edges,rig.pose.bones[part+'_'+side],t)
          for side in ('L','R') for part,fractions in [('forearm',[.52,.6,.75,.9]),('hand',[.3,.6])] for t in fractions}
report={'source':source.relative_to(ROOT).as_posix(),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'racialScale':scale,'sections':sections,'criterion':'Every exported rest/animated section span must remain within 10% of the scaled retained female foundation; separate 20% area-change and 75-degree angular-coverage gates remain.'}
(WORK/'review/female-arm-foundation.json').write_text(json.dumps(report,separators=(',',':')))
print(json.dumps({'minimumForearmSpan':min(min(v['span']) for k,v in sections.items() if k.startswith('forearm')),'sourceSha256':report['sourceSha256']}))
