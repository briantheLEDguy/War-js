"""Local topology relaxation proof on imported rejected GLB; never approval."""
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fauna import ROOT, resolve
from reimport_review import setup
from corrective_fields import smoothstep, haunch_envelope
from motion import solve_leg

definition = resolve('roe_deer_buck')
scale = definition['scale']
for phase in [.125, .625]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'review/candidates/buck_differential/frontier_sunmeadow_roe_deer_buck_lod0.glb'))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
    if obj.data.shape_keys: obj.shape_key_clear()
    rest = np.array([v.co[:] for v in obj.data.vertices])/scale
    action = next(a for a in bpy.data.actions if a.name == 'run')
    rig.animation_data_create(); rig.animation_data.action = action; rig.animation_data.action_slot = action.slots[0]
    first, last = action.frame_range; frame = first+(last-first)*phase
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame)); bpy.context.view_layer.update()
    for label in ['L', 'R']:
        foot = rig.pose.bones['hoof_hind_'+label].head.copy()
        solve_leg(rig, 'hind', label, foot, .36)
        bpy.context.view_layer.update()
    carrier = rig.pose.bones['pelvis'].matrix @ rig.data.bones['pelvis'].matrix_local.inverted()
    inverse = carrier.inverted()
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.copy()
    original = np.array([(inverse@v.co)[:] for v in mesh.vertices])/scale
    # glTF duplicates UV boundary vertices; weld their coincident rest samples
    # for topology relaxation without altering the actual delivery vertex order.
    unique, reverse = np.unique(np.round(rest, 5), axis=0, return_inverse=True)
    positions = np.zeros_like(unique); counts = np.bincount(reverse)
    for axis in range(3): positions[:, axis] = np.bincount(reverse, weights=original[:, axis])/counts
    edges = np.array([e.vertices[:] for e in mesh.edges]); edges = reverse[edges]
    edges = np.unique(np.sort(edges, axis=1), axis=0); edges = edges[edges[:, 0] != edges[:, 1]]
    a, b = np.concatenate([edges[:, 0], edges[:, 1]]), np.concatenate([edges[:, 1], edges[:, 0]])
    degree = np.maximum(1, np.bincount(a, minlength=len(unique)))
    mask = smoothstep(.28, .43, unique[:, 2]) * (1-smoothstep(.71, .83, unique[:, 2]))
    mask *= smoothstep(.018, .09, np.abs(unique[:, 0]))
    hind = smoothstep(-.025, .10, unique[:, 1]) * (1-smoothstep(.39, .49, unique[:, 1]))
    front = smoothstep(-.48, -.36, unique[:, 1]) * (1-smoothstep(-.21, -.09, unique[:, 1]))
    mask *= np.maximum(hind, front)
    def relax(points):
        points = points.copy()
        for iteration in range(150):
            average = np.column_stack([np.bincount(a, weights=points[b, axis], minlength=len(unique))/degree for axis in range(3)])
            points += (average-points)*mask[:, None]*.5
        return points
    positions = relax(positions)
    detail = unique-relax(unique)
    rotations = {g.index: np.array((inverse@rig.pose.bones[g.name].matrix@rig.data.bones[g.name].matrix_local.inverted()).to_3x3()) for g in obj.vertex_groups if g.name in rig.pose.bones}
    transported = np.zeros_like(original)
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            if group.group in rotations:
                transported[vertex.index] += (rotations[group.group]@detail[reverse[vertex.index]])*group.weight
    details = np.zeros_like(unique)
    for axis in range(3): details[:, axis] = np.bincount(reverse, weights=transported[:, axis])/counts
    positions += details
    correction = np.zeros_like(positions)
    for side, label in [(1, 'L'), (-1, 'R')]:
        hip = np.array((inverse@rig.pose.bones['thigh_'+label].head)[:])/scale
        knee = np.array((inverse@rig.pose.bones['thigh_'+label].tail)[:])/scale
        rest_direction = np.array(rig.data.bones['thigh_'+label].tail_local[:])-np.array(rig.data.bones['thigh_'+label].head_local[:])
        direction = knee-hip
        angle = math.atan2(rest_direction[1]*direction[2]-rest_direction[2]*direction[1], rest_direction[1]*direction[1]+rest_direction[2]*direction[2])
        tuck = smoothstep(.10, .70, -angle)
        support = np.exp(-((unique[:, 1]-.18)/.135)**2-((unique[:, 2]-.49)/.14)**2)
        support *= smoothstep(.07, .155, side*unique[:, 0])*smoothstep(.31, .41, unique[:, 2])*(1-smoothstep(.67, .80, unique[:, 2]))
        release = .9*support*smoothstep(.10, .55, -angle)
        positions -= details*release[:, None]
        correction[:, 0] += side*.045*support*tuck
        print('TUCK_ANGLE', side, angle, tuck, flush=True)
    positions += correction
    for vertex, point in zip(mesh.vertices, positions[reverse]): vertex.co = carrier@Vector(point*scale)
    obj.modifiers.clear(); obj.data = mesh; mesh.update()
    target = ROOT/'review/probes'/f'differential_haunch_release_{phase}.png'
    _, camera = setup([obj], target, 900, 16)
    center = Vector((0, -.005, .43)); camera.location = center+Vector((4, 0, .20))
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler(); camera.data.ortho_scale = 1.13
    bpy.ops.render.render(write_still=True)
    print('RELAXED_PROBE', phase, float(np.linalg.norm(positions[reverse]-original, axis=1).max()), flush=True)
