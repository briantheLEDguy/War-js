"""Diagnostic only: fit the current editable source, without replacing it."""
import bpy
import sys
from pathlib import Path
WORK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(WORK/'tools'))
from apron_clearance import fit_apron_clearance
bpy.ops.wm.open_mainfile(filepath=str(WORK/'sources/frontier_sunmeadow_dwarf_artisan.blend'))
rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
muted=[modifier for obj in bpy.context.scene.objects if obj.type=='MESH' for modifier in obj.modifiers if modifier.type=='ARMATURE' and modifier.show_viewport]
for modifier in muted:modifier.show_viewport=False
try:fit_apron_clearance(rig)
finally:
    for modifier in muted:modifier.show_viewport=True
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'review/apron-proof.blend'))
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
    if obj.type in ('ARMATURE','MESH'):obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(WORK/'review/apron-proof.glb'),export_format='GLB',use_selection=True,
    export_animations=True,export_animation_mode='ACTIONS',export_skins=True,export_morph=False,export_apply=True)
