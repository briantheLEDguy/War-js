"""Replace crouch depth with a working hip hinge; existing geometry stays literal."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_common as common
import author_crew as author

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT/'masters/ram_crew_source_assembly.blend'))
report=json.loads((common.ROOT/'review/source_fit.json').read_text())
for label,sign in [('left',-1),('right',1)]:
    rig=bpy.data.objects['crew_'+label]
    seat=next(s for s in report['seats'] if s['seat']==label)
    fingers={b.name:b.matrix_basis.copy() for b in rig.pose.bones
             if any(b.name.startswith(f+'_') for f in (*author.FINGERS,'thumb'))}
    author.pose_operator(rig,sign,Vector(seat['origin_blender']),seat['board_heights'],Vector(),fingers)
master=common.ROOT/'masters/ram_crew_source_hinge.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(master))
common.render(common.ROOT/'review/source_hinge_interior.png',(0,-.1,1.86),(0,6,.05),3.25)
common.render(common.ROOT/'review/source_hinge_grips.png',(0,-.1,1.68),(.15,1.8,.6),1.65,(1300,1000))
