"""Read the isolated basalt bevel tangent before choosing a source correction."""
import json,math
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters/frontier_cinderfen_basalt_outcrop.blend'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render)
bpy.context.view_layer.objects.active=obj
for m in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
data=obj.data
original_uv=[list(v.uv) for v in data.uv_layers['authored_uv'].data]
original_normals=[list(v.vector) for v in data.corner_normals]
rows=[]
def audit(stage):
    data.calc_tangents(uvmap='authored_uv')
    invalid=[l.index for l in data.loops if l.tangent.length<.99]
    rows.append({'stage':stage,'invalid':invalid,'customNormals':data.has_custom_normals,'normalChangeMax':max(sum((a-b)**2 for a,b in zip(old,new.vector)) for old,new in zip(original_normals,data.corner_normals)),'faceNormals':[list(data.corner_normals[i].vector) for i in data.polygons[10984].loop_indices],'uv':[list(data.uv_layers['authored_uv'].data[i].uv) for i in data.polygons[10984].loop_indices]})
    data.free_tangents();print(stage,invalid,flush=True);return invalid
audit('original_finished')
data.uv_layers['authored_uv'].name='retained_fracture_uv';data.uv_layers.new(name='authored_uv');data.uv_layers.active_index=1;data.uv_layers['authored_uv'].active_render=True
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(52),island_margin=4/2048,area_weight=.8,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
audit('smart_project')
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.pack_islands(rotate=True,rotate_method='ANY',scale=True,margin_method='FRACTION',margin=4/2048,shape_method='CONCAVE');bpy.ops.object.mode_set(mode='OBJECT')
bad=audit('packed')
packed_uv=[list(v.uv) for v in data.uv_layers['authored_uv'].data]
data.uv_layers.remove(data.uv_layers['retained_fracture_uv']);data.update();audit('runtime_uv_only')
for item,co in zip(data.uv_layers['authored_uv'].data,original_uv):item.uv=co
data.update();audit('restored_original_uv')
for item,co in zip(data.uv_layers['authored_uv'].data,packed_uv):item.uv=co
data.normals_split_custom_set(original_normals);data.update();audit('packed_restored_original_normals')
corrected=list(original_normals)
for face in data.polygons:
    if any(i in bad for i in face.loop_indices):
        for i in face.loop_indices:corrected[i]=list(face.normal)
data.normals_split_custom_set(corrected);data.update();audit('packed_corrected_face_normals')
(ROOT/'review/basalt_tangent_diagnosis.json').write_text(json.dumps(rows,indent=2)+'\n')
