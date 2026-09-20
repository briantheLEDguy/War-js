import bpy,sys,math,json
from pathlib import Path
root=Path('authoring/blender/frontier-workshop-items').resolve()
sys.path.insert(0,str(root/'tools'))
from materials_items import apply_materials
key='frontier_siege_ammunition_cradle';lod=0
bpy.ops.wm.open_mainfile(filepath=str(root/'masters'/f'{key}_lod{lod}.source.blend'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
fields=apply_materials(objects);parts=[]
for obj in objects:
    names={obj.data.materials[p.material_index].name.split('.')[-1] for p in obj.data.polygons}
    batch='timber' if names<={'oak','oak_end','working_oak'} else 'metal' if names<={'forged_iron','worked_steel'} else 'loads'
    if batch=='loads':parts.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();obj=parts[0];data=obj.data
margin=4/2048
data.uv_layers.new(name='runtime_uv');data.uv_layers.active_index=len(data.uv_layers)-1;data.uv_layers['runtime_uv'].active_render=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=margin,area_weight=.9,correct_aspect=True,scale_to_bounds=True);bpy.ops.uv.pack_islands(rotate=True,rotate_method='ANY',scale=True,margin_method='FRACTION',margin=margin,shape_method='CONCAVE');bpy.ops.object.mode_set(mode='OBJECT')
data.calc_tangents(uvmap='runtime_uv');invalid=[l.index for l in data.loops if l.tangent.length<.99]
print('INVALID',invalid,flush=True)
for loop in invalid:
    corner=data.loops[loop];vertex=corner.vertex_index
    faces=[f for f in data.polygons if vertex in f.vertices]
    print('LOOP',loop,'NORMAL',list(data.corner_normals[loop].vector),'POSITION',list(data.vertices[vertex].co),'NEIGHBORS',json.dumps([{'i':f.index,'smooth':f.use_smooth,'normal':list(f.normal),'area':f.area,'material':data.materials[f.material_index].name} for f in faces]),flush=True)
invalidfaces=[f for f in data.polygons if any(i in invalid for i in f.loop_indices)]
data.free_tangents()
for f in invalidfaces:
    uv=data.uv_layers['runtime_uv'].data
    original=[uv[i].uv.copy() for i in f.loop_indices]
    for deg in [90,45,30,60]:
        c=math.cos(math.radians(deg));s=math.sin(math.radians(deg));centre=sum(original,original[0].copy()*0)/3
        for i,p in zip(f.loop_indices,original):
            q=p-centre;uv[i].uv=(centre.x+q.x*c-q.y*s,centre.y+q.x*s+q.y*c)
        data.calc_tangents(uvmap='runtime_uv');print('ROTATION',deg,'INVALID',[(l.index,list(l.tangent)) for l in data.loops if l.tangent.length<.99],flush=True);data.free_tangents();uv=data.uv_layers['runtime_uv'].data
        for i,p in zip(f.loop_indices,original):uv[i].uv=p
# Check the actual update path before altering smooth normals.
for f in invalidfaces:
    uv=data.uv_layers['runtime_uv'].data;original=[uv[i].uv.copy() for i in f.loop_indices]
    centre=sum(original,original[0].copy()*0)/3
    for i,p in zip(f.loop_indices,original):q=p-centre;uv[i].uv=(centre.x-q.y,centre.y+q.x)
data.update();data.calc_tangents(uvmap='runtime_uv');print('UPDATED_ROTATION_INVALID',[(l.index,list(l.tangent)) for l in data.loops if l.tangent.length<.99],flush=True);data.free_tangents()
normals=[n.vector.copy() for n in data.corner_normals]
for amount in [.005,.01,.025,.05,.1]:
    changed=[n.copy() for n in normals]
    for f in invalidfaces:
        for i in f.loop_indices:
            if i in invalid:changed[i]=(normals[i]+f.normal*amount).normalized()
    data.normals_split_custom_set(changed);data.update();data.calc_tangents(uvmap='runtime_uv');print('NORMAL_BIAS',amount,'INVALID',[(l.index,list(l.tangent)) for l in data.loops if l.tangent.length<.99],flush=True);data.free_tangents()
