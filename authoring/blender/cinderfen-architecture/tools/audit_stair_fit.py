"""Audit placed stair bodies against actual exported curtain/gatehouse meshes."""
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
zone = json.loads((REPO / 'public/assets/maps/cinderfen_outskirts.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
library = {}
inputs = []


def geometry(key):
    if key not in library:
        path = REPO / 'public/assets/models' / f'{key}_lod0.glb'
        before = set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        created = [obj for obj in bpy.context.scene.objects if obj not in before]
        bpy.context.view_layer.update()
        vertices, faces = [], []
        for obj in created:
            if obj.type != 'MESH':
                continue
            offset = len(vertices)
            vertices.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
            faces.extend(tuple(offset + index for index in face.vertices) for face in obj.data.polygons)
        library[key] = vertices, faces
        for obj in created:
            bpy.data.objects.remove(obj, do_unlink=True)
        inputs.append({'model': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return library[key]


def placed_geometry(prop, origin):
    vertices, faces = geometry(prop['assetKey'])
    scale = prop.get('scale', 1)
    transform = (Matrix.Translation((prop['x'] - origin[0], -prop['z'] + origin[1], prop.get('y', 0)))
                 @ Matrix.Rotation(prop.get('rotY', 0), 4, 'Z')
                 @ Matrix.Diagonal(Vector((scale * prop.get('scaleX', 1), scale * prop.get('scaleZ', 1), scale * prop.get('scaleY', 1), 1))))
    return [transform @ vertex for vertex in vertices], faces


def tree(prop, origin):
    return BVHTree.FromPolygons(*placed_geometry(prop, origin))


stairs = [prop for prop in zone['props'] if prop.get('assetKey') == 'frontier_cinderfen_wall_stair']
inset = float(sys.argv[sys.argv.index('--inset') + 1]) if '--inset' in sys.argv else 0
for stair in stairs:
    yaw = stair['rotY'] - math.pi / 4
    stair['x'] -= inset * (math.cos(yaw) + math.sin(yaw))
    stair['z'] += inset * (math.sin(yaw) - math.cos(yaw))
walls = [prop for prop in zone['props'] if prop.get('assetKey') in ('frontier_cinderfen_curtain_walk', 'frontier_cinderfen_gatehouse')]
records = []
for stair in stairs:
    origin = (stair['x'], stair['z'])
    stair_tree = tree(stair, origin)
    collisions = []
    for wall in walls:
        if math.hypot(wall['x'] - stair['x'], wall['z'] - stair['z']) > 24:
            continue
        contacts = stair_tree.overlap(tree(wall, origin))
        if contacts:
            vertices, faces = placed_geometry(stair, origin)
            points = [vertices[index] for face, _ in contacts for index in faces[face]]
            collisions.append({'wall': wall['id'], 'trianglePairs': len(contacts),
                               'contactBoundsRelativeToStairZUp': [[min(p[axis] for p in points) for axis in range(3)], [max(p[axis] for p in points) for axis in range(3)]]})
    records.append({'stair': stair['id'], 'wallIntersections': collisions})
report = {'method': 'Actual published LOD0 GLB triangle intersections at generated zone transforms; corner landing socket contacts excluded.',
          'candidateDiagonalInset': inset,
          'mapSha256': hashlib.sha256((REPO / 'public/assets/maps/cinderfen_outskirts.json').read_bytes()).hexdigest(),
          'placements': [{key: prop[key] for key in ('id', 'assetKey', 'x', 'y', 'z', 'rotY', 'scale', 'scaleX', 'scaleY', 'scaleZ') if key in prop} for prop in stairs + walls],
          'models': inputs, 'stairs': records, 'intersectingStairs': sum(bool(record['wallIntersections']) for record in records)}
(ROOT / ('review/stair-wall-fit-candidate.json' if inset else 'review/stair-wall-fit.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
