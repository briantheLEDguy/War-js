"""Pack existing images and set useful opening views without changing geometry."""
from pathlib import Path
import hashlib
import json
import bpy

ROOT=Path(__file__).resolve().parents[1]
records=[]
for name in ('ember_arcanist_reference_master.blend','ember_arcanist_game_master.blend','ember_arcanist_reimport_review.blend'):
    path=ROOT/name
    previous=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    camera=bpy.data.objects.get('comparison.full_three_quarter')
    if camera:
        bpy.context.scene.camera=camera
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.shading.type='MATERIAL'
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    records.append({'file':name,'before_sha256':previous,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
(ROOT/'review/delivery_master_preparation.json').write_text(json.dumps({'changes':'Packed image maps and opening camera only; runtime GLBs and validation unchanged','masters':records},indent=2)+'\n')
