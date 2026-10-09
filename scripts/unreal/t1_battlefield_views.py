"""Read-only review cameras on retained vehicle routes, aimed into landscape neighborhoods."""
import math


def neighborhood_views(paths, cells):
    segments = [(a, b) for path in paths[:3] for a, b in zip(path['points'], path['points'][1:])]
    if not segments or any(not all(math.isfinite(p[k]) for p in (a, b) for k in ('x', 'z'))
        or a['x'] == b['x'] and a['z'] == b['z'] for a, b in segments):
        raise ValueError('Neighborhood cameras require finite connected routes')
    result = []
    for cell in cells:
        placements = cell['placements']
        if not placements:
            continue
        if any(not all(math.isfinite(p[k]) for k in ('x', 'z')) for p in placements):
            raise ValueError('Invalid landscape review target')
        target = {k: sum(p[k] for p in placements)/len(placements) for k in ('x', 'z')}
        options = []
        for a, b in segments:
            dx, dz = b['x']-a['x'], b['z']-a['z']
            t = min(1, max(0, ((target['x']-a['x'])*dx+(target['z']-a['z'])*dz)/(dx*dx+dz*dz)))
            eye = dict(x=a['x']+t*dx, z=a['z']+t*dz)
            options.append((math.hypot(eye['x']-target['x'], eye['z']-target['z']), eye))
        distance, eye = min(options, key=lambda row: row[0])
        if distance < 1:
            continue
        result.append(('landscape_'+cell['id'].split('_cell_')[-1], eye, target))
    return result
