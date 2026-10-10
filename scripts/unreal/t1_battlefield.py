"""Pure native triangle sampling and vertical assembly rebasing for the battlefield prototype."""
import copy
import math

ZONES = ('sunmeadow_march', 'cinderfen_outskirts')


def terrain_sampling_bounds(spatial):
    """Keep triangle sampling local when nonplayable scenery expands ownership."""
    content = spatial['bounds']; bounds = spatial.get('terrainBounds', content)
    for value in (content, bounds):
        if not isinstance(value, dict) or any(isinstance(value.get(k), bool) or not isinstance(value.get(k), (int, float))
                or not math.isfinite(value[k]) for k in ('minX', 'maxX', 'minZ', 'maxZ')):
            raise ValueError('Invalid terrain sampling bounds')
        if value['minX'] >= value['maxX'] or value['minZ'] >= value['maxZ']:
            raise ValueError('Empty terrain sampling bounds')
    if bounds['minX'] < content['minX'] or bounds['maxX'] > content['maxX'] or bounds['minZ'] < content['minZ'] or bounds['maxZ'] > content['maxZ']:
        raise ValueError('Terrain sampling escapes content ownership')
    if any(not bounds['minX'] <= p['x'] <= bounds['maxX'] or not bounds['minZ'] <= p['z'] <= bounds['maxZ'] for p in spatial.get('playableOutline', [])):
        raise ValueError('Playable outline escapes terrain sampling')
    return bounds


class Surface:
    def __init__(self, source, mesh):
        if source['id'] not in ZONES or mesh['zoneId'] != source['id']:
            raise ValueError('Surface must use its admitted regional identity')
        self.bounds = terrain_sampling_bounds(source['spatial']); self.grid = source['spatial']['terrainGrid']
        self.nx, self.nz = self.grid['segmentsX'], self.grid['segmentsZ']
        self.heights = [None] * ((self.nx+1)*(self.nz+1))
        b = self.bounds
        for p in mesh['positions']:
            if len(p) != 3 or not all(math.isfinite(v) for v in p): raise ValueError('Invalid terrain vertex')
            x = (p[1]/100-b['minX'])/(b['maxX']-b['minX'])*self.nx
            z = (p[0]/100-b['minZ'])/(b['maxZ']-b['minZ'])*self.nz
            ix, iz = round(x), round(z)
            if not 0 <= ix <= self.nx or not 0 <= iz <= self.nz or abs(x-ix) > .001 or abs(z-iz) > .001:
                raise ValueError('Terrain vertex escapes its rectangular grid')
            index = iz*(self.nx+1)+ix
            if self.heights[index] is not None: raise ValueError('Duplicate terrain vertex')
            self.heights[index] = p[2]
        if any(h is None for h in self.heights): raise ValueError('Terrain grid has missing vertices')

    def height_cm(self, x, z):
        b = self.bounds
        if not all(math.isfinite(v) for v in (x, z)) or not b['minX'] <= x <= b['maxX'] or not b['minZ'] <= z <= b['maxZ']:
            raise ValueError('Ground sample escapes its terrain sampling extent')
        fx = (x-b['minX'])/(b['maxX']-b['minX'])*self.nx; fz = (z-b['minZ'])/(b['maxZ']-b['minZ'])*self.nz
        ix, iz = min(self.nx-1, math.floor(fx)), min(self.nz-1, math.floor(fz)); tx, tz = fx-ix, fz-iz
        at = lambda dx,dz:self.heights[(iz+dz)*(self.nx+1)+ix+dx]
        return (at(0,0)+tx*(at(1,0)-at(0,0))+tz*(at(0,1)-at(0,0)) if tx+tz <= 1
                else at(1,1)+(1-tx)*(at(0,1)-at(1,1))+(1-tz)*(at(1,0)-at(1,1)))


def rebase_inventory(states, previous, source, old_surface, next_surface):
    if previous['id'] != source['id'] or source['id'] not in ZONES: raise ValueError('Assembly identities differ')
    result = copy.deepcopy(states); groups = {}
    for keep in source['orvrLayout']['keeps']:
        old = next(k for k in previous['orvrLayout']['keeps'] if k['objectiveId'] == keep['objectiveId'])
        groups[keep['objectiveId']] = (keep['y']-old['y'])*100
    for label, state in states.items():
        if '_village_furnished_home_' in label and state['kind'] == 'mesh' and label.rsplit('_',1)[-1] in ('0','1'):
            p = state['location']; groups[label] = next_surface.height_cm(p[1]/100,p[0]/100)-old_surface.height_cm(p[1]/100,p[0]/100)
    shifted = 0
    for label, state in result.items():
        if label in (source['id']+'_terrain',source['id']+'_roads'): continue
        matches = [delta for prefix,delta in groups.items() if label == prefix or label.startswith(prefix+'_')]
        if len(matches) > 1: raise ValueError('Ambiguous native assembly')
        p = state['location']
        delta = matches[0] if matches else next_surface.height_cm(p[1]/100,p[0]/100)-old_surface.height_cm(p[1]/100,p[0]/100)
        if not math.isfinite(delta) or abs(delta) > 25000: raise ValueError('Unbounded vertical rebase')
        p[2] += delta; shifted += abs(delta) > .001
    return result, dict(actors=len(result), verticallyShiftedActors=shifted, completeAssemblyDeltasCm=groups,
                       xyAndBindingsPreserved=True, terrainFootingAccepted=False)


def rebase_population(rows, old_surface, next_surface):
    result = copy.deepcopy(rows)
    for row in result:
        p = row['savedState']['location']
        p[2] += next_surface.height_cm(p[1]/100,p[0]/100)-old_surface.height_cm(p[1]/100,p[0]/100)
        row['point'] = p[:]
        for p in row['approach']: p[2] = next_surface.height_cm(p[1]/100,p[0]/100)
    return result


def rebase_homes(rows, groups, old_surface, next_surface):
    result = copy.deepcopy(rows)
    for row in result:
        delta = groups[row['id']]
        for key in ('location','exteriorEye','exteriorTarget','interiorEye','interiorTarget','wallFixture','interiorFixture','interiorVolume'):
            p = row.get(key)
            if isinstance(p,list) and len(p) == 3 and all(isinstance(n,(int,float)) for n in p): p[2] += delta
        for i,p in enumerate(row['route']):
            if i < row['approachPoints']: p[2] = next_surface.height_cm(p[1]/100,p[0]/100)
            else: p[2] += delta
        for p in row['interiorRoute']: p[2] += delta
        row['walkAccepted'] = False
    return result
