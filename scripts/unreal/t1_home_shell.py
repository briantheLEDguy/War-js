"""Bounded roof-pivot repairs for frozen, single-storey private home recipes."""
import copy
import math


def refit_shell(template, bounds):
    if template.get('kind') != 'home' or not template.get('interior') or template.get('upperFloor'):
        raise ValueError('Shell studies require single-storey furnished homes')
    result = copy.deepcopy(template)
    roofs = []
    for index, part in enumerate(result['components']):
        path = part['mesh']
        if not path.startswith(('/Game/Medieval_Environment/', '/Game/Medieval_Mod_Town/')) or '..' in path:
            raise ValueError('Shell parts must use the frozen private kit inventory')
        source = bounds[path]
        values = [*source['origin'], *source['extent'], *part['anchor'], *part['scale'], part['yaw']]
        if any(not math.isfinite(v) for v in values) or min(source['extent']) <= 0 or min(part['scale']) <= 0:
            raise ValueError('Shell bounds and transforms must be finite and positive')
        name = path.rsplit('.', 1)[-1]
        if name not in ('SM_MH_02_Slate_Roof_01', 'SM_MH_02_Slate_Porch_Roof_01'):
            continue
        if name == 'SM_MH_02_Slate_Roof_01' and abs(part['anchor'][2]-wall_top(template,bounds)) > .5:
            raise ValueError('Roof is already refitted or does not use the measured wall datum')
        # The kit's Z=0 is its eave datum. Normalizing the decorative skirt's
        # negative bounds to the wall top lifts the entire roof off that wall.
        offset = (source['origin'][2]-source['extent'][2])*part['scale'][2]
        if not -30 <= offset < -1:
            raise ValueError('Unexpected roof skirt; re-survey instead of guessing a repair')
        part['anchor'][2] += offset
        roofs.append(dict(component=index, mesh=path, deltaZ=offset, eaveDatum=part['anchor'][2]-offset))
    main = [r for r in roofs if r['mesh'].endswith('.SM_MH_02_Slate_Roof_01')]
    if not main or max(r['deltaZ'] for r in main)-min(r['deltaZ'] for r in main) > .001:
        raise ValueError('Main roof must have one consistent attachment datum')
    # Keep the original chimney seated on the same roof after its correction.
    for part in result['components']:
        if part['mesh'].endswith('.SM_Chimney_2'):
            part['anchor'][2] += main[0]['deltaZ']
    return dict(template=result, corrections=roofs, mainDeltaZ=main[0]['deltaZ'],
                visualApproved=False, licensedDistributionApproved=False)


def part_transform(part, bounds, grouped_bounds=None):
    """Resolve shared bed pivots as a group; all other parts use their own bounds."""
    sources = grouped_bounds or [bounds[part['mesh']]]
    low = [min(b['origin'][i]-b['extent'][i] for b in sources) for i in range(3)]
    high = [max(b['origin'][i]+b['extent'][i] for b in sources) for i in range(3)]
    origin = [(a+b)/2 for a, b in zip(low, high)]
    scale = part['scale']; angle = math.radians(part['yaw'])
    x, y = origin[0]*scale[0], origin[1]*scale[1]
    return [part['anchor'][0]-x*math.cos(angle)+y*math.sin(angle),
            part['anchor'][1]-x*math.sin(angle)-y*math.cos(angle), part['anchor'][2]-low[2]*scale[2]]


def wall_top(template,bounds):
    return max(p['anchor'][2]+2*bounds[p['mesh']]['extent'][2]*p['scale'][2]
               for p in template['components'] if p['mesh'].endswith(('.SM_MH_02_Stone_Wall_01',
                   '.SM_MH_02_Stone_Wall_Window_01', '.SM_MH_02_Stone_Wall_Door_01')))


def seam_probes(template, bounds):
    """Horizontal rays immediately above the wall tops catch open eave strips."""
    width, depth = template['roomSize']; top = wall_top(template,bounds)
    probes = []
    for side in (-1, 1):
        for bay in range(round(width/300)):
            x = (bay+.5)*300-width/2
            for height in (top+2, top+5, top+10):
                probes.append(dict(start=[x, 0, height], end=[x, side*(depth/2+150), height],
                                   side=side, bay=bay, height=height))
    return probes
