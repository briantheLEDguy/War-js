"""Independently audit exported full-capsule projection diagnostics.

Saved certificates are evidence only. They never authorize native movement.
Decimal projections audit the recorded axis rather than repeating native axis
selection or trusting the native separation boolean.
"""
import math
from decimal import Decimal, localcontext
from citadel_capsule_distance import _v, sub, cross, dot


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Certificate numbers must be finite')
    return float(value)


def _interval(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError('A complete projection interval is required')
    result = tuple(_number(x) for x in value)
    if result[0] > result[1]:
        raise ValueError('Projection interval extrema are reversed')
    return result


def audit_separating_plane(start, end, radius, vertices, certificate):
    start, end = _v(start), _v(end)
    radius = _number(radius)
    if radius <= 0 or radius > 1e6 or not isinstance(vertices, (list, tuple)) or len(vertices) != 3:
        raise ValueError('The full capsule and complete triangle are required')
    vertices = tuple(_v(p) for p in vertices)
    if (type(certificate.get('certificateVersion')) is not int or certificate['certificateVersion'] != 1
            or type(certificate.get('guardPolicyVersion')) is not int or certificate['guardPolicyVersion'] != 1):
        raise ValueError('The projection certificate and guard policy must be versioned')
    if certificate.get('projectionAxisRecorded') is not True:
        raise ValueError('The winning projection axis is missing')
    axis = _v(certificate['separatingUnitAxis'])
    origin = _v(certificate['projectionOriginCm'])
    squared_norm = math.fsum(x*x for x in axis)
    if abs(squared_norm - 1) > 1e-10 or abs(_number(certificate['separatingAxisSquaredLength']) - squared_norm) > 1e-12:
        raise ValueError('The projection axis must have unit length')
    if any(abs(origin[i] - (start[i] + end[i])*.5) > 1e-8 for i in range(3)):
        raise ValueError('The projection origin differs from the recorded capsule midpoint')
    longest = max(math.dist(vertices[i], vertices[(i+1) % 3]) for i in range(3))
    normal = cross(sub(vertices[1], vertices[0]), sub(vertices[2], vertices[0]))
    if longest*longest <= 1e-12 or math.sqrt(dot(normal, normal)) <= longest*longest*1e-6:
        raise ValueError('Degenerate or numerically skinny triangles cannot certify separation')
    magnitude = max(radius, *(abs(x) for point in (start, end, *vertices) for x in point))
    expected_guard = max(.001, 32*(2**-23)*(magnitude + longest + radius + math.dist(start, end)))
    guard = _number(certificate['numericalGuardCm'])
    if guard < expected_guard - max(1e-12, expected_guard*1e-12):
        raise ValueError('The numerical guard was reduced')
    with localcontext() as context:
        context.prec = 80
        d = Decimal.from_float
        support = d(radius)*sum((d(x)*d(x) for x in axis), Decimal(0)).sqrt()
        def projection(point):
            return sum(((d(point[i])-d(origin[i]))*d(axis[i]) for i in range(3)), Decimal(0))
        caps = tuple(projection(point) for point in (start, end))
        triangle = tuple(projection(point) for point in vertices)
        capsule_interval = (float(min(caps)-support), float(max(caps)+support))
        triangle_interval = (float(min(triangle)), float(max(triangle)))
    # This tolerance checks serialization and arithmetic agreement; it is never
    # subtracted from the required geometric guard to turn contact into clearance.
    for recorded, actual in ((certificate['capsuleProjectionCm'], capsule_interval),
                             (certificate['triangleProjectionCm'], triangle_interval)):
        if any(abs(a-b) > max(1e-8, abs(b)*1e-12) for a,b in zip(_interval(recorded), actual)):
            raise ValueError('Exported projection extrema do not cover the complete objects')
    above = triangle_interval[0] - capsule_interval[1]
    below = capsule_interval[0] - triangle_interval[1]
    gap = max(above, below)
    direction = 'triangle_above_capsule' if above >= below else 'capsule_above_triangle'
    if (abs(_number(certificate['gapTriangleAfterCapsuleCm'])-above) > 1e-8
            or abs(_number(certificate['gapCapsuleAfterTriangleCm'])-below) > 1e-8):
        raise ValueError('Both directed interval gaps must agree with independent projection')
    if certificate['projectionGapDirection'] != direction or abs(_number(certificate['separatingPlaneGapCm'])-gap) > 1e-8:
        raise ValueError('Exported separating gap disagrees with complete interval projections')
    certified = gap > guard
    if type(certificate.get('fullCapsuleSeparationCertified')) is not bool or certificate['fullCapsuleSeparationCertified'] != certified:
        raise ValueError('The native certificate disagrees with its independently projected gap')
    return dict(diagnosticOnly=True, independentProjectionAuditPassed=True,
                fullCapsuleSeparated=certified, separatingPlaneGapCm=gap,
                numericalGuardCm=guard, admissionGranted=False)
