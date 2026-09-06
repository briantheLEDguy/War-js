"""Read-only inspection of the repository's existing human base."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_guards import studio,camera
mesh=next(o for o in bpy.data.objects if o.type=='MESH')
mesh.hide_render=False; mesh.hide_viewport=False; mesh.hide_set(False)
for collection in bpy.data.collections: collection.hide_render=False; collection.hide_viewport=False
for obj in list(bpy.data.objects):
    if obj.type!='MESH': bpy.data.objects.remove(obj,do_unlink=True)
bounds=[mesh.matrix_world @ v.co for v in mesh.data.vertices]
print('BOUNDS',[(min(v[i] for v in bounds),max(v[i] for v in bounds)) for i in range(3)],flush=True)
mat=bpy.data.materials.new('Inspection skin'); mat.diffuse_color=(.52,.36,.27,1); mat.use_nodes=True
shader=mat.node_tree.nodes.get('Principled BSDF'); shader.inputs['Base Color'].default_value=(.52,.36,.27,1); shader.inputs['Roughness'].default_value=.62
mesh.data.materials.clear(); mesh.data.materials.append(mat)
for poly in mesh.data.polygons: poly.use_smooth=True
studio(); scene=bpy.context.scene; scene.cycles.samples=16; scene.render.resolution_x=700; scene.render.resolution_y=800
top=max(v.z for v in bounds)
scene.camera=camera('Base inspection',(1,-3,top-.12),(0,-.01,top-.12),.37)
scene.render.filepath=str(ROOT/'review/existing_human_base.png'); bpy.ops.render.render(write_still=True)
