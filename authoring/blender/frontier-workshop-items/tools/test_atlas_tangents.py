"""Regression: preserve the exact source mesh while resolving a grazing rope normal."""
import bpy,sys,math,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tools'))
from export_items import apply_materials,geometry_hash,repair_grazing_corner_normals,save
key='frontier_siege_ammunition_cradle';reports=[]
for lod in range(3):
    bpy.ops.wm.open_mainfile(filepath=str(root/'masters'/f'{key}_lod{lod}.source.blend'))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
    apply_materials(objects);parts=[]
    for obj in objects:
        names={obj.data.materials[p.material_index].name.split('.')[-1] for p in obj.data.polygons}
        if not names<={'oak','oak_end','working_oak'} and not names<={'forged_iron','worked_steel'}:parts.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();obj=parts[0];data=obj.data
    before=geometry_hash([obj]);margin=4/[2048,1024,512][lod]
    data.uv_layers.new(name='runtime_uv');data.uv_layers.active_index=len(data.uv_layers)-1;data.uv_layers['runtime_uv'].active_render=True
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=margin,area_weight=.9,correct_aspect=True,scale_to_bounds=True);bpy.ops.uv.pack_islands(rotate=True,rotate_method='ANY',scale=True,margin_method='FRACTION',margin=margin,shape_method='CONCAVE');bpy.ops.object.mode_set(mode='OBJECT')
    data.calc_tangents(uvmap='runtime_uv');invalid=[l.index for l in data.loops if l.tangent.length<.99];data.free_tangents()
    if lod==0:assert len(invalid)==1,'The real failing rope corner must remain covered'
    uv_before=[list(c.uv) for c in data.uv_layers['runtime_uv'].data]
    repairs=repair_grazing_corner_normals(data,invalid)
    data.calc_tangents(uvmap='runtime_uv');remaining=[l.index for l in data.loops if l.tangent.length<.99];data.free_tangents()
    assert not remaining,(lod,remaining)
    assert before==geometry_hash([obj]),'Repair changed surface geometry'
    assert uv_before==[list(c.uv) for c in data.uv_layers['runtime_uv'].data],'Repair changed UV atlas'
    assert all(r['changeDegrees']<1 for r in repairs),'Correction exceeds narrow shading tolerance'
    reports.append({'lod':lod,'invalidBefore':invalid,'invalidAfter':remaining,'geometrySha256':before,'geometryUnchanged':True,'uvUnchanged':True,'repairs':repairs})
    print('TANGENT_REGRESSION_PASS',lod,len(invalid),len(repairs),flush=True)
save(root/'review/tangent-regression.json',{'exporterSha256':hashlib.sha256((root/'tools/export_items.py').read_bytes()).hexdigest(),'lods':reports})
