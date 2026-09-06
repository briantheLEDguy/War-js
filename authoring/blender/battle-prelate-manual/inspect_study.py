"""Read the current Blender study without changing its geometry or settings."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parent
objects = []
for obj in bpy.data.objects:
    corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    objects.append({
        "name": obj.name,
        "type": obj.type,
        "visible": obj.visible_get(),
        "hide_viewport": obj.hide_viewport,
        "hide_render": obj.hide_render,
        "collections": [c.name for c in obj.users_collection],
        "vertices": len(obj.data.vertices) if obj.type == 'MESH' else None,
        "polygons": len(obj.data.polygons) if obj.type == 'MESH' else None,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "bounds_min": [min(p[i] for p in corners) for i in range(3)],
        "bounds_max": [max(p[i] for p in corners) for i in range(3)],
        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        "modifiers": [{"name": m.name, "type": m.type, "viewport": m.show_viewport} for m in obj.modifiers],
    })
materials = []
for mat in bpy.data.materials:
    nodes = mat.node_tree.nodes if mat.use_nodes else []
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    materials.append({
        "name": mat.name, "users": mat.users,
        "color": list(bsdf.inputs['Base Color'].default_value) if bsdf else list(mat.diffuse_color),
        "metallic": bsdf.inputs['Metallic'].default_value if bsdf else mat.metallic,
        "roughness": bsdf.inputs['Roughness'].default_value if bsdf else mat.roughness,
        "nodes": [{"name": n.name, "type": n.type} for n in nodes],
    })
report = {"file": bpy.data.filepath, "objects": objects, "materials": materials}
(root / 'study_inventory.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('STUDY INVENTORY:', len(objects), 'objects;', len(materials), 'materials')
