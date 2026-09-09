"""Source-only axillary-detail study on current actual poses; never approval."""
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fauna import ROOT, resolve
from imported_actions import activate_imported_clip
from joint_correctives import JointRelaxation, shoulder_detail_retention
from reimport_review import setup

scale = resolve('roe_deer_buck')['scale']
for phase in [.125, 7/9]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'review/candidates/buck_differential/frontier_sunmeadow_roe_deer_buck_lod0.glb'))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
    rest = np.asarray([v.co[:] for v in obj.data.vertices])
    edges = np.asarray([e.vertices[:] for e in obj.data.edges])
    relax = JointRelaxation(rest, edges, scale)
    action = activate_imported_clip(rig, [obj], 'run')
    first, last = action.frame_range; frame = first+(last-first)*phase
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame)); bpy.context.view_layer.update()
    posed = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    positions = np.asarray([v.co[:] for v in posed.vertices])
    rotations = np.zeros((len(rest), 3, 3))
    matrices = {group.index: np.asarray((rig.pose.bones[group.name].matrix@rig.data.bones[group.name].matrix_local.inverted()).to_3x3()) for group in obj.vertex_groups if group.name in rig.pose.bones}
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            if group.group in matrices: rotations[vertex.index] += matrices[group.group]*group.weight
    carrier = (rig.pose.bones['chest'].matrix@rig.data.bones['chest'].matrix_local.inverted()).to_3x3()
    angles = {}
    for side, label in [(1, 'L'), (-1, 'R')]:
        bone = rig.pose.bones['shoulder_'+label]
        resting = np.asarray(bone.bone.tail_local-bone.bone.head_local)
        direction = np.linalg.solve(np.asarray(carrier), np.asarray(bone.tail-bone.head))
        angles[side] = math.atan2(resting[1]*direction[2]-resting[2]*direction[1], resting[1]*direction[1]+resting[2]*direction[2])
    retention = shoulder_detail_retention(rest, scale, angles)
    adjusted = positions-np.einsum('nij,nj->ni', rotations, relax.detail)*(1-retention[:, None])
    lengths = np.linalg.norm(rest[edges[:, 0]]-rest[edges[:, 1]], axis=1); valid = lengths > .0002
    strain = lambda points: float((np.linalg.norm(points[edges[:, 0]]-points[edges[:, 1]], axis=1)[valid]/lengths[valid]).max())
    print('SHOULDER_STUDY', phase, angles, 'strain before/after', strain(positions), strain(adjusted), flush=True)
    mesh = bpy.data.meshes.new('axillary_study_surface')
    mesh.from_pydata(adjusted.tolist(), [], [list(p.vertices) for p in posed.polygons]); mesh.update()
    for polygon in mesh.polygons: polygon.use_smooth = True
    for layer in posed.uv_layers:
        target = mesh.uv_layers.new(name=layer.name)
        values = np.empty(len(layer.data)*2, dtype=np.float32); layer.data.foreach_get('uv', values); target.data.foreach_set('uv', values)
    for layer in posed.color_attributes:
        target = mesh.color_attributes.new(name=layer.name, type=layer.data_type, domain=layer.domain)
        values = np.empty(len(layer.data)*4, dtype=np.float32); layer.data.foreach_get('color', values); target.data.foreach_set('color', values)
    for material in obj.data.materials: mesh.materials.append(material)
    obj.modifiers.clear(); obj.data = mesh
    output = ROOT/'review/probes'/f'shoulder_release_{phase:.3f}.png'
    _, camera = setup([obj], output, 1000, 20)
    center = Vector((0, -.24, .47)); camera.location = center+Vector((-3, -2.1, .3))
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler(); camera.data.ortho_scale = .86
    bpy.ops.render.render(write_still=True)
