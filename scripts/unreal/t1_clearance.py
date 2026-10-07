"""Bounded probe inventory for isolated T1 candidates, independent of Unreal."""
import math


def clearance_routes(source, village):
    if source['id'] != village['zoneId']:
        raise ValueError('Village and terrain identities differ')
    routes = [dict(id=p['id'], kind='road', points=p['points'], width=p['width'], vehicle=True)
              for p in source['paths']]
    routes += [dict(id=p['id'], kind='supply', points=p['points'], width=p['width'], vehicle=True)
               for p in source['orvrLayout']['caravanRoutes']]
    routes += [dict(id=p['id'], kind='planned_entry', points=p['approach'], vehicle=False)
               for p in village['modules']]
    points = [dict(id=p['id'], kind='service', point=p['point'])
              for p in village['serviceReservations']]
    points += [dict(id=p['id'], kind='portal_arrival', point=p['arrivalPoint'])
               for p in source['zoneTriggers']]
    points.append(dict(id=source['id']+'_village_spawn', kind='spawn', point=source['spawnPoint']))
    identities = [p['id'] for p in routes + points]
    if len(identities) != len(set(identities)):
        raise ValueError('Clearance probe identities must be unique')
    for route in routes:
        if len(route['points']) < 2:
            raise ValueError('Clearance route needs at least two vertices')
        for p in route['points']:
            finite_point(p)
        if any(math.hypot(b['x']-a['x'], b['z']-a['z']) < .001
               for a, b in zip(route['points'], route['points'][1:])):
            raise ValueError('Degenerate clearance segment')
    for p in points:
        finite_point(p['point'])
    return routes, points


def finite_point(p):
    if any(not isinstance(p.get(k), (int, float)) or not math.isfinite(p[k]) for k in ('x', 'z')):
        raise ValueError('Clearance positions must be finite')


def segment_samples(a, b, step=2):
    """Include endpoints and cap sweep length; reverse travel uses the same samples."""
    finite_point(a)
    finite_point(b)
    if not math.isfinite(step) or step <= 0:
        raise ValueError('Positive finite sampling step required')
    count = max(1, math.ceil(math.hypot(b['x']-a['x'], b['z']-a['z'])/step))
    if count > 10000:
        raise ValueError('Clearance segment exceeds bounded probe inventory')
    return [dict(x=a['x']+(b['x']-a['x'])*i/count, z=a['z']+(b['z']-a['z'])*i/count)
            for i in range(count+1)]
