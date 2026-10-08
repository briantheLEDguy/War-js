"""Measured timber ceiling bays for the frozen single-storey home assemblies."""
import math
from t1_home_shell import wall_top

TIMBER = '/Game/Medieval_Environment/Medieval_Houses_Vol2/Meshes/SM_MH_02_Wood_Floor_01.SM_MH_02_Wood_Floor_01'
TINTS = {'sunmeadow_march': [1.12, 1.04, .90], 'cinderfen_outskirts': [.72, .68, .62]}


def ceiling_recipe(template, bounds, timber_bounds, zone):
    """Turn the reviewed plank surface downward; seat its whole depth below the eave."""
    if zone not in TINTS or template.get('kind') != 'home' or not template.get('interior') or template.get('upperFloor'):
        raise ValueError('Ceilings admit only first-batch single-storey furnished homes')
    if template.get('ceiling'):
        raise ValueError('Preserve an existing ceiling instead of applying another')
    width, depth = template['roomSize']
    values = [width, depth, *timber_bounds['origin'], *timber_bounds['extent']]
    if any(not math.isfinite(v) for v in values) or min(timber_bounds['extent']) <= 0:
        raise ValueError('Ceiling dimensions must be finite and positive')
    if any(not 600 <= size <= 900 or abs(size/300-round(size/300)) > 1e-6 for size in (width, depth)):
        raise ValueError('Ceiling rooms require measured 300 cm bays within the reserved footprints')
    thickness = 2*timber_bounds['extent'][2]
    if any(abs(2*timber_bounds['extent'][i]-300) > .1 for i in (0, 1)) or not 10 <= thickness <= 30:
        raise ValueError('Unexpected timber module; survey instead of stretching another asset')
    top = wall_top(template, bounds)
    floor_top = max(p['anchor'][2]+2*bounds[p['mesh']]['extent'][2]*p['scale'][2]
                    for p in template['components'] if p['role'] == 'floor')
    underside = top-thickness
    if not 250 <= underside-floor_top <= 320:
        raise ValueError('Ceiling would change the measured minimum room clearance')
    scale = [300/(2*timber_bounds['extent'][i]) for i in (0, 1)]+[1]
    ox, oy, oz = timber_bounds['origin']; ez = timber_bounds['extent'][2]
    panels = []
    for x in range(round(width/300)):
        for y in range(round(depth/300)):
            centre = [(x+.5)*300-width/2, (y+.5)*300-depth/2]
            # Pitch 180 rotates source X and Z. The source's textured top now
            # faces the room; bounds normalisation includes its timber depth.
            panels.append(dict(mesh=TIMBER, location=[centre[0]+ox*scale[0], centre[1]-oy*scale[1], underside+oz+ez],
                               rotation=[180, 0, 0], scale=scale.copy(), bay=[x, y]))
    probes = [dict(start=[x*150+75-width/2, y*150+75-depth/2, underside-40],
                   end=[x*150+75-width/2, y*150+75-depth/2, top+40])
              for x in range(round(width/150)) for y in range(round(depth/150))]
    return dict(source=TIMBER, panels=panels, probes=probes, roomSize=[width, depth],
                bottomZ=underside, topZ=top, floorTopZ=floor_top, minimumHeadroomCm=underside-floor_top,
                fill=dict(position=[0,0,floor_top+220],dayLumens=5000,nightLumens=3000,
                          attenuationRadiusCm=700,sourceRadiusCm=45,castShadows=False,
                          color=[255,225,195,255] if zone=='sunmeadow_march' else [255,215,185,255]),
                tint=TINTS[zone].copy(), zone=zone, visualApproved=False, licensedDistributionApproved=False)


def validate_ceiling_witnesses(recipe, witnesses):
    """Require every upward grid ray to hit the ceiling inside its measured depth."""
    if len(witnesses) != len(recipe['probes']):
        raise ValueError('Ceiling witness inventory is incomplete')
    for probe, row in zip(recipe['probes'], witnesses):
        if row.get('probe') != probe or not row.get('blockedByCeiling'):
            raise ValueError('Ceiling grid is open or blocked by another object')
        height = row.get('localHeight', math.inf)
        if not math.isfinite(height) or not recipe['bottomZ']-.1 <= height <= recipe['topZ']+.1:
            raise ValueError('Ceiling surface lies outside its measured depth')
