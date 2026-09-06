"""Fit the repository's existing human head/neck to the guard skeleton.

No downloads: geometry and packed textures come from blends/male_base.blend.
The original source stays untouched. A bounded decimation produces editable
explicit mesh records while retaining the supplied facial UVs.
"""
import hashlib
import json
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
source=REPO/'blends/male_base.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(source),link=False) as (a,b): b.objects=['Male base mesh']
obj=b.objects[0]; bpy.context.scene.collection.objects.link(obj)
obj.hide_render=False; obj.hide_viewport=False; obj.hide_set(False)
mesh=obj.data.copy(); mesh.transform(obj.matrix_world); obj.data=mesh; obj.matrix_world=Matrix.Identity(4)
bm=bmesh.new(); bm.from_mesh(mesh)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.z<1.43 or abs(v.co.x)>.195],context='VERTS')
bm.to_mesh(mesh); bm.free(); mesh.update(); mesh.calc_loop_triangles()
before=len(mesh.loop_triangles)
bpy.context.view_layer.objects.active=obj; obj.select_set(True)
mod=obj.modifiers.new('Facial runtime budget','DECIMATE'); mod.ratio=min(1,11000/before)
bpy.ops.object.modifier_apply(modifier=mod.name)
mesh=obj.data
bm=bmesh.new(); bm.from_mesh(mesh)
for vertex in bm.verts:
    if vertex.is_boundary and vertex.co.z<1.46: vertex.co.z=1.43
bm.to_mesh(mesh); bm.free(); mesh.update()
top=max(v.co.z for v in mesh.vertices)
for v in mesh.vertices: v.co+=Vector((.0038,.016,1.86-top))
uv=mesh.uv_layers.active
def corner_uv(p):
    if p.material_index!=1: return [list(uv.data[i].uv) for i in p.loop_indices]
    # The packed two-eye atlas needs a bounded iris footprint on the fitted
    # ocular surface; retain its original pixels and reproject only eye UVs.
    result=[]
    for index in p.vertices:
        co=mesh.vertices[index].co; center=.02827 if co.x>0 else -.02827
        result.append([.719+(co.x-center)*20,.700+(co.z-1.7556)*20])
    return result
part={'id':'head_skin','slot':'body','rigid_bone':'head',
      'vertices':[{'id':f'v{v.index}','co':list(v.co)} for v in mesh.vertices],
      'faces':[{'id':f'f{p.index}','vertices':[f'v{i}' for i in p.vertices],
                'uv':corner_uv(p),
                'material':'eye_white' if p.material_index==1 else 'skin'} for p in mesh.polygons],
      'modifiers':[], 'landmarks':{},'seams':[],'sharp_edges':[],'creases':[],'closed':False}
out=ROOT/'anatomy'; out.mkdir(exist_ok=True)
(out/'head_refined.json').write_text(json.dumps({'schema_version':1,'component':'head','parts':[part]},separators=(',',':'))+'\n')
textures=ROOT/'textures/imported'; textures.mkdir(parents=True,exist_ok=True)
for material,name in [(obj.data.materials[0],'skin.jpg'),(obj.data.materials[1],'eye_white.png')]:
    shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    image=shader.inputs['Base Color'].links[0].from_node.image
    if not image.packed_file: raise ValueError('Expected packed existing-source texture')
    (textures/name).write_bytes(bytes(image.packed_file.data))
mesh.calc_loop_triangles()
(out/'provenance.json').write_text(json.dumps({'source':'blends/male_base.blend','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'origin':'Existing repository-provided human base; original geometry and packed textures retained as provenance, no new acquisition.',
    'operation':'Upper head/neck extraction; preserve skin UVs and reproject eye UVs for natural iris size; decimate to 11000 triangles; translate into canonical guard fit.',
    'input_head_triangles':before,'output_head_triangles':len(mesh.loop_triangles),
    'textures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in textures.iterdir()}},indent=2)+'\n')
print('NATURAL_HEAD',before,len(mesh.loop_triangles),flush=True)
