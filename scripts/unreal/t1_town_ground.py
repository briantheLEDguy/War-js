"""Continuous local landforms and rigid assembly placement, independent of Unreal."""
import copy
import math


def smooth(value):
    t = max(0.0, min(1.0, value))
    return t*t*(3-2*t)


def valley_height(x, z, base):
    def raw(a, b):
        valley = 18*math.sin((b+15)/70)
        return (.022*b + .035*(math.hypot(a-valley, 18)-18)
                + 4.5*math.exp(-((a+105)/70)**2-((b-12)/100)**2)
                + 5.5*math.exp(-((a-110)/80)**2-((b-90)/95)**2)
                - 1.2*math.exp(-((a-50)/40)**2-((b+95)/55)**2))
    y = base+raw(x, z)-raw(0, 0)
    court = 1-smooth((math.hypot(x-55, z+40)-27)/25)
    return y*(1-court)+base*court


def patch_height(x, z, old_height, base):
    """The outer 70m merges smoothly into the retained regional surface."""
    weight = 1-smooth((max(abs(x)/195, abs(z-5)/195)-1)*195/70)
    return old_height*(1-weight)+valley_height(x, z, base)*weight


def fitted_height(x, z, height, lots):
    # Pads have separate elevations; never average overlapping level foundations.
    matches = []
    for lot in lots:
        dx, dz = x-lot['x'], z-lot['z']; a = lot['rotY']
        u, v = dx*math.cos(a)-dz*math.sin(a), dx*math.sin(a)+dz*math.cos(a)
        distance = max(abs(u)-lot['halfWidth'], abs(v)-lot['halfDepth'], 0)
        weight = 1-smooth(distance/lot.get('feather', 6))
        if weight: matches.append((weight, lot['height']))
    if not matches: return height
    # Disjoint cores are an authoring invariant; strongest influence avoids summing pads.
    weight, level = max(matches)
    return height*(1-weight)+level*weight


def frame_point(point, old_origin, new_origin, yaw_degrees):
    if any(not math.isfinite(v) for v in [*point, *old_origin, *new_origin, yaw_degrees]):
        raise ValueError('Nonfinite assembly frame')
    a = math.radians(yaw_degrees); c, s = math.cos(a), math.sin(a)
    x, y = point[0]-old_origin[0], point[1]-old_origin[1]
    return [new_origin[0]+c*x-s*y, new_origin[1]+s*x+c*y,
            new_origin[2]+point[2]-old_origin[2]]


def reframe_inventory(states, frames):
    """Move complete actor namespaces, retaining local offsets, scale and bindings."""
    if any(a != b and b.startswith(a+'_') for a in frames for b in frames):
        raise ValueError('Ambiguous assembly namespace')
    result = copy.deepcopy(states); counts = {key: 0 for key in frames}
    for label, state in result.items():
        matches = [key for key in frames if label == key or label.startswith(key+'_')]
        if len(matches) > 1: raise ValueError('Ambiguous assembly namespace')
        if not matches: continue
        key = matches[0]; frame = frames[key]; counts[key] += 1
        state['location'] = frame_point(state['location'], frame['old'], frame['new'], frame['yaw'])
        state['rotation'][1] += frame['yaw']
    if any(count == 0 for count in counts.values()): raise ValueError('Missing complete assembly')
    return result, counts


def ground_normals(positions, indices):
    normals = [[0.0, 0.0, 0.0] for _ in positions]
    for i in range(0, len(indices), 3):
        ids = indices[i:i+3]; a, b, c = [positions[j] for j in ids]
        u, v = [b[k]-a[k] for k in range(3)], [c[k]-a[k] for k in range(3)]
        n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        if n[2] < 0: n = [-value for value in n]
        for j in ids:
            for k in range(3): normals[j][k] += n[k]
    return [[v/max(math.sqrt(sum(n*n for n in row)), 1e-12) for v in row] for row in normals]
