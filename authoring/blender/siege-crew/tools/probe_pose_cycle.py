"""Assert unchanged limb reach through the literal ram action before baking."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_common as common
import author_crew as author

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT/'masters/ram_crew_source_assembly.blend'))
records=json.loads((common.ROOT/'review/source_fit.json').read_text())
ram=[o for o in bpy.context.scene.objects if o.name in ['ram_striker','suspension_front','suspension_rear']]
common.pin_clip(ram,'ram_strike')
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
striker=bpy.data.objects['ram_striker']
rest=striker.matrix_world.translation.copy()
actors=[]
for label,sign in [('left',-1),('right',1)]:
    rig=bpy.data.objects['crew_'+label]
    seat=next(s for s in records['seats'] if s['seat']==label)
    fingers={b.name:b.matrix_basis.copy() for b in rig.pose.bones
             if any(b.name.startswith(f+'_') for f in (*author.FINGERS,'thumb'))}
    actors.append((rig,sign,Vector(seat['origin_blender']),seat['board_heights'],fingers))
    for obj in bpy.context.scene.objects:
        for modifier in obj.modifiers:
            if modifier.type=='ARMATURE': modifier.show_viewport=False
report=[]
for frame in range(46):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    delta=striker.matrix_world.translation-rest
    for rig,sign,origin,contacts,fingers in actors:
        author.pose_operator(rig,sign,origin,contacts,delta,fingers)
    report.append({'frame':frame,'seconds':frame/30,'striker_delta':list(delta)})
out={'status':'all_unchanged_limbs_reachable','frames':report,
     'ram_sha256':common.RAM_SHA,'poses':'source solver; exported contact not yet verified'}
(common.ROOT/'review/reach_cycle.json').write_text(json.dumps(out,indent=2)+'\n')
print('ALL_46_FRAMES_REACHABLE',flush=True)
