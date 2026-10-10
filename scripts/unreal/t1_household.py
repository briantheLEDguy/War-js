"""Measured source-kit household layouts with a reserved straight doorway aisle."""
import copy
import math

BED_PARTS = ('SM_Bed_2', 'SM_Bed_Matress', 'SM_Bed_Pillow', 'SM_Bed_Sheet')
ROLES = ('field_workers', 'carter', 'stable_workers', 'orchard_workers', 'watchhouse')


def household_recipe(role, half_width_cm, half_depth_cm, catalog, floor_supported=None):
    """Local +Y faces the street. Native floor/collision/shelter proof remains separate."""
    if role not in ROLES:
        raise ValueError('Unknown household purpose')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in (half_width_cm, half_depth_cm)) or not 500 <= half_width_cm <= 800 or not 300 <= half_depth_cm <= 600:
        raise ValueError('Household requires a measured bounded room')
    if floor_supported is not None and not callable(floor_supported):
        raise ValueError('Native support sampler must be callable')
    placements = []

    def measured(asset):
        row = catalog.get(asset)
        if not isinstance(row, dict):
            raise ValueError('Required reviewed furniture is absent')
        origin, extent = row.get('origin'), row.get('extent')
        if any(not isinstance(v, list) or len(v) != 3 or any(isinstance(n, bool)
               or not isinstance(n, (int, float)) or not math.isfinite(n) for n in v)
               for v in (origin, extent)) or any(n <= 0 for n in extent):
            raise ValueError('Invalid measured furniture bounds')
        return origin, extent

    def add(asset, x, y, group, shared_base=None):
        origin, extent = measured(asset)
        base = -(origin[2]-extent[2]) if shared_base is None else shared_base
        bounds = [x+origin[0]-extent[0], x+origin[0]+extent[0],
                  y+origin[1]-extent[1], y+origin[1]+extent[1]]
        if bounds[0] < -half_width_cm or bounds[1] > half_width_cm or bounds[2] < -half_depth_cm or bounds[3] > half_depth_cm:
            raise ValueError('Furniture escapes the measured room')
        if bounds[0] < 75 and bounds[1] > -75:
            raise ValueError('Furniture enters the reserved 150cm doorway aisle')
        placements.append(dict(id=group+'_'+asset, asset=asset, group=group,
            localPositionCm=[x, y, base], localYawDegrees=0,
            footprintCm=bounds, collisionRequired=asset not in BED_PARTS[1:]))

    def bed(x, y, group):
        origin, extent = measured(BED_PARTS[0])
        # Keep all separately authored bed parts on their common source pivot.
        base = -(origin[2]-extent[2])
        for part in BED_PARTS: add(part, x, y, group, base)

    rear = -min(half_depth_cm-135, 240)
    if role == 'watchhouse':
        bed(-330, rear, 'rest_cot')
        add('SM_Table_Round', 300, 110, 'watch_desk')
        add('SM_Bench_2', -300, 170, 'patrol_bench')
    else:
        bed(-330, rear, 'west_bed'); bed(330, rear, 'east_bed')
        add('SM_Table_Round', -300, 170, 'household_table')
        add('SM_Bench_2', 300, 170, 'household_bench')
    add('SM_Crate_2', half_width_cm-230, 0, 'household_stores')
    if role in ('carter', 'orchard_workers', 'watchhouse'):
        add('SM_Crate_2', -half_width_cm+230, 0, 'working_stores')
    fitting_offsets = {}
    if floor_supported is not None:
        groups = list(dict.fromkeys(p['group'] for p in placements))
        offsets = sorted(((x, y) for x in range(-150, 151, 25) for y in range(-150, 151, 25)),
                         key=lambda p: (p[0]*p[0]+p[1]*p[1], abs(p[0]), -p[1], p[0]))
        fitted = []
        for group in groups:
            originals = [p for p in placements if p['group'] == group]
            # The long bench may turn to avoid retained source walls; beds keep authored axes.
            options = [(0, dx, dy) for dx, dy in offsets]
            if all(row['asset'] == 'SM_Bench_2' for row in originals):
                options.extend((90, dx, dy) for dx, dy in offsets)
            for yaw, dx, dy in options:
                candidate = copy.deepcopy(originals)
                for row in candidate:
                    px, py, _ = row['localPositionCm']
                    x0, x1, y0, y1 = row['footprintCm']
                    if yaw:
                        x0, x1, y0, y1 = px-(y1-py), px-(y0-py), py+(x0-px), py+(x1-px)
                    row['localPositionCm'][0] += dx; row['localPositionCm'][1] += dy
                    row['localYawDegrees'] = yaw
                    row['footprintCm'] = [x0+dx, x1+dx, y0+dy, y1+dy]
                clear = True
                for row in candidate:
                    x0, x1, y0, y1 = row['footprintCm']
                    if (x0 < -half_width_cm or x1 > half_width_cm or y0 < -half_depth_cm or y1 > half_depth_cm
                            or (x0 < 75 and x1 > -75)):
                        clear = False; break
                    for other in fitted:
                        ox0, ox1, oy0, oy1 = other['footprintCm']
                        if x0 < ox1+10 and ox0 < x1+10 and y0 < oy1+10 and oy0 < y1+10:
                            clear = False; break
                    if not clear or not floor_supported(copy.deepcopy(row)):
                        clear = False; break
                if clear:
                    fitted.extend(candidate); fitting_offsets[group] = [dx, dy]; break
            else:
                raise ValueError('No bounded supported household placement for '+group)
        placements = fitted
    for i, a in enumerate(placements):
        for b in placements[i+1:]:
            if a['group'] == b['group']: continue
            ax0, ax1, ay0, ay1 = a['footprintCm']; bx0, bx1, by0, by1 = b['footprintCm']
            if ax0 < bx1+10 and bx0 < ax1+10 and ay0 < by1+10 and by0 < ay1+10:
                raise ValueError('Separate household furnishings overlap or lack 10cm clearance')
    return dict(role=role, placements=copy.deepcopy(placements),
        doorwayAisleCm=150, commonBedPivotsPreserved=True,
        fittingOffsetsCm=fitting_offsets, nativeSupportSamplerUsed=floor_supported is not None,
        nativeFloorAndCollisionAccepted=False, appearanceApproved=False)
