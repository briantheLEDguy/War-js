"""Clean GLB contact measurements and fixed-camera ready/pour views."""
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'tools'))
import build_collection as build
from review_motion import activate_clip

KEY = 'frontier_oil_cauldron'
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
TOOL_SHA = sha(__file__)


def components(obj):
    # Weld only the duplicate vertices required for glTF normal and UV seams.
    vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    canonical = {}; parent = list(range(len(vertices)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def join(a, b): parent[find(a)] = find(b)
    for i, v in enumerate(vertices):
        key = tuple(round(x, 6) for x in v)
        if key in canonical: join(i, canonical[key])
        else: canonical[key] = i
    for edge in obj.data.edges: join(*edge.vertices)
    groups = {}
    for face in obj.data.polygons: groups.setdefault(find(face.vertices[0]), []).append(list(face.vertices))
    result = []
    for faces in groups.values():
        indices = sorted({i for face in faces for i in face})
        low = Vector([min(vertices[i][axis] for i in indices) for axis in range(3)])
        high = Vector([max(vertices[i][axis] for i in indices) for axis in range(3)])
        result.append({'vertices': vertices, 'indices': indices, 'faces': faces, 'low': low, 'high': high})
    return result


def audit_contact():
    obj = next(o for o in bpy.context.scene.objects if o.name == 'tipping_cauldron' and o.type == 'MESH')
    groups = components(obj)
    bowl = max(groups, key=lambda g: len(g['faces']))
    surface = BVHTree.FromPolygons(bowl['vertices'], bowl['faces'])
    records = []
    for x in [-.3, 0, .3]:
        for z in [.48, .75]:
            found = [g for g in groups if abs((g['low'].x + g['high'].x) / 2 - x) < .015
                     and abs((g['low'].z + g['high'].z) / 2 - z) < .015
                     and g['high'].x - g['low'].x < .16 and g['high'].z - g['low'].z < .16]
            if len(found) != 1: raise ValueError(f'Expected one actual exported rosette at {(x,z)}, found {len(found)}')
            group = found[0]; distances = []
            for i in group['indices']:
                vertex = group['vertices'][i]
                hit, normal, _, distance = surface.find_nearest(vertex)
                distances.append((vertex-hit).dot(normal))
            records.append({'x': x, 'z': z, 'minimum_signed_distance_m': min(distances),
                            'maximum_signed_distance_m': max(distances), 'vertices': len(distances)})
    return records


def main():
    records = []
    for lod in [0, 1, 2]:
        file = ROOT / 'runtime' / f'{KEY}_lod{lod}.glb'
        model_sha = sha(file)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.render.fps = 30
        bpy.ops.import_scene.gltf(filepath=str(file))
        activate_clip('oil_pour', 0)
        contacts = audit_contact()
        print('ACTUAL_CONTACT', lod, json.dumps(contacts), flush=True)
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.visible_get() and not o.hide_render]
        views = {}
        for name, seconds in [('ready', 0), ('pour', 43 / 30)]:
            activate_clip('oil_pour', seconds)
            for obj in list(bpy.context.scene.objects):
                if obj.type in {'LIGHT', 'CAMERA'}: bpy.data.objects.remove(obj, do_unlink=True)
            output = ROOT / 'review' / f'cauldron_lod{lod}_{name}.png'
            build.set_view(meshes, output)
            views[name] = {'file': str(output.relative_to(ROOT)), 'sha256': sha(output), 'seconds': seconds}
        if lod == 0:
            activate_clip('oil_pour', 0)
            scene = bpy.context.scene; camera = scene.camera
            center = Vector((0, -.39, .64)); camera.location = center + Vector((.65, -2, .32))
            camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
            camera.data.ortho_scale = 1.05
            output = ROOT / 'review' / 'cauldron_lod0_contact_detail.png'
            scene.render.filepath = str(output); bpy.ops.render.render(write_still=True)
            views['contact_detail'] = {'file': str(output.relative_to(ROOT)), 'sha256': sha(output), 'seconds': 0}
        if sha(file) != model_sha or sha(__file__) != TOOL_SHA:
            raise ValueError('Model or reviewer changed while rendering; rerun the complete review.')
        records.append({'lod': lod, 'model': file.name, 'modelSha256': model_sha, 'contacts': contacts, 'views': views})
        temporary = ROOT / 'review' / 'actual-export-review.tmp'
        temporary.write_text(json.dumps({'toolSha256': TOOL_SHA, 'models': records}, indent=2) + '\n')
        temporary.replace(ROOT / 'review' / 'actual-export-review.json')


if __name__ == '__main__': main()
