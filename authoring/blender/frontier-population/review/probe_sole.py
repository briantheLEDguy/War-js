import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(WORK/'tools'))
from tailored_locomotion import _solve_chain
bpy.ops.wm.open_mainfile(filepath=str(WORK/'sources/frontier_sunmeadow_dwarf_artisan.blend'))
rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
action=bpy.data.actions['death'];rig.animation_data.action=action
if action.slots:rig.animation_data.action_slot=action.slots[0]
for frame in (0,5,6,20,40,60):
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
    rows=[]
    for sign in (-1,1):
        obj=bpy.data.objects['fitted_boot_'+str(sign)]
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        rows.append({'side':sign,'bounds':min((evaluated.matrix_world@Vector(c)).z for c in evaluated.bound_box),
            'surface':min((evaluated.matrix_world@vertex.co).z for vertex in evaluated.data.vertices)})
    print(json.dumps({'frame':frame,'soles':rows}),flush=True)
bpy.context.scene.frame_set(5);bpy.context.view_layer.update()
foot=rig.pose.bones['foot_R'];ankle=foot.head.copy();rotation=foot.matrix.to_quaternion()
for step in range(5):
    obj=bpy.data.objects['fitted_boot_-1'];evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    low=min((evaluated.matrix_world@vertex.co).z for vertex in evaluated.data.vertices)
    print(json.dumps({'step':step,'height':low,'ankle':list(foot.head),'target':list(ankle)}),flush=True)
    ankle.z+=.004-low
    _solve_chain(rig,'R',ankle,rotation,hint=Vector((0,0,-1)))
