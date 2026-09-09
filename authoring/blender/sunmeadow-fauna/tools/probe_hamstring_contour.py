"""Source-only peak-tuck hamstring contour study from the actual candidate."""
import argparse
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fauna import ROOT, resolve
from imported_actions import activate_imported_clip
from hamstring_contour import hamstring_displacement
from reimport_review import setup

parser = argparse.ArgumentParser(); parser.add_argument('--measure-only', action='store_true'); parser.add_argument('--lift', type=float, default=.065)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'review/candidates/buck_differential/frontier_sunmeadow_roe_deer_buck_lod0.glb'))
rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
obj = next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and any(mod.type == 'ARMATURE' for mod in obj.modifiers))
scale = resolve('roe_deer_buck')['scale']; rest = np.asarray([vertex.co[:] for vertex in obj.data.vertices])/scale
for phase in [.125, .25, .375, .625, 7/9]:
    action = activate_imported_clip(rig, [obj], 'run'); first, last = action.frame_range; frame = first+(last-first)*phase
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame)); bpy.context.view_layer.update()
    carrier = np.asarray((rig.pose.bones['pelvis'].matrix@rig.data.bones['pelvis'].matrix_local.inverted()).to_3x3())
    angles = {}
    for side, label in [(1, 'L'), (-1, 'R')]:
        bone = rig.pose.bones['thigh_'+label]; resting = np.asarray(bone.bone.tail_local-bone.bone.head_local)
        direction = np.linalg.solve(carrier, np.asarray(bone.tail-bone.head))
        angles[side] = math.atan2(resting[1]*direction[2]-resting[2]*direction[1], resting[1]*direction[1]+resting[2]*direction[2])
    print('HAMSTRING_FLEXION', phase, angles, flush=True)
    if args.measure_only or phase != .375: continue
    posed = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    positions = np.asarray([vertex.co[:] for vertex in posed.vertices])
    displacement = hamstring_displacement(rest*scale, scale, carrier, angles)*(args.lift/.065)
    positions += displacement
    edges = np.asarray([edge.vertices[:] for edge in obj.data.edges]); lengths = np.linalg.norm((rest[edges[:, 0]]-rest[edges[:, 1]])*scale, axis=1); valid = lengths>.0002
    ratios = np.linalg.norm(positions[edges[:, 0]]-positions[edges[:, 1]], axis=1)[valid]/lengths[valid]
    print('HAMSTRING_LIFT', float(np.linalg.norm(displacement, axis=1).max()), 'STRAIN', float(ratios.max()), float(np.percentile(ratios, 99)), flush=True)
    mesh = bpy.data.meshes.new('hamstring_contour_study'); mesh.from_pydata(positions.tolist(), [], [list(p.vertices) for p in posed.polygons]); mesh.update()
    for polygon in mesh.polygons: polygon.use_smooth = True
    for layer in posed.uv_layers:
        target = mesh.uv_layers.new(name=layer.name); values = np.empty(len(layer.data)*2, dtype=np.float32)
        layer.data.foreach_get('uv', values); target.data.foreach_set('uv', values)
    for layer in posed.color_attributes:
        target = mesh.color_attributes.new(name=layer.name, type=layer.data_type, domain=layer.domain); values = np.empty(len(layer.data)*4, dtype=np.float32)
        layer.data.foreach_get('color', values); target.data.foreach_set('color', values)
    for material in obj.data.materials: mesh.materials.append(material)
    study = bpy.data.objects.new('hamstring_proof', mesh); bpy.context.collection.objects.link(study); obj.hide_render = True
    _, camera = setup([study], ROOT/'review/probes/hamstring.png', 1000, 20)
    for view, direction in [('profile', (4, 0, .20)), ('opposite', (-3, -2.1, .5))]:
        center = Vector((0, .22, .48)); camera.location = center+Vector(direction)
        camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler(); camera.data.ortho_scale = .94
        bpy.context.scene.render.filepath = str(ROOT/'review/probes'/f'hamstring_lift_{args.lift:g}_0.375_{view}.png')
        bpy.ops.render.render(write_still=True)
    study.hide_render = True; obj.hide_render = False
