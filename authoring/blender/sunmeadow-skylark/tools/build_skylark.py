"""Isolated original skylark v2. Exports remain unapproved review candidates."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from skylark_anatomy import anatomy, atlas, bone_records, WING
from skylark_materials import material
from quadruped_rig import create_rig, bind_explicit_weights


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def eyes(surface, lod):
    body = surface.parts[0]
    count = body['vertices']
    faces = [face for face in surface.faces if all(index < count for index in face)]
    tree = BVHTree.FromPolygons(list(map(Vector, surface.vertices[:count])), faces)
    segments = [40, 24, 16][lod]
    for side in [-1, 1]:
        vertices, coordinates = [], []
        for radius, depth in [(1.18, 0), (1, .00013), (.78, .00065), (.40, .00105), (.005, .00115)]:
            for index in range(segments):
                angle = math.tau*index/segments
                y = -.044+math.cos(angle)*.0031*radius
                z = .130+math.sin(angle)*.0029*radius
                hit = tree.ray_cast(Vector((side*.1, y, z)), Vector((-side, 0, 0)))[0]
                if hit is None:
                    raise RuntimeError('Eye survey misses the continuous head')
                vertices.append((hit.x+side*(depth+.000035), y, z))
                coordinates.append(atlas(.5+.46*min(1, radius)*math.cos(angle), .5+.46*min(1, radius)*math.sin(angle), 4))
        faces = []
        for ring in range(4):
            for index in range(segments):
                face = [ring*segments+index, ring*segments+(index+1)%segments, (ring+1)*segments+(index+1)%segments, (ring+1)*segments+index]
                faces.append(face if side > 0 else face[::-1])
        faces.append(list(range(segments-1, -1, -1)))
        faces.append(list(range(4*segments, 5*segments)))
        surface.add('fitted_eye_'+str(side), vertices, faces, [[coordinates[i] for i in face] for face in faces], [{'head': 1} for _ in vertices])


def object_from_surface(surface, name, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(surface.vertices, [], surface.faces)
    mesh.update()
    layer = mesh.uv_layers.new(name='AnatomicalUV')
    for polygon, coordinates in zip(mesh.polygons, surface.uv):
        polygon.use_smooth = True
        for loop, uv in zip(polygon.loop_indices, coordinates): layer.data[loop].uv = uv
    mesh.materials.append(mat)
    # Recalculate each closed shell after reflecting left/right authored cages.
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def pose_matrix(start, direction, normal):
    y = Vector(direction).normalized()
    x = y.cross(Vector(normal)).normalized()
    z = x.cross(y).normalized()
    rotation = Matrix((x, y, z)).transposed().to_4x4()
    rotation.translation = Vector(start)
    return rotation


def set_matrix(rig, name, desired, matrices):
    bone = rig.pose.bones[name]
    parent = bone.parent
    basis = bone.bone.convert_local_to_pose(desired, bone.bone.matrix_local,
        parent_matrix=matrices[parent.name] if parent else Matrix.Identity(4),
        parent_matrix_local=parent.bone.matrix_local if parent else Matrix.Identity(4), invert=True)
    bone.matrix_basis = basis
    matrices[name] = desired




def build(levels):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for directory in ['runtime', 'review', 'source', 'textures', 'masters']:
        (ROOT/directory).mkdir(exist_ok=True)
    bones = bone_records()
    rig = create_rig('skylark_v2_rig', bones)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        if bone.name.startswith('wing_'): bone.align_roll(Vector((0, 0, 1)))
    bpy.ops.object.mode_set(mode='OBJECT')
    models, evidence = [], []
    for lod in levels:
        surface = anatomy(lod)
        eyes(surface, lod)
        obj = object_from_surface(surface, f'frontier_sunmeadow_skylark_lod{lod}', material(ROOT, lod))
        bind_explicit_weights(obj, rig, surface.weights)
        obj.parent = None
        bpy.context.view_layer.objects.active = obj
        modifier = obj.modifiers.new('Explicit_delivery_triangles', 'TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        obj.data.calc_loop_triangles()
        evidence.append({'lod': lod, 'triangles': len(obj.data.loop_triangles), 'vertices': len(obj.data.vertices), 'parts': surface.parts})
        models.append(obj)
        if lod == 0:
            (ROOT/'source/skylark_v2_cage.json').write_text(json.dumps(vars(surface), separators=(',', ':'))+'\n')
    actions = []
    for lod, obj, record in zip(levels, models, evidence):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True); rig.select_set(True)
        bpy.context.view_layer.objects.active = obj
        target = ROOT/'runtime'/f'frontier_sunmeadow_skylark_lod{lod}.glb'
        bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', use_selection=True, export_yup=True,
            export_normals=True, export_tangents=True, export_texcoords=True, export_skins=True,
            export_animations=False, export_animation_mode='ACTIONS', export_anim_single_armature=True,
            export_force_sampling=True, export_frame_range=False)
        record.update(model=target.relative_to(ROOT).as_posix(), modelSha256=sha(target), bytes=target.stat().st_size)
        obj.hide_set(lod != 0); obj.hide_render = lod != 0
    master = ROOT/'masters/frontier_sunmeadow_skylark_v2.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(master), compress=True)
    tools = ['build_skylark.py', 'skylark_anatomy.py', 'skylark_materials.py', 'quadruped_rig.py']
    report = {'status': 'unapproved_anatomy_and_motion_candidate', 'sourceFiles': {'tools/'+name: sha(ROOT/'tools'/name) for name in tools},
              'master': master.relative_to(ROOT).as_posix(), 'masterSha256': sha(master), 'bones': bones,
              'clips': [action.name for action in actions], 'lods': evidence}
    (ROOT/'review/skylark_v2_build.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lods', default='0')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    build(list(map(int, args.lods.split(','))))
