"""Unpublished pose-correction experiment; this is not an export review receipt."""
import sys
import math
from pathlib import Path
import bpy
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from reimport_review import ROOT,setup

key='frontier_sunmeadow_roe_deer_buck'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters'/f'{key}.blend'))
rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
mesh=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH' and 'LOD0' in obj.name and any(mod.type=='ARMATURE' for mod in obj.modifiers))
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
group=mesh.vertex_groups.new(name='haunch_anatomical_correction')
for vertex in mesh.data.vertices:
    x,y,z=vertex.co
    weight=max(0,min(1,(z-.25)/.14))*max(0,min(1,(.82-z)/.12))*max(0,1-abs(y-.24)/.32)
    if weight>0:group.add([vertex.index],weight,'REPLACE')
modifier=mesh.modifiers.new('Draft_haunch_pose_volume','CORRECTIVE_SMOOTH')
modifier.factor=.9;modifier.iterations=12;modifier.smooth_type='LENGTH_WEIGHTED';modifier.use_only_smooth=False;modifier.vertex_group=group.name
mesh.hide_set(False);mesh.hide_render=False
output=ROOT/'review'/f'{key}_corrective_proof.png'
setup([mesh],output,800,16)
action=next(a for a in bpy.data.actions if a.name=='run');rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
first,last=action.frame_range;frame=first+(last-first)*.35;bpy.context.scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame));bpy.context.view_layer.update()
bpy.ops.render.render(write_still=True)
print('UNPUBLISHED_CORRECTIVE_PROOF',output)
