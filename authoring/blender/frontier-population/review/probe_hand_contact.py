import sys
from pathlib import Path
import bpy
import numpy as np
work=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(work/'tools'))
from apron_clearance import _surface,_skin
from tailored_locomotion import _solve_chain
from mathutils import Vector,Quaternion
bpy.ops.wm.open_mainfile(filepath=str(work/'sources/frontier_sunmeadow_dwarf_artisan.blend'))
rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
rig.animation_data.action=bpy.data.actions['death'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
bpy.context.scene.frame_set(60)
body=bpy.data.objects['dwarf_artisan_exposed_anatomy'];surface=_surface(body)
for side in ('L','R'):
    indices=sorted({int(index) for name,(ids,weights) in surface[2].items() if name.endswith('_'+side) and name.startswith(('hand_','index_','middle_','ring_','pinky_','thumb_')) for index in ids})
    points=_skin(surface,rig);index=min(indices,key=lambda i:points[i,2])
    print('CURRENT',side,'wrist',list(rig.pose.bones['hand_'+side].head),'lowest',points[index].tolist(),'rest',surface[0][index].tolist(),
          'weights',[(name,float(weights[np.flatnonzero(ids==index)[0]])) for name,(ids,weights) in surface[2].items() if index in ids])
    if side=='L':
        hand=rig.data.bones['hand_'+side]
        aligned=(hand.tail_local-hand.head_local).rotation_difference(Vector((.08,-1,0)))@hand.matrix_local.to_quaternion()
        aligned=Quaternion(Vector((1,0,0)),-.35)@aligned
        _solve_chain(rig,side,Vector((.39,.06,.075)),aligned,('upper_arm','forearm','hand'),Vector((1,0,0)))
        points=_skin(surface,rig);index=min(indices,key=lambda i:points[i,2])
        print('LOW TARGET',side,'wrist',list(rig.pose.bones['hand_'+side].head),'lowest',points[index].tolist(),'rest',surface[0][index].tolist(),
              'weights',[(name,float(weights[np.flatnonzero(ids==index)[0]])) for name,(ids,weights) in surface[2].items() if index in ids])
