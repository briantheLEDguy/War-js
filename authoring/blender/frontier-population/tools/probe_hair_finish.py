"""Export only the revised hair response on the current master for close review."""
import bpy
import hashlib
import json
import sys
from pathlib import Path

WORK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(WORK/'tools'))
from authored_artisan_head import hair_material
from export_tangents import repair_export_tangents

source=WORK/'sources/frontier_sunmeadow_dwarf_artisan.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
material=hair_material()
meshes=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
for obj in meshes:
    for index,old in enumerate(obj.data.materials):
        if old and old.name.startswith('artisan_chestnut_directional_hair'):obj.data.materials[index]=material
    bpy.context.view_layer.objects.active=obj
    for modifier in list(obj.modifiers):
        if modifier.type in ('SUBSURF','SOLIDIFY'):
            while list(obj.modifiers).index(modifier)>0:bpy.ops.object.modifier_move_up(modifier=modifier.name)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:obj.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join()
body=bpy.context.view_layer.objects.active
matrix=body.matrix_world.copy();body.parent=None;body.matrix_world=matrix
rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE');rig.select_set(True)
output=WORK/'review/hair-material-proof.glb'
bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,export_animations=True,
                          export_tangents=True,export_animation_mode='ACTIONS',export_skins=True,export_morph=False)
repair_export_tangents(output)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
(WORK/'review/hair-material-proof.json').write_text(json.dumps({'status':'material_proof_only','masterSha256':sha(source),
    'shaderSourceSha256':sha(WORK/'tools/authored_artisan_head.py'),'modelSha256':sha(output),'visualApproval':False},indent=2))
