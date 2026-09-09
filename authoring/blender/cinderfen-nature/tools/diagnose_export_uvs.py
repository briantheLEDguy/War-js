"""Test the actual bake UV as the sole exported stream, retaining master UVs."""
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters/frontier_cinderfen_marsh_alder.blend'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    for name in [layer.name for layer in obj.data.uv_layers if layer.name!='authored_uv']:
        obj.data.uv_layers.remove(obj.data.uv_layers[name])
    obj.data.uv_layers.active_index=0;obj.data.uv_layers[0].active_render=True;obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.gltf(filepath=str(ROOT/'review/diagnostic_alder_uv_finalization.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_tangents=True,export_texcoords=True,export_normals=True)
