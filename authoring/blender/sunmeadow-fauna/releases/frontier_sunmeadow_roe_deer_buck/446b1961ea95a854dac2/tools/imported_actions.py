"""Activate every imported glTF channel, including shape-key action slots."""
from mathutils import Matrix


def activate_imported_clip(rig, meshes, name):
    carriers = [rig]+[mesh.data.shape_keys for mesh in meshes if mesh.data.shape_keys]
    for carrier in carriers:
        if carrier.animation_data:
            carrier.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    for mesh in meshes:
        if mesh.data.shape_keys:
            for key in mesh.data.shape_keys.key_blocks:
                # Authored modes use signed unit weights. Blender's importer
                # sizes sliders from initial values, which otherwise clamps
                # valid negative glTF samples during subsequent evaluation.
                if key.name.startswith('joint_volume_'):
                    key.slider_min = -1
                    key.slider_max = 1
                key.value = 0
    if name == 'rest':
        return None
    result = None
    for carrier in carriers:
        animation = carrier.animation_data
        matching = [track for track in animation.nla_tracks if track.name == name and track.strips] if animation else []
        if len(matching) != 1:
            raise RuntimeError(f'Expected one imported {name} track on {carrier.name}')
        strip = matching[0].strips[0]
        animation.action = strip.action
        animation.action_slot = strip.action_slot
        if carrier == rig:
            result = strip.action
    return result
