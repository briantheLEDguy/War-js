"""Bounded appearance changes for the privately reviewed citadel decor.

Fixture geometry, collision and gameplay reservations remain immutable. A fresh
native copy and rendered comparison are required before adopting these settings.
"""
import math

ROOMS = ('forehall', 'throne_hall', 'west_archive', 'east_treasury')
PAINT_ROLES = ('furniture_857c0c1bcc3d', 'furniture_cfa70d090237')
PAINT = dict(tint=[.015, .032, .078], roughness=.48, metallic=.12)


def mounted_light_plan(ledger):
    """Move lantern emitters clear of opaque housings, retaining their parents."""
    mounts = [row for row in ledger if row.get('mountKind')]
    if len(mounts) != 16 or len({row['id'] for row in mounts}) != 16:
        raise ValueError('Sixteen distinct reviewed mounts required')
    counts = {(room, kind): 0 for room in ROOMS
              for kind in ('ceiling_chandelier', 'wall_lantern')}
    output = []
    for row in mounts:
        key = (row['group'], row['mountKind'])
        if key not in counts:
            raise ValueError('Unexpected interior mount')
        counts[key] += 1
        point, bounds, yaw = row['point'], row['boundsCm'], row['yawDegrees']
        if (len(point) != 3 or len(bounds) != 2 or any(len(p) != 3 for p in bounds)
                or any(type(v) not in (int, float) or not math.isfinite(v)
                       for v in [*point, *bounds[0], *bounds[1], yaw])
                or any(bounds[0][i] > bounds[1][i] for i in range(3))):
            raise ValueError('Finite ordered mount geometry required')
        quiet_room = row['group'] in ('west_archive', 'east_treasury')
        if row['mountKind'] == 'ceiling_chandelier':
            position = [point[0], point[1], bounds[0][2] - 20]
            intensity = 180000 if quiet_room else 120000 if row['group'] == 'throne_hall' else 96000
            radius, source_radius = (5200 if quiet_room else 4500), 15
        else:
            heading = math.radians(yaw)
            position = [point[0] + 70 * math.cos(heading),
                        point[1] + 70 * math.sin(heading),
                        (bounds[0][2] + bounds[1][2]) / 2]
            intensity, radius, source_radius = (7200 if quiet_room else 6000), (2200 if quiet_room else 1800), 8
        gap = math.sqrt(sum(max(bounds[0][i] - position[i], 0,
                                position[i] - bounds[1][i]) ** 2 for i in range(3)))
        if gap <= source_radius + 1:
            raise ValueError('Emitter overlaps its fixture')
        output.append(dict(id=row['id'], group=row['group'], kind=row['mountKind'],
                           positionCm=position, intensityLumens=intensity,
                           attenuationRadiusCm=radius, sourceRadiusCm=source_radius,
                           temperatureKelvin=2700, castShadows=True,
                           emitterToHousingBoundsGapCm=gap))
    if set(counts.values()) != {2}:
        raise ValueError('Two lights of each kind required per room')
    return output


def checked_paint(role, spec):
    """Restrict the adaptation to the two known turquoise paint materials."""
    if role not in PAINT_ROLES or set(spec) != {'tint', 'roughness', 'metallic', 'twoSided'}:
        raise ValueError('Only the reviewed plain paint roles may be adapted')
    expected = ([.025, .19, .18] if role == PAINT_ROLES[0] else [.025, .18, .17])
    roughness, metallic = (.24, .28) if role == PAINT_ROLES[0] else (.36, .35)
    if (not isinstance(spec['tint'], list) or len(spec['tint']) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   for v in [*spec['tint'], spec['roughness'], spec['metallic']])
            or any(abs(v - e) > 1e-6 for v, e in zip(spec['tint'], expected))
            or abs(spec['roughness'] - roughness) > 1e-6
            or abs(spec['metallic'] - metallic) > 1e-6
            or spec['twoSided'] is not True):
        raise ValueError('Reviewed source paint identity changed')
    return {**spec, **PAINT, 'tint': list(PAINT['tint'])}
