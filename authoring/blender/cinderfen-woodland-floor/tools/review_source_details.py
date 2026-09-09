"""Source-only close views of the large break and uneven side fork."""
import hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from review_floor import render
key='frontier_cinderfen_fallen_alder_limb'
master=ROOT/'masters'/f'{key}_lod0.source-preview.blend';bpy.ops.wm.open_mainfile(filepath=str(master))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
rows=[]
for name,target,frame,direction in [('large_break',(-1.62,-.16,.21),.75,(-1,-.42,.34)),('side_stub',(-.12,-.655,.515),.43,(1,-1,.7))]:
    path=ROOT/'review'/f'{key}_{name}_source.png';camera=render(objects,path,detail=True,detail_target=target,detail_frame=frame,camera_direction=direction)
    rows.append({'image':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'camera':camera})
(ROOT/'review/limb-source-details.json').write_text(json.dumps({'stage':'flat-color source geometry, not exported/PBR approval','masterSha256':hashlib.sha256(master.read_bytes()).hexdigest(),'toolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'views':rows},indent=2)+'\n')
