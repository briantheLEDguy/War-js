"""Low interior cameras reveal both crew contacts without hiding ram geometry."""
import sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import crew_common as common

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT/'masters/ram_crew_source_assembly.blend'))
common.render(common.ROOT/'review/source_interior_rear.png',(0,-.1,1.86),(0,6,.05),3.25)
common.render(common.ROOT/'review/source_grip_close.png',(.53,-.18,1.7),(0,2.8,.3),1.15,(1300,1000))
