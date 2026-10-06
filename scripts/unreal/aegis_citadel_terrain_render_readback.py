"""Compare actual original/clone render buffers for the measured terrain cut.

Committed topology/attributes are a separate mandatory comparison. This module
permits a regenerated lightmap atlas only when the original native build policy
declares that destination channel. It grants no collision or visual approval.
"""
from collections import defaultdict
import hashlib
import itertools
import json
import math

RENDER_POLICY = 'actual_render_index_order_oriented_triangle_corners'
POSITION_TOLERANCE_CM = .1
BASIS_DOT_THRESHOLD = .995
UV_ABSOLUTE_TOLERANCE = .0005
UV_RELATIVE_TOLERANCE = .001
GENERATED_UV_RANGE_TOLERANCE = .001


def _finite_vector(value, count):
    return (isinstance(value, list) and len(value) == count
            and all(type(v) in (int, float) and math.isfinite(v) for v in value))


def _integer(value):
    return type(value) is int and value >= 0


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _unit_dot(a, b):
    return _dot(a, b) / math.sqrt(_dot(a, a) * _dot(b, b))


def _uv_same(a, b):
    return all(abs(x - y) <= max(UV_ABSOLUTE_TOLERANCE,
               max(abs(x), abs(y)) * UV_RELATIVE_TOLERANCE) for x, y in zip(a, b))


def _channels(policy, committed_channels, rendered_channels):
    if (not isinstance(policy, dict) or policy.get('sourceLods') != 1
            or len(policy.get('buildSettings', [])) != 1
            or len(policy.get('reductionSettings', [])) != 1):
        raise ValueError('Actual single-LOD original terrain build policy is required')
    build, reduction = policy['buildSettings'][0], policy['reductionSettings'][0]
    if (not isinstance(build, dict) or not isinstance(reduction, dict)
            or build.get('buildScale3D') != {'x': 1, 'y': 1, 'z': 1}
            or policy.get('mesh', {}).get('nanite_settings', {}).get('bEnabled') is not False
            or reduction.get('percentTriangles') != 1 or reduction.get('percentVertices') != 1
            or reduction.get('maxDeviation') != 0 or reduction.get('bRecalculateNormals') is not False
            or type(build.get('bGenerateLightmapUVs')) is not bool):
        raise ValueError('Unsupported or incomplete actual terrain render policy')
    generated = []
    if build['bGenerateLightmapUVs']:
        source, destination = build.get('srcLightmapIndex'), build.get('dstLightmapIndex')
        if (not _integer(source) or source >= committed_channels or not _integer(destination)
                or destination >= rendered_channels or source == destination):
            raise ValueError('Generated lightmap destination is not declared by original policy')
        generated = [destination]
    authored = [channel for channel in range(committed_channels) if channel not in generated]
    if set(authored + generated) != set(range(rendered_channels)):
        raise ValueError('A rendered UV channel has no committed or generated source policy')
    return authored, generated


def _render(document, mesh, expected_triangles, channels, generated):
    if (not isinstance(document, dict) or document.get('schemaVersion') != 1
            or any(document.get(key) is not True for key in ('readOnly', 'available', 'valid'))
            or document.get('mesh') != mesh or document.get('lod') != 0
            or document.get('policy') != RENDER_POLICY or document.get('invalidValues') != 0
            or document.get('uvChannels') != channels
            or not isinstance(document.get('triangles'), list)
            or len(document['triangles']) != expected_triangles):
        raise ValueError('Complete actual original/clone rendered-face readback is required')
    identities = set()
    for face in document['triangles']:
        if (not isinstance(face, dict) or any(not _integer(face.get(key)) for key in ('index', 'section', 'materialIndex'))
                or face['index'] in identities or not isinstance(face.get('vertexIds'), list)
                or len(face['vertexIds']) != 3 or any(not _integer(v) for v in face['vertexIds'])
                or any(not isinstance(face.get(key), list) or len(face[key]) != 3
                       or any(not _finite_vector(v, 3) for v in face[key])
                       for key in ('positions', 'normals', 'tangents', 'binormals'))
                or not isinstance(face.get('uvChannels'), list) or len(face['uvChannels']) != channels
                or any(not isinstance(channel, list) or len(channel) != 3
                       or any(not _finite_vector(v, 2) for v in channel) for channel in face['uvChannels'])):
            raise ValueError('Actual rendered face identity or attributes are incomplete')
        identities.add(face['index'])
        for corner in range(3):
            axes = [face[key][corner] for key in ('tangents', 'binormals', 'normals')]
            if (any(abs(_dot(axis, axis) - 1) > tolerance + 1e-7
                    for axis, tolerance in zip(axes, (.02, .04, .02)))
                    or any(abs(_unit_dot(a, b)) > .02 + 1e-7 for a, b in itertools.combinations(axes, 2))):
                raise ValueError('Actual rendered normal/tangent/binormal basis is invalid')
        if any(v < -GENERATED_UV_RANGE_TOLERANCE or v > 1 + GENERATED_UV_RANGE_TOLERANCE
               for channel in generated for uv in face['uvChannels'][channel] for v in uv):
            raise ValueError('Actual generated lightmap UV is outside its finite atlas range')
    if identities != set(range(expected_triangles)):
        raise ValueError('Actual render index-order face identities are missing or duplicated')
    return document['triangles']


class _Faces:
    def __init__(self, faces, authored):
        self.faces, self.authored, self.used = faces, authored, set()
        self.buckets = defaultdict(list)
        for index, face in enumerate(faces):
            for rotation, point in enumerate(face['positions']):
                self.buckets[(face['materialIndex'], *self._cell(point))].append((index, rotation))

    @staticmethod
    def _cell(point):
        return tuple(math.floor(v / POSITION_TOLERANCE_CM) for v in point)

    def take(self, expected, compare_basis=False):
        cell = self._cell(expected['positions'][0])
        matches = []
        for delta in itertools.product((-1, 0, 1), repeat=3):
            key = (expected['materialIndex'], *(a + b for a, b in zip(cell, delta)))
            for index, rotation in self.buckets.get(key, ()):
                if index in self.used:
                    continue
                face = self.faces[index]
                order = [(corner + rotation) % 3 for corner in range(3)]
                if (any(math.dist(a, face['positions'][b]) > POSITION_TOLERANCE_CM
                        for a, b in zip(expected['positions'], order))
                        or any(not _uv_same(expected['uvChannels'][channel][corner], face['uvChannels'][channel][actual])
                               for channel in self.authored for corner, actual in enumerate(order))
                        or compare_basis and any(_unit_dot(expected[key][corner], face[key][actual]) < BASIS_DOT_THRESHOLD
                            for key in ('normals', 'tangents', 'binormals') for corner, actual in enumerate(order))):
                    continue
                matches.append((index, rotation))
        if not matches:
            raise ValueError('Actual rendered exterior/fragment position, material, winding, UV or basis changed')
        # Coincident faces remain a multiset. Basis-aware selection cannot consume
        # a different seam merely because its position and UV happen to coincide.
        index, rotation = min(matches)
        self.used.add(index)
        face = self.faces[index]
        return dict(face, **{key: [face[key][(corner + rotation) % 3] for corner in range(3)]
                    for key in ('positions', 'normals', 'tangents', 'binormals')},
                    uvChannels=[[channel[(corner + rotation) % 3] for corner in range(3)] for channel in face['uvChannels']])


def _extent(points, transform):
    if not points:
        return None
    translation, scale, quaternion = (transform.get(key) for key in ('translationCm', 'scale', 'rotationQuaternion'))
    if (not _finite_vector(translation, 3) or not _finite_vector(scale, 3)
            or not _finite_vector(quaternion, 4) or abs(_dot(quaternion, quaternion) - 1) > 1e-9):
        raise ValueError('The exact source actor transform is required for measured world extent')
    x, y, z, w = quaternion
    world = []
    for point in points:
        p = [a * b for a, b in zip(point, scale)]
        cross = [y*p[2]-z*p[1], z*p[0]-x*p[2], x*p[1]-y*p[0]]
        cross2 = [y*cross[2]-z*cross[1], z*cross[0]-x*cross[2], x*cross[1]-y*cross[0]]
        world.append([translation[i] + p[i] + 2*w*cross[i] + 2*cross2[i] for i in range(3)])
    return [[min(p[i] for p in world) for i in range(3)], [max(p[i] for p in world) for i in range(3)]]


def checked_rendered_carve(wrapper, source_render, clone_render, source_policy, target_mesh):
    """Verify all unchanged exterior faces and the exact original touched-vertex star.

    This consumes actual render exports, never authored-normal correspondence.
    The caller must also run checked_committed_carve with original stored topology.
    """
    payload = wrapper.get('sourceExportPayload')
    if (wrapper.get('schemaVersion') != 1 or not isinstance(payload, str)
            or hashlib.sha256(payload.encode()).hexdigest() != wrapper.get('sourceExportSha256')):
        raise ValueError('Original raw committed source payload SHA changed')
    original = json.loads(payload)
    source, clipped, receipt = original['data'], wrapper['data'], wrapper['carveReceipt']
    count = len(source['indices']) // 3
    if (original.get('mesh') != wrapper.get('sourceMesh') or source['indices'] != list(range(count * 3))
            or len(original.get('cornerVertexIds', [])) != count * 3
            or len(original.get('triangleIds', [])) != count or len(set(original['triangleIds'])) != count
            or any(not _integer(v) for v in original['cornerVertexIds'])
            or len(clipped['indices']) % 3):
        raise ValueError('Original committed corner and native triangle identity mapping is incomplete')
    outside, touched = receipt['outsidePreservation']['sourceTriangleIds'], receipt['touchedSourceTriangles']
    if (any(not isinstance(values, list) or values != sorted(set(values)) or any(not _integer(v) or v >= count for v in values)
            for values in (outside, touched)) or set(outside) & set(touched)
            or set(outside) | set(touched) != set(range(count))):
        raise ValueError('Measured touched/exterior source triangle ledger is incomplete')
    touched_vertices = {original['cornerVertexIds'][offset] for face in touched for offset in range(face*3, face*3+3)}
    star = [face for face in range(count) if touched_vertices.intersection(original['cornerVertexIds'][face*3:face*3+3])]
    excluded = sorted(set(star) & set(outside))
    channels = source_render.get('uvChannels')
    if not _integer(channels) or channels < 1:
        raise ValueError('Actual original rendered UV channel count is missing')
    authored, generated = _channels(source_policy, len(source['uvChannels']), channels)
    before = _render(source_render, original['mesh'], count, channels, generated)
    after = _render(clone_render, target_mesh, len(clipped['indices'])//3, channels, generated)
    source_faces, clone_faces = _Faces(before, authored), _Faces(after, authored)
    baseline = {}
    for face in range(count):
        corners = source['indices'][face*3:face*3+3]
        expected = dict(materialIndex=source['triangleMaterials'][face], positions=[source['positions'][i] for i in corners],
                        uvChannels=[[channel[i] for i in corners] for channel in source['uvChannels']])
        baseline[face] = source_faces.take(expected)
    for face in outside:
        clone_faces.take(baseline[face], compare_basis=face not in excluded)
    # Every remaining fragment must also match the actual committed clipped face.
    unchanged = {tuple(source['indices'][face*3:face*3+3]) for face in outside}
    fragments = 0
    for offset in range(0, len(clipped['indices']), 3):
        corners = clipped['indices'][offset:offset+3]
        if tuple(corners) in unchanged:
            unchanged.remove(tuple(corners))
            continue
        expected = dict(materialIndex=clipped['triangleMaterials'][offset//3], positions=[clipped['positions'][i] for i in corners],
                        uvChannels=[[channel[i] for i in corners] for channel in clipped['uvChannels']])
        clone_faces.take(expected)
        fragments += 1
    if unchanged or len(clone_faces.used) != len(after):
        raise ValueError('A clipped/exterior actual rendered face was missing or duplicated')
    star_points = [source['positions'][i] for face in star for i in range(face*3, face*3+3)]
    return dict(version=1, comparisonPolicy='actual_original_clone_oriented_rendered_faces_exact_source_vertex_star',
        sourceMesh=original['mesh'], targetMesh=target_mesh, lod=0,
        sourceTriangles=count, cloneTriangles=len(after), exteriorTriangles=len(outside), fragmentTriangles=fragments,
        exteriorSourceTriangleIds=[original['triangleIds'][i] for i in outside],
        touchedSourceVertexIds=sorted(touched_vertices), touchedVertexStarSourceTriangleIds=[original['triangleIds'][i] for i in star],
        computedBasisExcludedSourceTriangleIds=[original['triangleIds'][i] for i in excluded],
        computedBasisComparedTriangles=len(outside)-len(excluded),
        touchedVertexStarLocalBounds=_extent(star_points, {'translationCm':[0,0,0],'scale':[1,1,1],'rotationQuaternion':[0,0,0,1]}),
        touchedVertexStarWorldBounds=_extent(star_points, wrapper['actorTransform']),
        authoredUvChannels=authored, generatedDestinationUvChannels=generated,
        sourcePositionToleranceCm=POSITION_TOLERANCE_CM, sourceBasisDotThreshold=BASIS_DOT_THRESHOLD,
        sourceUvAbsoluteTolerance=UV_ABSOLUTE_TOLERANCE, sourceUvRelativeTolerance=UV_RELATIVE_TOLERANCE,
        generatedUvRangeTolerance=GENERATED_UV_RANGE_TOLERANCE,
        nativeExteriorRenderPreserved=True, nativeExteriorComputedBasisPreserved=True,
        committedTopologyComparisonRequired=True,
        nativeCollisionVerified=False, visualApproved=False, published=False)
