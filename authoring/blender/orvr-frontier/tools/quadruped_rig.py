"""Shared export plumbing for independently authored animal anatomy and motion.

Geometry, bone positions, skin assignments and motion remain species-authored.
This module does not create an animal body or invent a generic gait.
"""
from __future__ import annotations
import bpy
from mathutils import Matrix


def create_rig(name, bones):
    """Create Z-up/-Y-front bones from ordered {name,head,tail,parent?} records."""
    data = bpy.data.armatures.new(name + '.skeleton')
    rig = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for record in bones:
        bone = data.edit_bones.new(record['name'])
        bone.head, bone.tail = record['head'], record['tail']
        if record.get('parent'):
            bone.parent = data.edit_bones[record['parent']]
        bone.use_deform = record.get('deform', True)
        if record.get('roll') is not None:
            bone.roll = record['roll']
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.show_in_front = True
    rig['coordinate_contract'] = 'Blender Z-up/front -Y; glTF Y-up/front +Z; root remains in place'
    return rig


def bind_explicit_weights(mesh, rig, weights):
    """Bind one finite normalized bone-weight mapping per actual mesh vertex."""
    if len(weights) != len(mesh.data.vertices):
        raise ValueError('Every animal vertex needs an authored skin assignment')
    groups = {bone.name: mesh.vertex_groups.new(name=bone.name)
              for bone in rig.data.bones if bone.use_deform}
    for index, assignments in enumerate(weights):
        total = sum(assignments.values())
        if total <= 0 or len(assignments) > 4:
            raise ValueError(f'Invalid skin assignment at vertex {index}')
        for name, weight in assignments.items():
            if name not in groups or weight < 0:
                raise ValueError(f'Unknown bone or negative weight at vertex {index}: {name}')
            if weight:
                groups[name].add([index], weight / total, 'REPLACE')
    mesh.parent = rig
    modifier = mesh.modifiers.new('authored_anatomical_skin', 'ARMATURE')
    modifier.object = rig
    modifier.use_deform_preserve_volume = False
