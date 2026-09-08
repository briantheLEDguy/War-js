"""Confirm conservative building envelope overlap against actual exported triangles."""
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

ROOT = Path(__file__).resolve().parents[1]


def imported_geometry(stem, x, z, angle):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    model = ROOT / 'runtime' / (stem + '_lod0.glb')
    bpy.ops.import_scene.gltf(filepath=str(model))
    transform = Matrix.Translation((x, -z, 0)) @ Matrix.Rotation(angle, 4, 'Z')
    vertices, triangles = [], []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        offset = len(vertices)
        vertices.extend(transform @ obj.matrix_world @ v.co for v in obj.data.vertices)
        triangles.extend(tuple(offset + i for i in tri.vertices) for tri in obj.data.loop_triangles)
    return vertices, triangles, {'model': model.name, 'sha256': hashlib.sha256(model.read_bytes()).hexdigest(), 'placement': {'x': x, 'z': z, 'rotY': angle}}


def segment_triangle(start, end, tri):
    delta = end - start
    length = delta.length
    if length < 1e-8:
        return None
    direction = delta / length
    point = intersect_ray_tri(*tri, direction, start, True)
    if point is not None and 1e-5 < (point - start).dot(direction) < length - 1e-5:
        return point
    return None


def audit(salvage_z):
    a, af, am = imported_geometry('frontier_sunmeadow_supply_post', -401, salvage_z, .35)
    b, bf, bm = imported_geometry('frontier_sunmeadow_workshop', -397, -244, -math.pi/2)
    candidates = BVHTree.FromPolygons(a, af, all_triangles=True).overlap(BVHTree.FromPolygons(b, bf, all_triangles=True))
    points = []
    pairs = 0
    for ai, bi in candidates:
        at, bt = [a[i] for i in af[ai]], [b[i] for i in bf[bi]]
        hits = []
        for src, target in [(at, bt), (bt, at)]:
            for i in range(3):
                hit = segment_triangle(src[i], src[(i+1)%3], target)
                if hit is not None:
                    hits.append([round(hit.x, 5), round(hit.z, 5), round(-hit.y, 5)])
        if hits:
            pairs += 1
            if len(points) < 20:
                points.extend(hits)
    return {'models': [am, bm], 'candidate_triangle_pairs': len(candidates), 'confirmed_intersecting_triangle_pairs': pairs, 'sample_intersection_points_runtime_xyz': points[:20]}


if __name__ == '__main__':
    result = {'method': 'LOD0 actual GLB reimport triangles placed in world. BVH pairs are confirmed with bounded edge/triangle segment intersections, excluding endpoints within 10 micrometres.', 'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'original': audit(-253), 'proposed': audit(-256)}
    (ROOT/'review/building_pair_audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PAIR_AUDIT ' + json.dumps(result), flush=True)
