"""Private catalog adapters for furnished T1 home studies; coordinates are cm."""
import math


def native_home(module, template, ground_y):
    if not module['interiorRequired'] or template.get('kind') != 'home' or not template.get('interior'):
        raise ValueError('Only the two reserved furnished homes may use this adapter')
    if template.get('upperFloor'):
        raise ValueError('Initial T1 home studies require a single floor')
    if not template['mesh'].startswith('/Game/LicensedKits/CapitalExpansion/V1/') or '..' in template['mesh']:
        raise ValueError('House study requires the fingerprinted private catalog')
    if len(template['sha256']) != 64:
        raise ValueError('House study requires a source package fingerprint')
    if not all(math.isfinite(v) for v in [module['x'], module['z'], module['rotY'], ground_y, *template['origin'], *template['extent']]):
        raise ValueError('Non-finite home transform')
    # Catalog front is -Y; T1 source front is -Z, which becomes native -X.
    yaw = module['rotY']-math.pi/2
    c, s = math.cos(yaw), math.sin(yaw)
    ox, oy, oz = template['origin']
    extent = template['extent']
    if min(extent) <= 0 or extent[1]*2 > module['reservation']['depth']*100 or extent[0]*2 > module['reservation']['width']*100:
        raise ValueError('Catalog home exceeds its reserved footprint')
    if extent[2]*2 > 1200:
        raise ValueError('Catalog home exceeds the twelve-metre study height')
    location = [module['z']*100-(ox*c-oy*s), module['x']*100-(ox*s+oy*c), ground_y*100-(oz-extent[2])]

    def point(local):
        x, y, z = local
        return [location[0]+x*c-y*s, location[1]+x*s+y*c, location[2]+z]

    entrance = template['entrance']
    # An aligned approach crosses the doorway before turning inside the room.
    route = [point(entrance), point([entrance[0], -template['roomSize'][1]/2+85, 10]),
             point([entrance[0], 0, 10]), point([0, 0, 10])]
    approach = [[p['z']*100, p['x']*100, ground_y*100] for p in reversed(module['approach'])]
    return dict(id=module['id'], template=template['id'], mesh=template['mesh'], sourceSha256=template['sha256'],
        location=location, yawDegrees=math.degrees(yaw), approachPoints=len(approach), route=approach+route+list(reversed(route[:-1])),
        interiorRoute=route+list(reversed(route[:-1])),
        exteriorEye=point([entrance[0], entrance[1]-400, 170]), exteriorTarget=point([0, 0, 170]),
        interiorEye=point([entrance[0], -template['roomSize'][1]/2+150, 170]),
        interiorTarget=point([0, template['roomSize'][1]/2-90, 135]),
        wallFixture=point([entrance[0]+110, -template['roomSize'][1]/2-15, 230]),
        # Keep the light outside the thick source wall; the kit torch anchor
        # itself lies inside the masonry's collision depth.
        interiorFixture=point([template['roomSize'][0]/2-110, template['roomSize'][1]/4, 200]),
        interiorVolume=point([0, 0, 150]), interiorExtent=[template['roomSize'][0]/2-40, template['roomSize'][1]/2-40, 140],
        visualApproved=False, walkAccepted=False, licensedDistributionApproved=False)
