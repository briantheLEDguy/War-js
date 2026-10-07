"""Validate additional reviewed furnishings against the retained citadel.

This layer adds individually editable props; it never rebuilds the accepted
shell or changes encounter topology. Native collision and appearance still
require checks in the resulting private world.
"""
import math
import re

from aegis_citadel_furnishing_density import (
    ArchitectureClearance, MARGIN_CM, aabb_gap, overlaps, route_witness,
)
from aegis_citadel_furnishings import DRESSING_GROUPS, source_furnishing


def checked_requests(requests):
    if not isinstance(requests, list) or not 1 <= len(requests) <= 128:
        raise ValueError('A bounded nonempty decor ledger is required')
    identities = set()
    for row in requests:
        if not isinstance(row, dict) or set(row) != {
                'id', 'group', 'source', 'point', 'scale', 'yawDegrees', 'centerPlan'}:
            raise ValueError('Exact floor-mounted decor request fields required')
        identity = row['id']
        if not isinstance(identity, str) or not re.fullmatch('decor_[a-z0-9_]{1,90}', identity):
            raise ValueError('Invalid decor identity')
        if identity in identities:
            raise ValueError('Duplicate decor identity: ' + identity)
        identities.add(identity)
        if row['group'] not in (*DRESSING_GROUPS, 'courtyard'):
            raise ValueError('Unknown decor area: ' + identity)
        if (not isinstance(row['source'], str) or
                not re.fullmatch('public/assets/models/prop_aegis_[a-z0-9_]+[.]glb', row['source'])):
            raise ValueError('A reviewed Aegis furnishing source is required')
        values = row['point']
        if (not isinstance(values, list) or len(values) != 3 or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
            raise ValueError('Finite decor position required')
        if (type(row['scale']) not in (int, float) or not math.isfinite(row['scale']) or
                not .4 <= row['scale'] <= 1.4 or type(row['yawDegrees']) not in (int, float) or
                not math.isfinite(row['yawDegrees']) or row['centerPlan'] is not True):
            raise ValueError('Bounded decor scale and authored yaw required')
    return requests


def checked_decor(blueprint, architecture, existing, requests, residents):
    """Use actual transformed source bounds and all retained play reservations."""
    checked_requests(requests)
    occupied = list(existing)
    old_ids = [row['id'] for row in occupied]
    if len(old_ids) != len(set(old_ids)) or set(old_ids) & {r['id'] for r in requests}:
        raise ValueError('Decor identity aliases an existing object')
    prepared = [source_furnishing(row) for row in requests]
    checker = ArchitectureClearance(architecture, [receipt['boundsCm'] for _, receipt in prepared])
    output, ledger = [], []
    for request, (mesh, receipt) in zip(requests, prepared):
        identity, bounds = request['id'], receipt['boundsCm']
        room = next((r for r in blueprint['rooms'] if r['id'] == request['group']), None)
        if room and not all(room['bounds'][0][i] <= bounds[0][i] and
                            bounds[1][i] <= room['bounds'][1][i] for i in range(3)):
            raise ValueError('Decor leaves signed room: ' + identity)
        route = route_witness(blueprint, bounds)
        center = [(bounds[0][i] + bounds[1][i]) / 2 for i in range(2)] + [bounds[0][2]]
        radius = route['circumscribedRadiusCm']
        for row in occupied:
            if overlaps(bounds, row['boundsCm'], MARGIN_CM):
                raise ValueError('Decor overlap: ' + identity + ' / ' + row['id'])
        for objective in blueprint['objectives'] + blueprint['optionalObjectives']:
            p = objective['point'] if isinstance(objective, dict) else objective
            if abs(p[2] - center[2]) < 210 and math.dist(p[:2], center[:2]) < 650 + radius:
                raise ValueError('Objective reservation: ' + identity)
        for pad in blueprint.get('gameplayPads', []):
            if pad.get('preserveTransform'):
                continue
            p = pad['footprintCentreFloorCm']
            if (bounds[0][2] < p[2] + pad['maximumHeightCm'] and bounds[1][2] > p[2] and
                    math.dist(p[:2], center[:2]) < pad['maximumFootprintRadiusCm'] + radius + MARGIN_CM):
                raise ValueError('Gameplay/service reservation: ' + identity + ' / ' + pad['id'])
        for gate in blueprint.get('gates', []):
            for leaf in gate['leaves']:
                x, y, z = leaf['point']
                width, height = leaf['width'], leaf['height']
                if overlaps(bounds, [[x - 255, y - width / 2, z],
                                     [x + 255, y + width / 2, z + height]], MARGIN_CM):
                    raise ValueError('Gate reservation: ' + identity)
        for resident in residents:
            x, y, z = resident['pointCm']
            r, h = resident['clearanceRadiusCm'], resident['heightCm']
            if overlaps(bounds, [[x - r, y - r, z], [x + r, y + r, z + h]], MARGIN_CM):
                raise ValueError('Resident reservation: ' + identity + ' / ' + resident['id'])
        geometry = checker.check(identity, bounds)
        neighbor = min((dict(id=r['id'], gapCm=aabb_gap(bounds, r['boundsCm'])) for r in occupied),
                       key=lambda r: r['gapCm'], default=None)
        occupied.append(dict(id=identity, boundsCm=bounds))
        output.append(mesh)
        ledger.append({**request, **receipt, 'routeClearance': route,
                       'architectureClearance': geometry, 'closestPriorFurnishing': neighbor,
                       'furnishingMarginCm': MARGIN_CM, 'individuallyEditable': True,
                       'nativeClearanceVerified': False, 'visualApproved': False})
    return output, ledger, checker.inventory
