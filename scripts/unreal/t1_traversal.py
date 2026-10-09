"""Bounded live-walking fixtures derived from unchanged T1 candidate receipts."""
import math

ZONES = ('sunmeadow_march', 'cinderfen_outskirts')


def traversal_config(receipt, zone, source, headless):
    identity = zone['id']
    if identity not in ZONES or source['id'] != identity:
        raise ValueError('Only matching first-batch zones admit traversal')
    kind = receipt.get('kind', 'homes')
    if kind not in ('homes', 'materials', 'atmosphere'): raise ValueError('Unknown private traversal candidate kind')
    expected = '/Game/WorldRebuild/T1Redesign_'+kind.capitalize()+'_'+receipt['signature'][:12]+'_'
    if not zone['map'].startswith(expected) or not zone['map'].endswith('/'+identity+'/Review'):
        raise ValueError('Traversal requires the exact private candidate')
    routes = []
    for home in zone['homes']:
        count = len(home['route'])
        points = [dict(position=p, terrain=i < home['approachPoints'], indoor=home['approachPoints'] < i < count-1,
                       capture=i in (home['approachPoints'], home['approachPoints']+3, count-1))
                  for i, p in enumerate(home['route'])]
        routes.append(dict(id=home['id'], kind='home', points=points))
    if receipt.get('study') in ('retained-population', 'dramatic-relief', 'battlefield-landscape', 'battlefield-navigation'):
        for actor in zone['population']:
            if not actor['sourceRulesUnchanged'] or actor['gameplayAccepted'] is not False:
                raise ValueError('Population walking cannot admit changed rules or gameplay acceptance')
            # Stop about two metres from the actor, then walk back to the
            # connected road. NPC bodies retain their authored NoCollision;
            # the fixture must not walk through them for a close-up.
            approach = actor['approach'][:-4]
            if len(approach) < 2: raise ValueError('Population approach needs room for a player stand-off')
            ordered = approach+list(reversed(approach[:-1]))
            captures = {max(1,len(approach)//2),len(approach)-1,len(ordered)-1}
            points = [dict(position=p,terrain=True,indoor=False,capture=i in captures) for i,p in enumerate(ordered)]
            routes.append(dict(id=actor['id']+'_approach',kind='road',points=points))
    for route in zone.get('landscapeWalks',[]):
        if route.get('walkingAccepted') is not False or route.get('drivingAccepted') is not False or not route.get('terrainAndCapsuleChecked'):
            raise ValueError('Counter walks require their own native movement acceptance')
        for direction,ordered in [('forward',route['points']),('reverse',list(reversed(route['points'])))] if headless else [('forward',route['points'])]:
            points=[dict(position=p,terrain=True,indoor=False,capture=not headless and i in (len(ordered)//2,len(ordered)-1)) for i,p in enumerate(ordered)]
            routes.append(dict(id=route['id']+'_'+direction,kind='road',points=points))
    if headless:
        cross_country = [dict(id=c['id'],points=c['points']) for c in source['orvrLayout']['terrain']['clearCorridors']
                         if c['id'] not in {p['id'] for p in source['paths']}] if receipt.get('study') in ('battlefield-landscape','battlefield-navigation') else []
        for route in source['paths']+source['orvrLayout']['caravanRoutes']+cross_country:
            points = [dict(position=[p['z']*100, p['x']*100, p.get('y', 0)*100], terrain=True, indoor=False)
                      for p in route['points']]
            for direction, ordered in [('forward', points), ('reverse', list(reversed(points)))]:
                routes.append(dict(id=route['id']+'_'+direction, kind='road', points=ordered))
    ids = [r['id'] for r in routes]
    if len(ids) != len(set(ids)) or not 1 <= len(routes) <= 80:
        raise ValueError('Traversal route inventory must be unique and bounded')
    for route in routes:
        if not 2 <= len(route['points']) <= 2000:
            raise ValueError('Traversal requires bounded polylines')
        for point in route['points']:
            p = point['position']
            if len(p) != 3 or any(not isinstance(n, (int, float)) or not math.isfinite(n) or abs(n) > 300000 for n in p):
                raise ValueError('Traversal native coordinates must be finite and bounded')
    return dict(signature=receipt['signature'], zone=identity, map=zone['map'], capture=not headless,
                visual='/Game/MigrationProof/Visual_'+('civic_sunfire_templar_m' if identity == ZONES[0] else 'mire_warbrute_m'),
                routes=routes)


def validate_traversal(report, config):
    if not report.get('passed') or report.get('signature') != config['signature'] or report.get('map') != config['map']:
        raise ValueError('Live traversal failed or refers to another candidate: '+report.get('detail', 'missing report'))
    rows = report.get('routes', [])
    if len(rows) != len(config['routes']) or [r['id'] for r in rows] != [r['id'] for r in config['routes']]:
        raise ValueError('Live traversal did not cover the complete configured inventory')
    if not report.get('visibleCharacterReady') or report.get('developmentFlight') is not False:
        raise ValueError('Live traversal requires the visible normal character')
    for field, value in [('capsuleRadiusCm', 42), ('capsuleHalfHeightCm', 96), ('maxStepHeightCm', 45), ('maxWalkSpeedCm', 600)]:
        if report.get(field) != value:
            raise ValueError('Traversal changed native character geometry or speed')
    for row, route in zip(rows, config['routes']):
        if not row.get('completed') or row.get('reachedWaypoints') != len(route['points']) or row.get('inRouteTeleports') != 0 or row.get('jumps') != 0:
            raise ValueError('Route did not complete by normal walking')
        if not 0 <= row.get('longestAirborneSeconds', math.inf) <= .75 or not math.isfinite(row.get('distanceCm', math.inf)):
            raise ValueError('Route has invalid ground-support or movement evidence')
    for field in ('drivingAccepted', 'visualApproved', 'cameraAccepted', 'gameplayAccepted'):
        if report.get(field) is not False:
            raise ValueError('Traversal cannot grant another acceptance gate')
