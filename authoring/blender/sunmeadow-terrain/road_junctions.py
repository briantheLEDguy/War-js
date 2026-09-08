"""Explicit rounded road transition tessellation; survey routes remain untouched."""
import math


def connected_junctions(paths):
    candidates = {}
    for path in paths:
        for point in [path['points'][0], path['points'][-1]]:
            candidates[(round(point['x'], 5), round(point['z'], 5))] = point
    result = []
    for x, z in candidates:
        touching = []
        alignments = set()
        for index, path in enumerate(paths):
            for a, b in zip(path['points'], path['points'][1:]):
                dx, dz = b['x']-a['x'], b['z']-a['z']
                length2 = dx*dx+dz*dz
                if length2 < 1e-12:
                    continue
                t = max(0, min(1, ((x-a['x'])*dx+(z-a['z'])*dz)/length2))
                if math.hypot(x-a['x']-t*dx, z-a['z']-t*dz) <= .001:
                    touching.append(index)
                    points = tuple((p['x'], p['z']) for p in path['points'])
                    alignments.add(min(points, points[::-1]))
                    break
        if len(alignments) >= 2:
            half = max(paths[index]['width']/2 for index in touching)
            result.append({'x': x, 'z': z, 'half_width': half, 'paths': touching,
                           'inner_radius': half-min(.35, half*.25), 'outer_radius': half+min(.6, half*.5)})
    return result


def transition_polygons(junction):
    """Return indexed-order world X/Z/alpha patches with <=2m radial bands."""
    inner, outer = junction['inner_radius'], junction['outer_radius']
    segments = max(12, math.ceil(2*math.pi*outer))
    bands = max(1, math.ceil(inner/2))
    radii = [inner*index/bands for index in range(1, bands+1)] + [outer]
    previous = None
    for band, radius in enumerate(radii):
        alpha = 0 if band == len(radii)-1 else 1
        ring = [(junction['x']+radius*math.cos(2*math.pi*i/segments),
                 junction['z']+radius*math.sin(2*math.pi*i/segments), alpha) for i in range(segments)]
        for index in range(segments):
            nxt = (index+1)%segments
            if previous is None:
                yield [(junction['x'], junction['z'], 1), ring[index], ring[nxt]]
            else:
                yield [previous[index], ring[index], ring[nxt], previous[nxt]]
        previous = ring
