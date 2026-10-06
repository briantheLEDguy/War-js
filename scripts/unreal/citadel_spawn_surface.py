"""Signed spawn footprints; native floor and capsule checks remain mandatory."""
import math


def gradient(row, recipe_version):
    value = row.get('groundGradient', [0, 0])
    if (recipe_version >= 6 and 'groundGradient' not in row or
            not isinstance(value, list) or len(value) != 2 or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in value) or
            math.hypot(*value) > 1 or row['index'] >= 2 and value != [0, 0]):
        raise ValueError('Spawn surface requires a finite walkable ground gradient; upper pads stay flat.')
    return value


def seed(point, x, y, edge, slope):
    dx, dy = x * edge / 2, y * edge / 2
    return [point[0] + dx, point[1] + dy, point[2] + slope[0] * dx + slope[1] * dy]


def validate_retained_surfaces(baseline, approaches):
    """Bind both lower footprints to the unchanged native scene, never an old map guess."""
    rows = baseline.get('spawnPadSurfaces', [])
    if len(rows) != 2 or {row.get('index') for row in rows} != {0, 1}:
        raise ValueError('Both retained spawn surfaces require a fresh native survey.')
    hashes = baseline['packageHashes']
    for row in rows:
        pad = next(p for p in approaches if p['index'] == row['index'])
        slope = gradient(pad, 6)
        samples = row.get('samples', [])
        if (row.get('schemaVersion') != 1 or row.get('point') != pad['points'][0] or
                row.get('widthCm') != pad['widthCm'] or row.get('groundGradient') != slope or
                row.get('capsuleRadiusCm') != 42 or row.get('capsuleHalfHeightCm') != 96 or
                row.get('diagnosticOnly') is not True or len(samples) != 25 or
                {(s.get('x'), s.get('y')) for s in samples} !=
                {(x, y) for x in range(-2, 3) for y in range(-2, 3)}):
            raise ValueError('Retained spawn surface differs from its exact measured footprint.')
        for sample in samples:
            source = sample.get('source', {})
            floor, normal = sample.get('floor'), sample.get('normal')
            expected = seed(row['point'], sample['x'], sample['y'], row['widthCm']/2-42, slope)
            if (source.get('meshPackage') not in hashes or
                    source.get('meshSha256') != hashes[source['meshPackage']] or
                    source.get('actorPackage') not in hashes or not source.get('actorPath') or
                    not source.get('componentPath') or not source.get('actorStateSha256') or
                    not isinstance(floor, list) or len(floor) != 3 or
                    not isinstance(normal, list) or len(normal) != 3 or
                    any(type(v) not in (int, float) or not math.isfinite(v) for v in floor + normal) or
                    normal[2] < math.sqrt(.5) or sample.get('capsuleClear') is not True or
                    math.dist(floor[:2], expected[:2]) > .01 or abs(floor[2]-expected[2]) > 25 or
                    any(abs(-normal[i]/normal[2]-slope[i]) > .001 for i in range(2))):
                raise ValueError('Retained native spawn survey lacks unchanged source, support or capsule clearance.')
