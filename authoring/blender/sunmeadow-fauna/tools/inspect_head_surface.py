"""Measure literal head-surface drift across a torso cage rebuild."""
import json
import hashlib
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from static_normals import unpack, accessor

ROOT = Path(__file__).resolve().parents[1]
paths = [ROOT/'checkpoints/buck-combined-before-pelvis/frontier_sunmeadow_roe_deer_buck_lod0.glb',
         ROOT/'runtime/frontier_sunmeadow_roe_deer_buck_lod0.glb']
records = []
for path in paths:
    payload = path.read_bytes(); doc, binary, _ = unpack(payload)
    points, triangles = [], []
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            positions = accessor(doc, binary, primitive['attributes']['POSITION'])
            indices = accessor(doc, binary, primitive['indices']).reshape(-1, 3)
            triangles.extend((indices+len(points)).tolist()); points.extend(positions.tolist())
    values = np.asarray(points)
    head = values[(values[:, 1]>.76)&(values[:, 2]>.40)]
    records.append((path, hashlib.sha256(payload).hexdigest(), head, BVHTree.FromPolygons(points, triangles, all_triangles=True)))
directions = []
for source, target in [(records[0], records[1]), (records[1], records[0])]:
    distances = np.asarray([target[3].find_nearest(Vector(point))[3] for point in source[2]])
    directions.append({'from': source[0].relative_to(ROOT).as_posix(), 'to': target[0].relative_to(ROOT).as_posix(),
                       'samples': len(distances), 'maximum_surface_distance_m': float(distances.max()),
                       'p99_surface_distance_m': float(np.percentile(distances, 99))})
report = {'sources': {path.relative_to(ROOT).as_posix(): digest for path, digest, _, _ in records},
          'directed_surface_comparisons': directions, 'status': 'diagnostic_not_visual_approval'}
(ROOT/'review/buck_head_surface_comparison.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2), flush=True)
