"""Portable source/proof bindings for immutable world-X citadel ramp profiles."""
import hashlib
import json
import math
import re

PROFILE_FIELDS = {'schemaVersion', 'routeId', 'kind', 'meshId', 'knotsCm', 'boundaryPolicy', 'construction'}
SURFACE_METHOD = 'signed_world_x_piecewise_linear_per_lane_and_movement_step'
ABSENT = object()


def _fail(reason):
    raise ValueError('Invalid signed citadel route surface: ' + reason)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value) and abs(value) <= 1_000_000


def _point(value):
    return isinstance(value, list) and len(value) == 3 and all(_finite(v) for v in value)


def _same(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if type(a) in (int, float) and type(b) in (int, float):
        return a == b
    return type(a) is type(b) and a == b


def checked_profile(value):
    if (not isinstance(value, dict) or set(value) != PROFILE_FIELDS or type(value.get('schemaVersion')) is not int
            or value['schemaVersion'] != 1 or not isinstance(value.get('routeId'), str)
            or not re.fullmatch('[a-z0-9_]{1,80}', value['routeId']) or value.get('kind') != 'world_x_piecewise_linear'
            or value.get('meshId') != 'stairs_and_balconies'
            or value.get('boundaryPolicy') != 'closed_profile_domain_shared_boundaries_same_height'
            or value.get('construction') != 'continuous_paved_fan_ramp'
            or not isinstance(value.get('knotsCm'), list) or not 2 <= len(value['knotsCm']) <= 64
            or any(not isinstance(k, list) or len(k) != 2 or not all(_finite(v) for v in k) for k in value['knotsCm'])):
        _fail('schema, identity or knots')
    for a, b in zip(value['knotsCm'], value['knotsCm'][1:]):
        if b[0] <= a[0] or 1 / math.hypot(1, (b[1]-a[1])/(b[0]-a[0])) < .7:
            _fail('nonmonotonic X or unwalkable authored slope')
    return value


def surface_height(profile, x):
    knots = profile['knotsCm']
    if not _finite(x) or x < knots[0][0] or x > knots[-1][0]:
        _fail('sample escaped the closed profile domain')
    for a, b in zip(knots, knots[1:]):
        if x <= b[0]:
            return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
    return knots[-1][1]


def checked_profiles(values, routes):
    if values is ABSENT:
        return {}
    if not isinstance(values, list) or len(values) > 16:
        _fail('bounded profile list')
    result = {}
    for value in values:
        checked_profile(value)
        route = next((r for r in routes if r['id'] == value['routeId']), None)
        if (not route or value['routeId'] in result or not _finite(route.get('width')) or route['width'] < 600
                or not isinstance(route.get('points'), list) or len(route['points']) < 2
                or any(not _point(p) or abs(p[2]-surface_height(value, p[0])) > .01 for p in route['points'])):
            _fail('route identity or centerline height')
        for a, b in zip(route['points'], route['points'][1:]):
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dy)
            if length < 1:
                _fail('physical route segment')
            for p in (a, b):
                for side in (-1, 1):
                    surface_height(value, p[0]-dy/length*side*route['width']/2)
        result[value['routeId']] = value
    return result


def width_seed(route, segment, alpha, lane, radius):
    a, b = route['points'][segment:segment+2]
    if (not _finite(alpha) or not 0 <= alpha <= 1 or not _finite(lane) or abs(lane) > 1
            or not _finite(radius) or radius < 42 or route['clearWidthCm'] <= 2*radius):
        _fail('walking sample parameters')
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    if length < 1:
        _fail('walking segment')
    offset = lane*(route['clearWidthCm']/2-radius)
    x, y = a[0]+dx*alpha-dy/length*offset, a[1]+dy*alpha+dx/length*offset
    z = surface_height(route['surfaceProfile'], x) if 'surfaceProfile' in route else a[2]+(b[2]-a[2])*alpha
    return [x, y, z]


def checked_surface_report(setup, routes):
    expected = [dict(id=r['id'], surfaceProfile=r['surfaceProfile']) for r in routes if 'surfaceProfile' in r]
    for row in expected:
        checked_profile(row['surfaceProfile'])
        if row['id'] not in (row['surfaceProfile']['routeId']+':forward', row['surfaceProfile']['routeId']+':reverse'):
            _fail('profile belongs to another proof route')
    if expected:
        if setup.get('surfaceSamplingMethod') != SURFACE_METHOD or not _same(setup.get('surfaceProfiles'), expected):
            _fail('native sampling method or exact profile witnesses')
    elif ('surfaceProfiles' in setup and setup['surfaceProfiles'] != []
            or 'surfaceSamplingMethod' in setup and setup['surfaceSamplingMethod'] != SURFACE_METHOD):
        _fail('native sampling method or exact profile witnesses')


def _orient(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _contains(triangle, point):
    scale = max(1, *(math.dist(a[:2], triangle[(i+1)%3][:2]) for i, a in enumerate(triangle)))
    return all(_orient(a, triangle[(i+1)%3], point) >= -1e-6*scale for i, a in enumerate(triangle))


def checked_surface_bindings(source, blueprint, meshes):
    profiles = checked_profiles(blueprint.get('routeSurfaceProfiles', ABSENT), blueprint.get('routes', []))
    bindings = source.get('surfaceBindings', [])
    if not isinstance(bindings, list) or len(bindings) != len(profiles):
        _fail('complete source surface bindings')
    used = set()
    for row in bindings:
        if (not isinstance(row, dict) or set(row) != {'routeId', 'profilePayload', 'profileSha256', 'meshId', 'sourceMeshSha256', 'topTriangleIndices'}
                or row.get('routeId') not in profiles or row['routeId'] in used or not isinstance(row.get('profilePayload'), str)
                or len(row['profilePayload'].encode('utf-8')) > 65_536
                or hashlib.sha256(row['profilePayload'].encode('utf-8')).hexdigest() != row.get('profileSha256')):
            _fail('source profile identity or raw payload SHA')
        used.add(row['routeId'])
        profile = profiles[row['routeId']]
        try:
            parsed = json.loads(row['profilePayload'])
        except (ValueError, TypeError):
            _fail('source profile payload JSON')
        checked_profile(parsed)
        asset = next((a for a in source['assets'] if a['id'] == row['meshId']), None)
        mesh = meshes.get(row['meshId'])
        if (parsed != profile or row['meshId'] != profile['meshId'] or not asset or row['sourceMeshSha256'] != asset['sha256']
                or not mesh or not isinstance(row.get('topTriangleIndices'), list) or not 1 <= len(row['topTriangleIndices']) <= 8192
                or any(type(i) is not int for i in row['topTriangleIndices']) or len(set(row['topTriangleIndices'])) != len(row['topTriangleIndices'])):
            _fail('actual floor mesh or source ordinals')
        triangles, identities = [], set()
        for index in row['topTriangleIndices']:
            if index < 0 or index >= len(mesh['indices'])//3:
                _fail('source triangle ordinal')
            points = [mesh['positions'][i] for i in mesh['indices'][index*3:index*3+3]]
            if len(points) != 3 or any(not _point(p) or abs(p[2]-surface_height(profile, p[0])) > .01 for p in points):
                _fail('authored triangle does not follow h(worldX)')
            a, b, c = points
            ab, ac = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
            normal = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]]
            minimum, maximum = min(p[0] for p in points), max(p[0] for p in points)
            if (normal[2] <= 0 or normal[2]/math.hypot(*normal) < .7
                    or any(minimum+.01 < k[0] < maximum-.01 for k in profile['knotsCm'][1:-1])):
                _fail('floor winding/slope or unpartitioned knot seam')
            identity = tuple(sorted(tuple(p) for p in points))
            if identity in identities:
                _fail('duplicate source floor face')
            identities.add(identity)
            triangles.append(points)
        route = next(r for r in blueprint['routes'] if r['id'] == row['routeId'])
        proof = dict(id=route['id'], points=route['points'], clearWidthCm=route['width'], surfaceProfile=profile)
        previous = {}

        def covered(p):
            if not any(_contains(t, p) for t in triangles):
                _fail('source floor omits a lane or turn sample')

        for segment, (a, b) in enumerate(zip(proof['points'], proof['points'][1:])):
            count = max(1, math.ceil(math.dist(a[:2], b[:2])/10))
            for sample in range(count+1):
                for lane in (-1, -.5, 0, .5, 1):
                    p = width_seed(proof, segment, sample/count, lane, 42)
                    before = previous.get(lane)
                    if before:
                        steps = max(1, math.ceil(math.dist(p[:2], before[:2])/10))
                        for i in range(1, steps):
                            x = before[0]+(p[0]-before[0])*i/steps
                            covered([x, before[1]+(p[1]-before[1])*i/steps, surface_height(profile, x)])
                    covered(p)
                    if abs(lane) == 1:
                        dx, dy = b[0]-a[0], b[1]-a[1]
                        length = math.hypot(dx, dy)
                        x = p[0]-dy/length*lane*42
                        covered([x, p[1]+dx/length*lane*42, surface_height(profile, x)])
                    previous[lane] = p
    return profiles
