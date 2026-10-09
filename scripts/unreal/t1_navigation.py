"""Exact first-batch navigation maps and route inventories; physical driving stays unverified."""
import math
import re

ZONES=('sunmeadow_march','cinderfen_outskirts')


def navigation_map(signature,zone):
    if not re.fullmatch(r'[a-f0-9]{64}',signature) or zone not in ZONES:
        raise ValueError('Navigation requires an exact private first-batch revision')
    return '/Game/WorldRebuild/T1Redesign_Atmosphere_'+signature[:12]+'_Navigation/'+zone+'/Review'


def route_inventory(source,height_cm):
    identity=source['id']
    if identity not in ZONES:raise ValueError('Later-batch native environments remain gated')
    layout=source['orvrLayout'];routes=[];seen=set()
    candidates=[('road',r) for r in source['paths']]+[('supply',r) for r in layout['caravanRoutes']]
    road_ids={r['id'] for r in source['paths']}
    candidates += [('off-road',r) for r in layout['terrain']['clearCorridors']
        if r['id'] not in road_ids and '_ground_entry' not in r['id'] and '_scarp_' not in r['id'] and '_pocket_' not in r['id']]
    for kind,route in candidates:
        if route['id'] in seen or len(route['points'])<2:raise ValueError('Navigation routes must have distinct identities and at least two points')
        seen.add(route['id']);points=[]
        for point in route['points']:
            x,z=point['x'],point['z'];position=[z*100,x*100,height_cm(x,z)+20]
            if any(not math.isfinite(v) or abs(v)>2000000 for v in position):raise ValueError('Navigation route coordinate is unbounded')
            if not points or position!=points[-1]:points.append(position)
        if len(points)<2:raise ValueError('Degenerate navigation route')
        routes.append(dict(id=route['id'],kind=kind,points=points))
    if sum(r['kind']=='supply' for r in routes)!=6:raise ValueError('Retain all six physical supply itineraries')
    return routes


def validate_probe(probe,route,convoy):
    profile='SiegeConvoy' if convoy else 'Default'
    if probe.get('passed') is not True or probe.get('profile')!=profile or probe.get('physicalDrivingVerified') is not False:
        raise ValueError('Native navigation probe failed or claimed physical driving')
    rows=probe.get('points',[])
    if len(rows)!=len(route['points']) or type(probe.get('queryBudget')) is not int or not 1<=probe['queryBudget']<=100000:
        raise ValueError('Incomplete native route/query inventory')
    for i,row in enumerate(rows):
        if type(row.get('index')) is not int or row['index']!=i or any(row.get(k) is not True for k in ('projected','connected','withinOutline')) or row.get('searchLimit') is not False:
            raise ValueError('Unprojected, disconnected, out-of-outline or exhausted route')
        length=row.get('lengthCm')
        if isinstance(length,bool) or not isinstance(length,(int,float)) or not math.isfinite(length) or length<0:
            raise ValueError('Invalid native path length')
    return True


def navigation_payload(description):
    """Compare saved tiles across routing copies without comparing package identity."""
    rows=description.get('actors',[])
    if len(rows)!=2 or {r.get('profile') for r in rows}!={'Default','SiegeConvoy'}:
        raise ValueError('Both exact native profiles are required')
    result=[]
    for row in rows:
        if row.get('registered') is not True or row.get('needsRebuild') is not False or row.get('needsRebuildOnLoad') is not False:
            raise ValueError('Copied native navigation is missing, dirty or scheduled for rebuild')
        if type(row.get('activeTiles')) is not int or not 0<row['activeTiles']<=16384 or row.get('tileCapacity')!=16384 or not row.get('tileSnapshot'):
            raise ValueError('Copied native tile inventory is empty or unbounded')
        result.append({k:v for k,v in row.items() if k not in ('actor','package')})
    return sorted(result,key=lambda r:r['profile'])


def validate_navigation_parent(parent,scene_signature):
    if parent.get('study')!='battlefield-navigation' or parent.get('navigationVerified') is not True or parent.get('diagnostic') is not False or parent.get('failures')!=[] or parent.get('parentSignature')!=scene_signature:
        raise ValueError('Safe staging needs admitted navigation from its exact landscape parent')
    if len(parent.get('zones',[]))!=2 or {r.get('id') for r in parent['zones']}!=set(ZONES):
        raise ValueError('Safe staging must retain both first-batch zones')
    for zone in parent['zones']:
        if zone.get('map')!=navigation_map(parent['signature'],zone['id']) or zone.get('navigation',{}).get('saveReloadVerified') is not True or zone['navigation'].get('failures')!=[]:
            raise ValueError('Each staged region needs its exact saved and reloaded navigation')
        navigation_payload(zone['navigation']['reloaded'])
    return True
