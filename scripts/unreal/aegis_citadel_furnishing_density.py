"""Opt-in source furnishing study; native collision and appearance stay unapproved."""
import hashlib
import math
from pathlib import Path

ARCHITECTURE_GROUPS = frozenset(('court_and_foundations', 'stairs_and_balconies',
    'curtain_gatehouses', 'fortress_keep_shell', 'gothic_facade_and_spires',
    'ribbed_interiors', 'wing_foundation_repairs', 'sculpture_plinths'))
MARGIN_CM = 15
FLOOR_TOLERANCE_CM = .05
CELL_CM = 500


def density_requests():
    """Gathering bays use reviewed assemblies at the retained human scales."""
    rows = []
    def add(group, kind, point, yaw=0, scale=.85):
        rows.append(dict(id=f'density_{group}_{kind}_{len(rows)}', group=group,
            source='public/assets/models/prop_aegis_'+kind+'.glb', point=point,
            yawDegrees=yaw, scale=scale, centerPlan=True))
    def gathering(group, x, y, z, scale=.85):
        add(group, 'citadel_feast_table', [x,y,z], scale=scale)
        for dx in (-170,170):
            add(group, 'civic_bench', [x+dx,y,z], 0 if dx<0 else 180, .8)
    for sign in (-1,1):
        gathering('forehall', 28060, sign*2400, 6010)
        for x in (29150,29750):
            gathering('throne_hall', x, sign*1500, 6010)
        group = 'west_terrace' if sign<0 else 'east_terrace'
        gathering(group, 18700, sign*4200, 4210, .75)
        add(group, 'barrel_cluster', [18150,sign*4550,4210])
    return rows


def study_plan():
    import citadel_review_world
    return dict(version=1, requests=density_requests(), residentReservations=citadel_review_world.residents(),
        sourceRecipeSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        residentRecipeSha256=hashlib.sha256(Path(citadel_review_world.__file__).read_bytes()).hexdigest(),
        nativeClearanceVerified=False, visualApproved=False, gameplayApproved=False)


def overlaps(a, b, margin=0):
    return all(a[1][i]+margin>b[0][i] and a[0][i]-margin<b[1][i] for i in range(3))


def bounds_of(points):
    return [[min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)]]


def aabb_gap(a,b):
    return math.sqrt(sum(max(0,a[0][i]-b[1][i],b[0][i]-a[1][i])**2 for i in range(3)))


def triangle_box_intersection(points, bounds):
    """Thirteen-axis SAT, including edge axes missed by triangle-AABB overlap."""
    center=[(bounds[0][i]+bounds[1][i])/2 for i in range(3)]
    half=[(bounds[1][i]-bounds[0][i])/2 for i in range(3)]
    v=[[p[i]-center[i] for i in range(3)] for p in points]
    edges=[[v[(j+1)%3][i]-v[j][i] for i in range(3)] for j in range(3)]
    def cross(a,b):
        return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    basis=[[1,0,0],[0,1,0],[0,0,1]]
    axes=basis+[cross(edges[0],edges[1])]+[cross(e,a) for e in edges for a in basis]
    for axis in axes:
        if sum(a*a for a in axis)<1e-16: continue
        projected=[sum(p[i]*axis[i] for i in range(3)) for p in v]
        radius=sum(half[i]*abs(axis[i]) for i in range(3))
        if min(projected)>radius+1e-7 or max(projected)<-radius-1e-7: return False
    return True


def floor_height(points, x, y):
    a,b,c=points
    normal_z=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    if normal_z<=1e-8: return None
    u=((x-a[0])*(c[1]-a[1])-(y-a[1])*(c[0]-a[0]))/normal_z
    v=((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/normal_z
    if u < -1e-8 or v < -1e-8 or u+v>1+1e-8: return None
    return a[2]+u*(b[2]-a[2])+v*(c[2]-a[2])


def cells(bounds):
    for x in range(math.floor(bounds[0][0]/CELL_CM),math.floor(bounds[1][0]/CELL_CM)+1):
        for y in range(math.floor(bounds[0][1]/CELL_CM),math.floor(bounds[1][1]/CELL_CM)+1):
            yield x,y


class ArchitectureClearance:
    """Index actual source triangles only near the requested transformed bounds."""
    def __init__(self, meshes, bounds):
        envelopes=[[[b[0][0]-MARGIN_CM,b[0][1]-MARGIN_CM,b[0][2]-FLOOR_TOLERANCE_CM],
                    [b[1][i]+MARGIN_CM for i in range(3)]] for b in bounds]
        self.inventory=[]; self.bins={cell:[] for b in envelopes for cell in cells(b)}
        overall=bounds_of([p for b in envelopes for p in b])
        for mesh in meshes:
            if not mesh.positions or not mesh.indices or len(mesh.indices)%3:
                raise ValueError('Empty or incomplete architecture triangles')
            self.inventory.append(dict(id=mesh.key, triangles=len(mesh.indices)//3))
            for offset in range(0,len(mesh.indices),3):
                p=[mesh.positions[i] for i in mesh.indices[offset:offset+3]]
                if max(q[2] for q in p)<overall[0][2] or min(q[2] for q in p)>overall[1][2]: continue
                tri_bounds=bounds_of(p)
                if not all(tri_bounds[1][i]>=overall[0][i] and tri_bounds[0][i]<=overall[1][i] for i in range(3)): continue
                clipped=[[max(tri_bounds[0][i],overall[0][i]) for i in range(3)],
                         [min(tri_bounds[1][i],overall[1][i]) for i in range(3)]]
                for cell in cells(clipped):
                    if cell in self.bins: self.bins[cell].append((mesh.key,offset//3,p,tri_bounds))
        ids=[r['id'] for r in self.inventory]
        if len(ids)!=len(set(ids)) or set(ids)!=ARCHITECTURE_GROUPS:
            raise ValueError('Complete eight-group architecture closure required')

    def check(self, identity, bounds):
        envelope=[[bounds[0][0]-MARGIN_CM,bounds[0][1]-MARGIN_CM,bounds[0][2]+FLOOR_TOLERANCE_CM],
                  [bounds[1][i]+MARGIN_CM for i in range(3)]]
        near={}
        for cell in cells(envelope):
            for group,ordinal,p,b in self.bins.get(cell,[]): near[(group,ordinal)]=(p,b)
        checked=0
        for key,(p,b) in near.items():
            if not all(b[1][i]>=envelope[0][i] and b[0][i]<=envelope[1][i] for i in range(3)): continue
            checked+=1
            if triangle_box_intersection(p,envelope):
                raise ValueError(f'Architecture intersection: {identity} / {key[0]} triangle {key[1]}')
        samples=[]
        for tx in (0,.5,1):
            for ty in (0,.5,1):
                x=bounds[0][0]+tx*(bounds[1][0]-bounds[0][0])
                y=bounds[0][1]+ty*(bounds[1][1]-bounds[0][1])
                matches=[]
                for (group,ordinal),(p,b) in near.items():
                    if not (b[0][0]<=x<=b[1][0] and b[0][1]<=y<=b[1][1]): continue
                    z=floor_height(p,x,y)
                    if z is not None and abs(z-bounds[0][2])<=FLOOR_TOLERANCE_CM:
                        matches.append(dict(group=group, triangle=ordinal, zCm=z))
                if not matches: raise ValueError(f'Unsupported floor sample: {identity} at {x},{y}')
                samples.append(dict(pointCm=[x,y,bounds[0][2]],support=matches[0]))
        return dict(clearanceEnvelopeCm=envelope, testedTriangles=checked,
            triangleIntersections=0, floorSamples=samples, floorToleranceCm=FLOOR_TOLERANCE_CM)


def route_witness(blueprint, bounds):
    """Conservative circumscribed bounds, clipped by every segment's elevation."""
    center=[(bounds[0][i]+bounds[1][i])/2 for i in range(2)]
    radius=math.dist(bounds[0][:2],bounds[1][:2])/2
    rows=[*blueprint['routes'],*[dict(id='spawn_'+str(r['index']),
        points=r['points'] if len(r['points'])>1 else r['points']*2,width=r['widthCm'])
        for r in blueprint.get('spawnApproaches',[])]]
    witnesses=[]
    for route in rows:
        for ordinal,(a,b) in enumerate(zip(route['points'],route['points'][1:])):
            lo,hi=0.,1.; dz=b[2]-a[2]
            if dz:
                ts=sorted(((bounds[0][2]-207-a[2])/dz,(bounds[1][2]+15-a[2])/dz))
                lo,hi=max(lo,ts[0]),min(hi,ts[1])
                if hi<lo: continue
            elif bounds[1][2]<=a[2]-15 or bounds[0][2]>=a[2]+207: continue
            dx,dy=b[0]-a[0],b[1]-a[1]; length=dx*dx+dy*dy
            t=max(lo,min(hi,((center[0]-a[0])*dx+(center[1]-a[1])*dy)/length)) if length else lo
            gap=math.dist(center,[a[0]+t*dx,a[1]+t*dy])-route['width']/2-radius-10
            witnesses.append(dict(route=route['id'],segment=ordinal,t=t,gapCm=gap))
    worst=min(witnesses,key=lambda r:r['gapCm']) if witnesses else None
    if worst and worst['gapCm']<0: raise ValueError('Signed route reservation: '+worst['route'])
    return dict(circumscribedRadiusCm=radius, closestReservation=worst,
        signedRoutes=len(blueprint['routes']), spawnApproaches=len(blueprint.get('spawnApproaches',[])))


def checked_density(blueprint, architecture, existing, study):
    from aegis_citadel_furnishings import source_furnishing
    from aegis_citadel_mesh import Mesh, append_mesh
    if study!=study_plan(): raise ValueError('Density study differs from its signed source/resident plan')
    requests=study['requests']; prepared=[source_furnishing(r) for r in requests]
    checker=ArchitectureClearance(architecture,[receipt['boundsCm'] for _,receipt in prepared])
    occupied=list(existing); groups={}; ledger=[]
    for request,(mesh,receipt) in zip(requests,prepared):
        bounds=receipt['boundsCm']; identity=request['id']
        room=next((r for r in blueprint['rooms'] if r['id']==request['group']),None)
        if room and not all(room['bounds'][0][i]<=bounds[0][i] and bounds[1][i]<=room['bounds'][1][i] for i in range(3)):
            raise ValueError('Furnishing leaves signed room: '+identity)
        route=route_witness(blueprint,bounds)
        for row in occupied:
            if overlaps(bounds,row['boundsCm'],MARGIN_CM):
                raise ValueError('Furnishing overlap: '+identity+' / '+row['id'])
        center=[(bounds[0][i]+bounds[1][i])/2 for i in range(2)]+[bounds[0][2]]
        radius=route['circumscribedRadiusCm']
        for objective in blueprint['objectives']+blueprint['optionalObjectives']:
            p=objective.get('point') if isinstance(objective,dict) else objective
            if p and abs(p[2]-center[2])<210 and math.dist(p[:2],center[:2])<650+radius:
                raise ValueError('Capture/objective reservation: '+identity)
        for pad in blueprint.get('gameplayPads',[]):
            if pad.get('preserveTransform'): continue
            p=pad['footprintCentreFloorCm']
            if bounds[0][2]<p[2]+pad['maximumHeightCm'] and bounds[1][2]>p[2] and math.dist(p[:2],center[:2])<pad['maximumFootprintRadiusCm']+radius+MARGIN_CM:
                raise ValueError('Gameplay/service pad reservation: '+identity+' / '+pad['id'])
        for gate in blueprint.get('gates',[]):
            for leaf in gate['leaves']:
                x,y,z=leaf['point']; width=leaf['width']; height=leaf['height']
                if overlaps(bounds,[[x-255,y-width/2,z],[x+255,y+width/2,z+height]],MARGIN_CM):
                    raise ValueError('Gate reservation: '+identity)
        for resident in study['residentReservations']:
            p=resident['pointCm']; r=resident['clearanceRadiusCm']
            if overlaps(bounds,[[p[0]-r,p[1]-r,p[2]],[p[0]+r,p[1]+r,p[2]+resident['heightCm']]],MARGIN_CM):
                raise ValueError('Resident reservation: '+identity+' / '+resident['id'])
        geometry=checker.check(identity,bounds)
        neighbor=min((dict(id=r['id'],gapCm=aabb_gap(bounds,r['boundsCm'])) for r in occupied),
            key=lambda r:r['gapCm'],default=None)
        occupied.append(dict(id=identity,boundsCm=bounds))
        group=groups.setdefault(request['group'],Mesh('density_'+request['group']))
        append_mesh(group,mesh)
        ledger.append({**request,**receipt,'routeClearance':route,'architectureClearance':geometry,
            'furnishingMarginCm':MARGIN_CM,'closestPriorFurnishing':neighbor,
            'residentReservations':len(study['residentReservations']),
            'nativeClearanceVerified':False,'visualApproved':False,'gameplayApproved':False})
    return groups,ledger,checker.inventory
