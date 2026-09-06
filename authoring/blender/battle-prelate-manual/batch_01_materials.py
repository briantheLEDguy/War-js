"""Explicit material/visibility edits to the existing study; creates no geometry."""
import bpy
import hashlib
import json
import time
from array import array
from pathlib import Path

root = Path(__file__).resolve().parent
assert Path(bpy.data.filepath).parent == root, 'Open the isolated study first.'
assert not bpy.context.scene.get('bp_batch_01_applied'), 'Batch already applied.'

def mesh_hashes():
    result = {}
    for mesh in bpy.data.meshes:
        coords = array('f', [0.0]) * (len(mesh.vertices) * 3)
        mesh.vertices.foreach_get('co', coords)
        indices = array('i', [0]) * len(mesh.loops)
        mesh.loops.foreach_get('vertex_index', indices)
        result[mesh.name] = hashlib.sha256(coords.tobytes() + indices.tobytes()).hexdigest()
    return result

before_hashes = mesh_hashes()
before_objects = set(bpy.data.objects.keys())
checkpoint = root / 'battle_prelate_before_batch.blend'
assert not checkpoint.exists(), 'Preserve the existing batch checkpoint.'
bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
started = time.perf_counter()

# Each mapping is an artist-selected existing component, not a generated part.
groups = {
    'steel': [
        'BP_Head_Gorget_High', 'BP_Chest_CuirassFront_High',
        'BP_Chest_CuirassBack_High', 'BP_Shoulders_Pauldrons_High',
        'BP_Shoulders_Lamellae_High', 'BP_Hands_Bracers_High',
        'BP_Legs_Cuisses_High', 'BP_Legs_KneeCops_High',
        'BP_Feet_Boots_High', 'BP_Waist_FauldPlates_High',
    ],
    'crimson': ['BP_Tabard_PrayerApron_High', 'BP_Back_CoatTails_High'],
    'mail': ['BP_Chest_FullMailUnderlayer_High', 'BP_Legs_Chausses_High'],
    'leather': ['BP_Hands_Gloves_High', 'BP_Feet_LeatherUnderboots_High', 'BP_Waist_BeltFauld_High'],
}
palette = {
    'steel': ('MAT_Study_Steel', (0.16, 0.18, 0.20, 1), 0.9, 0.46),
    'crimson': ('MAT_Study_Crimson', (0.08866, 0.02029, 0.02315, 1), 0.0, 0.85),
    'mail': ('MAT_Study_Mail', (0.01850, 0.02122, 0.02315, 1), 0.8, 0.55),
    'leather': ('MAT_Study_Leather', (0.02315, 0.01229, 0.00913, 1), 0.0, 0.80),
}
selected_names = {name for names in groups.values() for name in names}
for name in selected_names:
    obj = bpy.data.objects[name]
    assert obj.type == 'MESH' and len(obj.material_slots) == 1, name
    assert not obj.material_slots[0].material.name.endswith('_Atlas'), name

changes = []
for key, names in groups.items():
    name, color, metallic, roughness = palette[key]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    mat.diffuse_color, mat.metallic, mat.roughness = color, metallic, roughness
    for object_name in names:
        obj = bpy.data.objects[object_name]
        changes.append({'object': object_name, 'old_material': obj.material_slots[0].material.name, 'material': name})
        obj.material_slots[0].material = mat

# Display one authoring version; preserve all LODs and alternative garments.
for obj in bpy.data.objects:
    if obj.name.startswith('BP_') and obj.type == 'MESH':
        visible = obj.name in selected_names
        obj.hide_set(not visible)
        obj.hide_render = not visible
        if visible:
            obj.hide_viewport = False

for name in ('body_civic_humanoid_v2_m.high-poly', 'grooming_eyebrows_eyebrow006', 'grooming_eyelashes_eyelashes01'):
    obj = bpy.data.objects[name]
    obj.hide_set(False)
    obj.hide_render = False

bpy.context.view_layer.update()
assert before_hashes == mesh_hashes(), 'Unexpected mesh change.'
assert before_objects == set(bpy.data.objects.keys()), 'Unexpected object creation.'
bpy.context.scene['bp_batch_01_applied'] = True
elapsed = time.perf_counter() - started
(root / 'batch_01_report.json').write_text(json.dumps({
    'material_assignments': changes,
    'visible_authoring_parts': sorted(selected_names),
    'mesh_data_unchanged': True,
    'object_count_unchanged': True,
    'execution_seconds_excluding_saves': elapsed,
    'checkpoint': str(checkpoint),
}, indent=2), encoding='utf-8')

# Return to the same viewport after the console command and save that layout.
area = bpy.context.area
area.type = 'VIEW_3D'
space = area.spaces.active
space.region_3d.view_location = (0.0, -0.02, 0.96)
space.region_3d.view_distance = 3.5
space.overlay.show_extras = False
space.shading.type = 'MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(root / 'battle_prelate_batch_study.blend'))
print('BATCH COMPLETE:', len(changes), 'material assignments;', round(elapsed, 3), 'seconds; geometry unchanged.')
