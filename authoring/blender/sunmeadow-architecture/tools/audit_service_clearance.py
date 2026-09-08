"""Read-only headroom sampling at composed NPC, service, keep and entrance positions."""
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]


def geometry(stem):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    model = ROOT/'runtime'/(stem+'_lod0.glb')
    bpy.ops.import_scene.gltf(filepath=str(model))
    vertices, faces = [], []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in polygon.vertices) for polygon in obj.data.polygons)
    return BVHTree.FromPolygons(vertices, faces), {'model': model.name, 'sha256': hashlib.sha256(model.read_bytes()).hexdigest()}


if __name__ == '__main__':
    source = ROOT/'review/composition_audit.json'
    composed = json.loads(source.read_text())
    models = {prop['assetKey']: geometry(prop['assetKey']) for prop in {p['assetKey']:p for p in composed['architecture']}.values()}
    points = composed['servicePoints'] + [{'id': e['id']+'_entrance', **e['entrance']} for e in composed['entrances']]
    blocked, rays = [], 0
    for point in points:
        for prop in composed['architecture']:
            if math.hypot(point['x']-prop['x'], point['z']-prop['z']) > 20:
                continue
            tree = models[prop['assetKey']][0]
            angle = prop.get('rotY', 0)
            scale = prop.get('scale', 1)
            for dx in [-.5, -.25, 0, .25, .5]:
                for dz in [-.5, -.25, 0, .25, .5]:
                    if dx*dx+dz*dz > .250001:
                        continue
                    wx, wz = point['x']+dx-prop['x'], point['z']+dz-prop['z']
                    lx = (math.cos(angle)*wx-math.sin(angle)*wz)/scale
                    lz = (math.sin(angle)*wx+math.cos(angle)*wz)/scale
                    bottom = (point.get('y', 0)+.3-prop.get('y', 0))/scale
                    start = Vector((lx, -lz, bottom))
                    hit, _, _, _ = tree.ray_cast(start, Vector((0, 0, 1)), 1.9/scale)
                    rays += 1
                    if hit is not None:
                        blocked.append({'point': point['id'], 'modelInstance': prop['id'], 'footprintOffset': [dx, dz], 'local_z_up_hit': list(hit)})
    result = {'method': 'Actual LOD0 GLB surfaces, 13 vertical rays over a 0.5m radius at each NPC/service/keep-use position and building entrance. Samples cover 0.3m to 2.2m above ground; authored floor thickness is excluded. This is sampled headroom, supplemented by collision/BFS tests, not a continuous swept-volume proof.', 'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'composition_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'source_sha256': composed['sourceSha256'], 'models': [value[1] for value in models.values()], 'points': points, 'rays': rays, 'blocked_rays': blocked}
    (ROOT/'review/service_clearance_audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print('SERVICE_CLEARANCE '+json.dumps({'points': len(points), 'rays': rays, 'blocked_rays': blocked}), flush=True)
