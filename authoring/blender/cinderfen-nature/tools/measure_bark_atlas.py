"""Measure the actual face coverage from bounded UV packing alternatives."""
import bpy, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters/frontier_cinderfen_marsh_alder.blend'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and '.joined_lod0' in o.name)
bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
obj.data.uv_layers.active_index=obj.data.uv_layers.find('authored_uv')
records=[]
for margin in [.0005]:
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(68),island_margin=margin,area_weight=.8,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.uv.pack_islands(rotate=True,rotate_method='ANY',scale=True,margin_method='FRACTION',margin=margin,shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    uv=obj.data.uv_layers['authored_uv'].data
    area=0
    for face in obj.data.polygons:
        coords=[uv[i].uv for i in face.loop_indices]
        area+=abs(sum(a.x*b.y-b.x*a.y for a,b in zip(coords,coords[1:]+coords[:1])))*.5
    records.append({'margin':margin,'occupiedFraction':area})
    print('ATLAS_MEASUREMENT',records[-1],flush=True)
(ROOT/'review/bark-atlas-measurements.json').write_text(json.dumps(records,indent=2)+'\n')
