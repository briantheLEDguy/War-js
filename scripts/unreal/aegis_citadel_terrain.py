"""Portable, bounded terrain subtraction for the private citadel candidate.

The old sparse hall survey ended at X32600; the retained mountain begins crossing
floor Z6010 near X32800 and reaches Z6880 at the back wall X33400. Additional
throne/rear/edge probes below are survey inputs, never inferred native approvals.

Input positions are ACTOR-LOCAL centimetres. Occupied carve boxes are WORLD
centimetres and the unchanged actor transform is explicit. Original buffers and
all unaffected triangle indices/attributes remain verbatim. Crossing faces retain
input winding and source-corner barycentric UV/normal interpolation. Nothing here
loads Unreal, writes Content, hides an actor, or changes a published source mesh.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math


HALL_CARVE_WORLD = dict(id='occupied_commander_hall', coordinateSpace='world_cm',
                        bounds=[[25960.0, -4260.0, 5980.0], [33460.0, 4260.0, 24000.0]])
MOUNTAIN_ACTOR_TRANSFORM = dict(translationCm=[25000.0, 0.0, 0.0],
                               rotationQuaternion=[0.0, 0.0, 0.0, 1.0], scale=[1.0, 1.0, 1.0])
UPPER_EDIT_BOUNDS = [[13500.0, -9600.0, 2400.0], [34500.0, 9600.0, 24000.0]]
EPSILON_CM = 1e-7
AREA_EPSILON_CM2 = 1e-9


def _sum(values):
    """Match native Python 3.11's ordered binary64 reductions on every host.

    Python 3.12+ compensates builtin float sums. Changing reduction order changes
    byte-bound boundary positions and tangent/normal receipts by a few ULPs.
    """
    total = 0
    for value in values:
        total += value
    return total


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def _finite_vector(value, count, label):
    if (not isinstance(value, (list, tuple)) or len(value) != count or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value)):
        raise ValueError(label + ' must be a finite numeric vector.')


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _sub(a, b): return [a[i] - b[i] for i in range(3)]


def _unit(n):
    length = math.sqrt(_sum(v * v for v in n))
    if length < 1e-12: raise ValueError('A boundary normal cannot be interpolated from opposed source normals.')
    return [v / length for v in n]


def _point(weights, source):
    return [_sum(weights[j] * source[j][k] for j in range(3)) for k in range(3)]


def _area(poly, source):
    points = [_point(w, source) for w in poly]
    total = 0.0
    for b, c in zip(points[1:-1], points[2:]):
        n = _cross(_sub(b, points[0]), _sub(c, points[0]))
        total += math.sqrt(_sum(v * v for v in n)) / 2
    return total


def _clean(poly, source):
    clean = []
    for weights in poly:
        point = _point(weights, source)
        if not clean or math.dist(point, _point(clean[-1], source)) > EPSILON_CM: clean.append(weights)
    if len(clean) > 1 and math.dist(_point(clean[0], source), _point(clean[-1], source)) <= EPSILON_CM:
        clean.pop()
    return clean if len(clean) >= 3 and _area(clean, source) > AREA_EPSILON_CM2 else []


def _split(poly, source, axis, boundary, direction):
    """Split a convex source-face polygon; direction*(position-boundary)<=0 is inside."""
    inside, outside = [], []
    values = [direction * (_point(w, source)[axis] - boundary) for w in poly]
    if all(abs(value) <= EPSILON_CM for value in values): return poly, []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        da, db = values[i], values[(i + 1) % len(poly)]
        if da <= EPSILON_CM: inside.append(a)
        if da >= -EPSILON_CM: outside.append(a)
        if (da < -EPSILON_CM and db > EPSILON_CM) or (da > EPSILON_CM and db < -EPSILON_CM):
            t = da / (da - db)
            vertex = tuple(a[j] + (b[j] - a[j]) * t for j in range(3))
            inside.append(vertex)
            outside.append(vertex)
    return _clean(inside, source), _clean(outside, source)


def _subtract(poly, source, bounds):
    # The complement is decomposed into disjoint convex fragments. Do not simply
    # delete crossing triangles: their exterior portions must remain visible.
    remainder = poly
    exterior = []
    for axis in range(3):
        for boundary, direction in ((bounds[0][axis], -1), (bounds[1][axis], 1)):
            if not remainder: return exterior, 0.0
            remainder, fragment = _split(remainder, source, axis, boundary, direction)
            if fragment: exterior.append(fragment)
    removed_area = _area(remainder, source) if remainder else 0.0
    if removed_area <= AREA_EPSILON_CM2: return [poly], 0.0
    return exterior, removed_area


def _validated(mesh, volumes, actor_transform):
    if not isinstance(mesh, dict): raise ValueError('Terrain source must be an explicit mesh document.')
    positions, normals, uvs, indices = [mesh.get(k) for k in ('positions', 'normals', 'uvs', 'indices')]
    if not isinstance(positions, list) or not positions or len(positions) > 2_000_000:
        raise ValueError('Terrain vertex count is missing or unbounded.')
    if not isinstance(normals, list) or not isinstance(uvs, list) or len(normals) != len(positions) or len(uvs) != len(positions):
        raise ValueError('Source position/normal/UV cardinalities differ.')
    for p, n, uv in zip(positions, normals, uvs):
        _finite_vector(p, 3, 'Source position'); _finite_vector(n, 3, 'Source normal'); _finite_vector(uv, 2, 'Source UV')
        if _sum(v * v for v in n) < 1e-12: raise ValueError('Source normal is zero.')
    # Native corner seams must already be split in this indexed document. Readback
    # adapters may merge corners only when all attributes, including UVs, match.
    for name, size in (('vertexColors', 4), ('tangents', 3)):
        values = mesh.get(name)
        if values is None: continue
        if not isinstance(values, list) or len(values) != len(positions):
            raise ValueError(name + ' cardinality differs from positions.')
        for value in values: _finite_vector(value, size, name)
    signs = mesh.get('binormalSigns')
    if signs is not None and (not isinstance(signs, list) or len(signs) != len(positions) or
            any(isinstance(sign, bool) or not isinstance(sign, (int, float)) or not math.isfinite(sign) for sign in signs)):
        raise ValueError('Stored source binormal signs must be explicit finite values.')
    channels = mesh.get('uvChannels')
    if channels is not None:
        if not isinstance(channels, list) or not 1 <= len(channels) <= 8:
            raise ValueError('Source UV channel count is malformed.')
        for channel in channels:
            if not isinstance(channel, list) or len(channel) != len(positions):
                raise ValueError('Source UV channel cardinality differs from positions.')
            for uv in channel: _finite_vector(uv, 2, 'Source UV channel')
        if channels[0] != uvs: raise ValueError('Primary UVs differ from explicit native UV channel zero.')
    if any(key in mesh for key in ('cornerAttributes', 'vertexInstances', 'vertexAttributes',
                                  'colors', 'vertexTangents', 'binormalSign')):
        raise ValueError('Unsupported source attribute layout requires an explicit lossless readback adapter.')
    if (not isinstance(indices, list) or not indices or len(indices) % 3 or len(indices) > 6_000_000 or
            any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(positions) for i in indices)):
        raise ValueError('Terrain indices are malformed.')
    materials = mesh.get('triangleMaterials')
    if materials is not None and (not isinstance(materials, list) or len(materials) * 3 != len(indices) or
                                  any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in materials)):
        raise ValueError('Triangle material count is malformed.')
    if not isinstance(actor_transform, dict) or set(actor_transform) != {'translationCm', 'rotationQuaternion', 'scale'}:
        raise ValueError('The actor transform must be explicit.')
    _finite_vector(actor_transform['translationCm'], 3, 'Actor translation')
    if actor_transform['rotationQuaternion'] != [0, 0, 0, 1] or actor_transform['scale'] != [1, 1, 1]:
        raise ValueError('This carve requires the measured unchanged identity actor rotation/scale.')
    if not isinstance(volumes, list) or not 1 <= len(volumes) <= 12: raise ValueError('Carve volumes must be bounded.')
    ids = set()
    local = []
    for volume in volumes:
        if (not isinstance(volume, dict) or set(volume) != {'id', 'coordinateSpace', 'bounds'} or
                not isinstance(volume['id'], str) or not volume['id'] or volume['id'] in ids or
                volume['coordinateSpace'] != 'world_cm'):
            raise ValueError('Every occupied volume requires a unique identity and explicit world coordinates.')
        bounds = volume['bounds']
        if not isinstance(bounds, list) or len(bounds) != 2: raise ValueError('Carve bounds are malformed.')
        for vector in bounds: _finite_vector(vector, 3, 'Carve bounds')
        if any(bounds[0][i] >= bounds[1][i] or bounds[0][i] < UPPER_EDIT_BOUNDS[0][i] or
               bounds[1][i] > UPPER_EDIT_BOUNDS[1][i] for i in range(3)):
            raise ValueError('An occupied carve must stay strictly bounded to the approved upper precinct.')
        ids.add(volume['id'])
        local.append([[p[i] - actor_transform['translationCm'][i] for i in range(3)] for p in bounds])
    return positions, normals, uvs, indices, materials, local


def carve_terrain(mesh, volumes, *, actor_transform, source_provenance):
    """Subtract signed occupied world boxes from actor-local terrain faces.

    source_provenance is descriptive caller evidence and is bound, not treated as
    verified. Staging must independently read/hash the actual native mesh and actor
    before using this result. Native corner attributes must be split into the
    indexed source records; optional vertexColors/tangents/binormalSigns and all
    uvChannels are preserved. No source object, transform or buffer is mutated.
    """
    positions, normals, uvs, indices, materials, local_volumes = _validated(mesh, volumes, actor_transform)
    if not isinstance(source_provenance, dict): raise ValueError('Actual source provenance must be supplied explicitly.')
    result = deepcopy(mesh)
    result['indices'] = []
    if materials is not None: result['triangleMaterials'] = []
    identity = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    vertex_cache = {}
    unchanged, touched, fully_removed = [], [], []
    outside_rows = []
    boundary_vertices = []
    discarded_area = 0.0
    source_area = 0.0
    for offset in range(0, len(indices), 3):
        triangle = offset // 3
        ids = indices[offset:offset + 3]
        source = [positions[i] for i in ids]
        area = _area(identity, source)
        if area <= AREA_EPSILON_CM2: raise ValueError('Degenerate source face must be diagnosed before carving.')
        source_area += area
        polygons = [identity]
        removed = 0.0
        for bounds in local_volumes:
            next_polygons = []
            for poly in polygons:
                # This common path emits the original face without recomputing a
                # single source position, normal, UV or triangle index.
                points = [_point(w, source) for w in poly]
                if any(max(p[i] for p in points) < bounds[0][i] - EPSILON_CM or
                       min(p[i] for p in points) > bounds[1][i] + EPSILON_CM for i in range(3)):
                    next_polygons.append(poly); continue
                exterior, cut_area = _subtract(poly, source, bounds)
                next_polygons.extend(exterior); removed += cut_area
            polygons = next_polygons
            if len(polygons) > 512: raise ValueError('Carve fragmentation exceeds the bounded source-face budget.')
        start_triangle = len(result['indices']) // 3
        if removed <= AREA_EPSILON_CM2:
            result['indices'].extend(ids)
            if materials is not None: result['triangleMaterials'].append(materials[triangle])
            unchanged.append(triangle)
            outside_rows.append([triangle, ids, [positions[i] for i in ids], [normals[i] for i in ids],
                                 [uvs[i] for i in ids], materials[triangle] if materials is not None else None,
                                 {key: [mesh[key][i] for i in ids] for key in
                                  ('vertexColors', 'tangents', 'binormalSigns') if key in mesh},
                                 [[channel[i] for i in ids] for channel in mesh.get('uvChannels', [])]])
            if result['indices'][start_triangle * 3:start_triangle * 3 + 3] != ids:
                raise ValueError('Unchanged face indices drifted.')
            continue
        discarded_area += removed
        touched.append(triangle)
        if not polygons: fully_removed.append(triangle)
        source_normal = _cross(_sub(source[1], source[0]), _sub(source[2], source[0]))

        def emit_vertex(weights):
            for i, w in enumerate(weights):
                if w == 1.0 and all(weights[j] == 0.0 for j in range(3) if j != i): return ids[i]
            # Global source indices keep UV/hard-normal seams separate. Only
            # identical source interpolation weights share a new boundary vertex.
            sparse = tuple(sorted((ids[j], round(w, 15)) for j, w in enumerate(weights) if abs(w) > 1e-15))
            if sparse in vertex_cache: return vertex_cache[sparse]
            p = _point(weights, source)
            n = _unit([_sum(weights[j] * normals[ids[j]][k] for j in range(3)) for k in range(3)])
            uv = [_sum(weights[j] * uvs[ids[j]][k] for j in range(3)) for k in range(2)]
            attributes = {}
            if 'vertexColors' in mesh:
                attributes['vertexColors'] = [_sum(weights[j] * mesh['vertexColors'][ids[j]][k]
                                                   for j in range(3)) for k in range(4)]
            if 'tangents' in mesh:
                tangent = [_sum(weights[j] * mesh['tangents'][ids[j]][k] for j in range(3)) for k in range(3)]
                dot = _sum(tangent[k] * n[k] for k in range(3))
                contributing = [mesh['tangents'][ids[j]] for j in range(3) if weights[j] > 1e-15]
                # Registered defaults describe stored data, not authored validity.
                # Preserve a zero field instead of inventing an arbitrary tangent.
                attributes['tangents'] = [0.0, 0.0, 0.0] if all(all(v == 0 for v in t) for t in contributing) \
                    else _unit([tangent[k] - dot * n[k] for k in range(3)])
            if 'binormalSigns' in mesh:
                signs = {mesh['binormalSigns'][ids[j]] for j in range(3) if weights[j] > 1e-15}
                if len(signs) != 1:
                    raise ValueError('A carve boundary cannot interpolate a handedness seam; split source corners first.')
                attributes['binormalSigns'] = next(iter(signs))
            channel_uvs = [[_sum(weights[j] * channel[ids[j]][k] for j in range(3)) for k in range(2)]
                           for channel in mesh.get('uvChannels', [])]
            index = len(result['positions'])
            result['positions'].append(p); result['normals'].append(n); result['uvs'].append(uv)
            for key, value in attributes.items(): result[key].append(value)
            for channel, value in zip(result.get('uvChannels', []), channel_uvs): channel.append(value)
            vertex_cache[sparse] = index
            boundary_vertices.append(dict(index=index, sourceIndices=ids, weights=list(weights),
                                          position=p, normal=n, uv=uv, attributes=attributes, uvChannels=channel_uvs))
            return index

        for poly in polygons:
            for b, c in zip(poly[1:-1], poly[2:]):
                weights = [poly[0], b, c]
                points = [_point(w, source) for w in weights]
                n = _cross(_sub(points[1], points[0]), _sub(points[2], points[0]))
                if math.sqrt(_sum(v * v for v in n)) / 2 <= AREA_EPSILON_CM2: continue
                if _sum(n[k] * source_normal[k] for k in range(3)) <= 0:
                    raise ValueError('Clipping reversed the source winding.')
                result['indices'].extend(emit_vertex(w) for w in weights)
                if materials is not None: result['triangleMaterials'].append(materials[triangle])
    for key in ('positions', 'normals', 'uvs', 'vertexColors', 'tangents', 'binormalSigns'):
        if key not in mesh: continue
        if result[key][:len(mesh[key])] != mesh[key]: raise ValueError('Original vertex attributes changed.')
    for source_channel, result_channel in zip(mesh.get('uvChannels', []), result.get('uvChannels', [])):
        if result_channel[:len(source_channel)] != source_channel: raise ValueError('Original UV channel changed.')
    output_area = 0.0
    for offset in range(0, len(result['indices']), 3):
        output_area += _area(identity, [result['positions'][i] for i in result['indices'][offset:offset + 3]])
    if abs(source_area - output_area - discarded_area) > max(1e-4, source_area * 1e-10):
        raise ValueError('The terrain surface area does not reconcile after bounded subtraction.')
    receipt = dict(schemaVersion=1, geometryOnly=True, coordinateSpace='actor_local_cm',
                   actorTransform=deepcopy(actor_transform), worldVolumes=deepcopy(volumes), localVolumeBounds=local_volumes,
                   sourceProvenance=deepcopy(source_provenance), sourceMeshSha256=_sha(mesh), outputMeshSha256=_sha(result),
                   method='convex_halfspace_difference_source_corner_barycentrics',
                   winding='preserve_input_index_order', normalInterpolation='linear_source_normals_then_unit',
                   uvInterpolation='linear_source_uvs', tangentInterpolation='preserve_zero_otherwise_linear_then_orthogonalize_and_unit',
                   vertexColorInterpolation='linear_without_clamping', binormalInterpolation='preserve_uniform_stored_source_value',
                   sourceTriangles=len(indices) // 3,
                   outputTriangles=len(result['indices']) // 3, touchedSourceTriangles=touched,
                   fullyRemovedSourceTriangles=fully_removed, addedBoundaryVertices=boundary_vertices,
                   discardedSurfaceAreaCm2=discarded_area,
                   outsidePreservation=dict(triangles=len(unchanged), sourceTriangleIds=unchanged,
                       sourceTriangleAttributesSha256=_sha(outside_rows), originalVertexBufferPrefixPreserved=True,
                       sourcePositionsSha256=_sha(positions), sourceNormalsSha256=_sha(normals), sourceUvsSha256=_sha(uvs),
                       additionalAttributeSha256={key: _sha(mesh[key]) for key in
                           ('vertexColors', 'tangents', 'binormalSigns', 'uvChannels') if key in mesh}),
                   nativeSourceVerified=False, nativeCollisionVerified=False, visualApproved=False)
    return result, receipt


def hall_terrain_probe_points():
    """Actual native traces must cover the missed throne/rear strip and wall edges."""
    x_values = [26000, 27820, 28900, 29900, 30600, 31500, 31800, 32600, 32630,
                32800, 33000, 33200, 33286, 33300, 33400, 33460]
    y_values = [-4210, -3500, -2400, -1600, -800, 0, 800, 1600, 2400, 3500, 4210]
    return [dict(id='hall_retained_terrain_rear_edges', point=[x, y, 6010]) for x in x_values for y in y_values]


def checked_native_terrain_source(export, expected_mesh):
    """Accept committed corner-expanded source only; no cached/GLB substitution."""
    if (not isinstance(export, dict) or type(export.get('schemaVersion')) is not int or export['schemaVersion'] != 1
            or export.get('readOnly') is not True
            or export.get('available') is not True or export.get('valid') is not True or export.get('lod') != 0
            or type(export.get('lod')) is not int or export.get('mesh') != expected_mesh
            or type(export.get('invalidValues')) is not int or export['invalidValues'] != 0
            or export.get('sourcePolicy') != 'committed_mesh_description_bulk_data_no_working_copy'
            or export.get('coordinateSpace') != 'mesh_local_cm'
            or export.get('triangleOrder') != 'native_triangle_ids_and_corner_order'
            or export.get('optionalAttributePolicy') != 'stored_registered_values_authorship_not_inferred'):
        raise ValueError('Actual committed native terrain source export is unavailable or changed identity.')
    data = export.get('data')
    _validated(data, [HALL_CARVE_WORLD], MOUNTAIN_ACTOR_TRANSFORM)
    if not isinstance(data.get('uvChannels'), list) or not data['uvChannels']:
        raise ValueError('Actual committed native terrain UV channels are required.')
    triangles = len(data['indices']) // 3
    corners = len(data['positions'])
    if (corners != triangles * 3 or data['indices'] != list(range(corners))
            or type(export.get('sourceTriangleCount')) is not int or export['sourceTriangleCount'] != triangles
            or any(type(export.get(key)) is not int or export[key] <= 0 for key in
                   ('sourceVertexCount', 'sourceVertexInstanceCount'))):
        raise ValueError('Native terrain source is not the actual expanded triangle-corner ordering.')
    for key, count in (('triangleIds', triangles), ('trianglePolygonIds', triangles),
                       ('trianglePolygonGroupIds', triangles), ('cornerVertexIds', corners),
                       ('cornerVertexInstanceIds', corners)):
        values = export.get(key)
        if (not isinstance(values, list) or len(values) != count
                or any(type(value) is not int or value < 0 for value in values)):
            raise ValueError('Native terrain source identity array is missing: ' + key)
    if len(set(export['triangleIds'])) != triangles:
        raise ValueError('Native terrain source repeats a committed triangle identity.')
    slots, groups = export.get('materialSlots'), export.get('polygonGroups')
    if (not isinstance(slots, list) or not slots or any(not isinstance(row, dict)
            or row.get('index') != index or not isinstance(row.get('slotName'), str)
            or not isinstance(row.get('importedSlotName'), str)
            or row.get('material') is not None and (not isinstance(row['material'], str)
                or not row['material'].startswith(('/Game/', '/Engine/')) or '..' in row['material'])
            for index, row in enumerate(slots))):
        raise ValueError('Native terrain material slots are unavailable or malformed.')
    if (not isinstance(groups, list) or not groups or any(not isinstance(row, dict)
            or type(row.get('id')) is not int or row['id'] < 0 or not isinstance(row.get('slotName'), str)
            or type(row.get('materialIndex')) is not int or not 0 <= row['materialIndex'] < len(slots)
            for row in groups) or len({row['id'] for row in groups}) != len(groups)):
        raise ValueError('Native terrain polygon-group material identities are malformed.')
    group_materials = {row['id']: row['materialIndex'] for row in groups}
    if 'triangleMaterials' not in data or any(group_materials.get(group) != material
            or not slots[material]['material'] for group, material in
            zip(export['trianglePolygonGroupIds'], data['triangleMaterials'])):
        raise ValueError('Native terrain source material mapping differs from committed polygon groups.')
    # Keep metadata alongside the raw export, not as incorrectly remapped output
    # triangle arrays. All actual per-corner attribute arrays are copied verbatim.
    return deepcopy(data)


def native_terrain_carve_document(source_payload, *, source_provenance):
    """Bound native import document; accepts only the actual committed mountain export."""
    source_mesh = '/Game/Capitals/crownward/Terrain_mountain.Terrain_mountain'
    if not isinstance(source_payload, str): raise ValueError('The exact native source JSON payload is required.')
    export = json.loads(source_payload)
    data = checked_native_terrain_source(export, source_mesh)
    output, receipt = carve_terrain(data, [HALL_CARVE_WORLD], actor_transform=MOUNTAIN_ACTOR_TRANSFORM,
                                    source_provenance=source_provenance)
    return dict(schemaVersion=1, sourceMesh=source_mesh, sourceExportPayload=source_payload,
        sourceExportSha256=hashlib.sha256(source_payload.encode('utf-8')).hexdigest(),
        actorTransform=deepcopy(MOUNTAIN_ACTOR_TRANSFORM), worldVolumes=[deepcopy(HALL_CARVE_WORLD)],
        localVolumeBounds=receipt['localVolumeBounds'], data=output, carveReceipt=receipt)
