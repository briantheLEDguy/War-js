"""Plan vertical terrain changes without breaking complete native building/keep assemblies."""
import copy
import math


def _number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def grounded_inventory(states, old_surface, next_surface, assembly_deltas_cm, fixed_labels=()):
    """Source X/Z maps to native Y/X; footing, movement and authority need separate native proof."""
    fixed = set(fixed_labels)
    if not fixed <= states.keys():
        raise ValueError('Fixed actor is absent from the exact candidate inventory')
    groups = dict(assembly_deltas_cm)
    for prefix, delta in groups.items():
        if not isinstance(prefix, str) or not prefix or not any(
                label == prefix or label.startswith(prefix + '_') for label in states):
            raise ValueError('Assembly namespace is absent from the exact candidate inventory')
        if not _number(delta) or abs(delta) > 25000:
            raise ValueError('Unbounded assembly translation')
    plan = {}
    for label, state in states.items():
        p = state.get('location')
        if not isinstance(p, list) or len(p) != 3 or not all(_number(v) for v in p):
            raise ValueError('Invalid native actor location')
        matches = [prefix for prefix in groups if label == prefix or label.startswith(prefix + '_')]
        if len(matches) > 1 or (matches and label in fixed):
            raise ValueError('Ambiguous or fixed native assembly member')
        delta = 0 if label in fixed else groups[matches[0]] if matches else (
            next_surface.height_cm(p[1]/100, p[0]/100) - old_surface.height_cm(p[1]/100, p[0]/100))
        if not _number(delta) or abs(delta) > 25000:
            raise ValueError('Unbounded grounded translation')
        plan[label] = delta
    result = copy.deepcopy(states)
    for label, delta in plan.items():
        result[label]['location'][2] += delta
    return result, dict(completeAssemblyDeltasCm=groups, actorDeltasCm=plan,
        verticallyShiftedActors=sum(abs(v) > .001 for v in plan.values()),
        xyAndBindingsPreserved=True, terrainFootingAccepted=False, authorityIntegrated=False)


def conform_ground_overlay(data, old_surface, next_surface):
    """Retain native corner topology, UVs and alpha while updating cosmetic ground support."""
    positions, normals, indices = (data.get(k) for k in ('positions', 'normals', 'indices'))
    if (not isinstance(positions, list) or not positions or not isinstance(normals, list)
            or len(normals) != len(positions) or not isinstance(indices, list) or not indices or len(indices) % 3
            or any(not isinstance(p, list) or len(p) != 3 or not all(_number(v) for v in p)
                   for p in positions + normals)
            or any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(positions) for i in indices)
            or len(indices) != len(positions) or len(set(indices)) != len(indices)):
        raise ValueError('Invalid committed overlay corners')
    result = copy.deepcopy(data); maximum = 0; inherited_degenerate = 0
    # Expanded corners may reference the same authoring list. Each corner must move once.
    result['positions'] = [p[:] for p in positions]
    for p in result['positions']:
        delta = next_surface.height_cm(p[1]/100, p[0]/100) - old_surface.height_cm(p[1]/100, p[0]/100)
        if not _number(delta) or abs(delta) > 25000:
            raise ValueError('Unbounded overlay translation')
        p[2] += delta; maximum = max(maximum, abs(delta))

    def cross(points):
        a, b, c = points; u = [b[k]-a[k] for k in range(3)]; v = [c[k]-a[k] for k in range(3)]
        return [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]

    for i in range(0, len(indices), 3):
        ids = indices[i:i+3]; n = cross([result['positions'][j] for j in ids]); length = math.sqrt(sum(v*v for v in n))
        if length < 1e-8:
            old = cross([positions[j] for j in ids])
            if math.sqrt(sum(v*v for v in old)) >= 1e-8:
                raise ValueError('Ground change collapsed a previously valid overlay triangle')
            # Native float corners can already contain coincident zero-alpha edge vertices.
            inherited_degenerate += 1
            continue
        orientation = sum(n[k]*normals[ids[0]][k] for k in range(3))
        if abs(orientation) < 1e-8:
            raise ValueError('Overlay normal has ambiguous orientation')
        sign = 1 if orientation > 0 else -1
        for j in ids: result['normals'][j] = [sign*v/length for v in n]
    return result, dict(maximumCornerDeltaCm=maximum, inheritedDegenerateTriangles=inherited_degenerate,
        topologyUvsAndAlphaPreserved=True, requiresDegenerateSourceReconciliation=inherited_degenerate > 0, collisionAccepted=False)
