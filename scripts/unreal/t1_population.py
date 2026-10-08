"""Admit retained first-pair population without changing gameplay identities."""
import copy
import math
from world_resources import resource_bindings

ZONES = ('sunmeadow_march', 'cinderfen_outskirts')
POSE_FIELDS = {'x', 'y', 'z', 'rotY'}


def rules(row):
    return {k: v for k, v in row.items() if k not in POSE_FIELDS}


def unique(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows): raise ValueError('Duplicate population identity: '+key)
    return result


def native_point(row):
    values = [row.get('z', 0)*100, row.get('x', 0)*100, row.get('y', 0)*100]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 300000 for v in values):
        raise ValueError('Population coordinates must be finite first-pair native positions')
    return values


def population_plan(candidate, canonical, survey, world_catalog, imports, registry, source_catalog):
    zone = candidate['id']
    if zone not in ZONES or canonical['id'] != zone or survey['zone'] != zone:
        raise ValueError('Population admits matching first-pair sources only')
    npcs, nodes = unique(canonical['npcs'], 'id'), unique(canonical['resourceNodes'], 'id')
    props = unique(canonical['props'], 'id')
    unique(candidate['npcs'], 'id'); unique(candidate['resourceNodes'], 'id')
    if not set(npcs).issubset({n['id'] for n in candidate['npcs']}) or {n['id'] for n in candidate['resourceNodes']} != set(nodes):
        raise ValueError('Candidate dropped retained population identities or changed resource inventory')
    profiles = unique(imports['entries'], 'profileKey')
    npc_actors = unique([a for a in survey['actors'] if a['kind'] == 'npc'], 'id')
    resource_actors = unique([a for a in survey['actors'] if a['kind'] == 'resource'], 'id')
    bindings = {(r['zone'], r['entity']): r for r in world_catalog['bindings'] if r['purpose'] == 'resource'}
    if len(bindings) != sum(r['purpose'] == 'resource' for r in world_catalog['bindings']):
        raise ValueError('Duplicate native resource catalog binding')
    ready, pending = [], []
    for row in candidate['npcs']:
        if row['id'] not in npcs:
            # Frozen authoring contains six staged camp additions absent from
            # the active content manifest. A source actor cannot admit them.
            pending.append(dict(kind='npc', id=row['id'], reason='canonical-content-identity-pending')); continue
        if rules(row) != rules(npcs[row['id']]): raise ValueError('Retained NPC rules changed: '+row['id'])
        actor, visual = npc_actors.get(row['id']), profiles.get(row['characterProfileKey'])
        if not actor or not visual:
            pending.append(dict(kind='npc', id=row['id'], reason='exact-native-profile-or-actor-pending')); continue
        identity = actor['identity']
        if (identity != dict(npc_id=row['id'], display_name=row['name'], city_role=row['role'], character_profile=row['characterProfileKey'])
            or actor['mesh'] != visual['skeletalMeshPath'] or actor['animation']['asset'] not in visual['animationPaths']
            or actor['collision'] != 'NoCollision' or not actor['animation']['looping'] or not actor['animation']['playing']):
            raise ValueError('Retained NPC body, animation or identity changed: '+row['id'])
        ready.append(dict(kind='npc', id=row['id'], source=copy.deepcopy(actor), definition=copy.deepcopy(row),
            canonical=copy.deepcopy(npcs[row['id']]), visual=copy.deepcopy(visual), point=native_point(row)))
    reviewed, missing = resource_bindings(candidate, registry, source_catalog)
    for row in candidate['resourceNodes']:
        if rules(row) != rules(nodes[row['id']]): raise ValueError('Retained resource rules changed: '+row['id'])
    for row in reviewed:
        node, prop = row['node'], row['prop']; actor = resource_actors.get(node['id']); binding = bindings.get((zone, node['id']))
        if rules(prop) != rules(props[prop['id']]): raise ValueError('Retained resource prop rules changed: '+node['id'])
        if not actor or not binding: raise ValueError('Reviewed resource lacks its exact saved native actor')
        if (actor['identity'] != dict(zone_id=zone, node_id=node['id'], visual_prop_id=prop['id'])
            or actor['mesh'] != binding['mesh'] or actor['materials'] != binding['materials']
            or actor['collision'] != binding['collision'] or binding['sourceModel'] != row['model']
            or binding['sourceSha256'] != row['sourceSha256'] or binding['visualProp'] != prop['id']):
            raise ValueError('Native herb binding differs from its exact source review')
        ready.append(dict(kind='resource', id=node['id'], source=copy.deepcopy(actor), definition=copy.deepcopy(node),
            prop=copy.deepcopy(prop), binding=copy.deepcopy(binding), model=row['model'], sourceSha256=row['sourceSha256'], point=native_point(node)))
    pending.extend(dict(kind='resource', id=row['id'], reason=row['reason']) for row in missing)
    pending.extend(dict(kind='crafting', id=row['id'], reason='complete-native-station-admission-and-behaviour-pending') for row in candidate.get('craftingStations', []))
    return dict(zone=zone, ready=ready, pending=pending, gameplayAccepted=False, visualApproved=False)


def inside_outline(point, outline):
    """Native XY against source XZ polygon; boundary is included, concavity retained."""
    x, y = point[:2]; polygon = [(p['z']*100, p['x']*100) for p in outline]
    if len(polygon) < 3 or any(not math.isfinite(n) for p in polygon+[tuple(point[:2])] for n in p):
        raise ValueError('Playable outline must be a finite polygon')
    inside = False
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        cross = (x-a[0])*(b[1]-a[1])-(y-a[1])*(b[0]-a[0])
        if abs(cross) <= 1e-6 and min(a[0], b[0]) <= x <= max(a[0], b[0]) and min(a[1], b[1]) <= y <= max(a[1], b[1]): return True
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]: inside = not inside
    return inside


def nearest_route_points(point, paths):
    """Sorted road projections allow native collision review to choose a connected approach."""
    results = []
    for route in paths:
        points = [native_point(p) for p in route['points']]
        for a, b in zip(points, points[1:]):
            d = [b[i]-a[i] for i in range(2)]; length = sum(v*v for v in d)
            if length <= 1e-6: continue
            t = max(0, min(1, sum((point[i]-a[i])*d[i] for i in range(2))/length))
            p = [a[i]+(b[i]-a[i])*t for i in range(3)]
            results.append(dict(road=route['id'], point=p, distanceCm=math.hypot(p[0]-point[0], p[1]-point[1])))
    if not results: raise ValueError('Population requires an existing route network')
    return sorted(results, key=lambda row: row['distanceCm'])
