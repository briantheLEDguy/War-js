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


def terrain_camera_sample(position, normal, expected_height, walking):
    """Camera footing must be walkable; a terrain focus may lie on a steep upward face."""
    if type(walking) is not bool or len(position)!=3 or len(normal)!=3 or any(not math.isfinite(v) for v in [*position,*normal,expected_height]):
        raise ValueError('Invalid terrain camera sample')
    if abs(position[2]-expected_height)>1 or abs(math.hypot(*normal)-1)>.02 or normal[2]<=0 or walking and normal[2]<.71:
        raise ValueError('Unsupported terrain camera footing or focus')
    return list(position)
