"""Deterministic irregular woodland clusters with open lanes, pads and small clearings."""
import math, random
from t1_landscape_ecology import inside, segment_distance

GROUPS = (('western_wood', -565, 150, 115, 110, .75), ('barrow_wood', -415, 305, 95, 65, .25))


def woodland_layout(source, height, occupied, crown_ratio, limit=190):
    if source.get('id') != 'sunmeadow_march' or not isinstance(limit, int) or isinstance(limit, bool) or not 0 <= limit <= 220:
        raise ValueError('Woodland clusters require the bounded Sunmeadow prototype')
    if not math.isfinite(crown_ratio) or not .1 <= crown_ratio <= 1:
        raise ValueError('Invalid woodland crown-to-height ratio')
    occupied = [dict(p) for p in occupied]
    if any(any(not math.isfinite(p[k]) for k in ('x', 'z', 'radius')) or not .25 <= p['radius'] <= 100 for p in occupied):
        raise ValueError('Invalid woodland obstacle reserves')
    routes = [*source['paths'], *source['orvrLayout']['caravanRoutes']]
    routes += [dict(points=c['points'], width=c['radius']*2) for c in source['orvrLayout']['terrain']['clearCorridors']]
    pads = source['orvrLayout']['terrain']['flattenAreas']
    rng = random.Random(713910); result = []
    for group, cx, cz, rx, rz, share in GROUPS:
        target = round(limit*share); count = 0
        for _ in range(target*200):
            if count >= target: break
            x = cx+rng.uniform(-rx, rx); z = cz+rng.uniform(-rz, rz)
            if math.hypot((x-cx)/rx, (z-cz)/rz) > 1+.08*math.sin(x/19+math.cos(z/23)) or not inside(dict(x=x, z=z), source['spatial']['playableOutline']): continue
            if math.hypot(x-(cx+30), z-(cz-20)) < 18 or math.hypot(x+510, z-90) < 7: continue
            if any(math.hypot(x-a['x'], z-a['z']) < a['radius']+18 for a in pads): continue
            tree_height = 13+9*rng.random(); crown = tree_height*crown_ratio
            if any(segment_distance(dict(x=x, z=z), a, b) < route['width']/2+crown+3 for route in routes for a, b in zip(route['points'], route['points'][1:])): continue
            if any(math.hypot(x-p['x'], z-p['z']) < p['radius'] for p in occupied): continue
            floor = height(x, z); samples = [height(x+dx, z+dz) for dx, dz in [(1, 0), (-1, 0), (0, 1), (0, -1)]]
            if not all(math.isfinite(h) for h in [floor, *samples]): raise ValueError('Woodland grounding must be finite')
            if max(abs(h-floor) for h in samples) > .65: continue
            result.append(dict(id='sunmeadow_march_'+group+'_'+str(count), group=group, x=x, z=z, groundMetres=floor, heightMetres=tree_height, yawDegrees=rng.uniform(-180, 180)))
            occupied.append(dict(x=x, z=z, radius=8)); count += 1
    # Never silently exceed the admitted global canopy budget through rounded group shares.
    return result[:limit]
