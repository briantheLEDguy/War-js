"""Fit continuous paving and explicit, reviewable scenery changes to city lots."""
import hashlib
import json
import math
import sys
from dutch_bastion import ROOT, OUT, digest
sys.path.insert(0,str(OUT/'python'))
from shapely.geometry import Polygon, Point, box, LineString
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
from shapely.geometry.polygon import orient
from dutch_architecture import Mesh, MATERIALS
from dutch_polygon_architecture import polygons
from dutch_city_ground import paving_height
from capital_geography import height
from capital_geography import road_surface
from dutch_mesh_clipping import clip_legacy_roads, retained_road_region
from dutch_city_validation import bridge_decks

plan=json.loads((OUT/'city-plan.json').read_text())
layout=json.loads((ROOT/'scripts/campaign/dutch-bastion-layout.json').read_text())
source=json.loads((ROOT/'public/assets/maps/aegis_capital.json').read_text())
survey=json.loads((OUT/'city-source-survey.json').read_text())
houses=unary_union([Polygon(l['polygon']) for b in plan['blocks'] for l in b['lots']])
domain=Polygon(layout['boundary'])
canals=unary_union([box(c['x']-c['width']/2,c['z']-c['depth']/2,c['x']+c['width']/2,c['z']+c['depth']/2) for c in source['canals']])
interiors=unary_union([Polygon(s['polygon']).buffer(-1.8,join_style='mitre') for s in plan['protectedSites'] if s['kind']=='existing_interior'])
roads=unary_union([LineString(s['points']).buffer(s['width']/2+.6) for s in plan['streets']])
surface_domain=domain.union(unary_union([LineString(s['points']).buffer(s['width']/2,cap_style='flat') for s in plan['streets']]))
open_land=surface_domain.difference(canals).difference(houses).difference(interiors)
surfaces=[];directory=OUT/'city-geometry';directory.mkdir(exist_ok=True)
for tx in range(-150,150,50):
    for tz in range(-150,150,50):
        patch=open_land.intersection(box(tx,tz,tx+50,tz+50))
        if patch.is_empty: continue
        mesh=Mesh()
        for x in range(tx,tx+50):
            for z in range(tz,tz+50):
                # Match the height field's diagonal before clipping road edges.
                for half in ([(x,z),(x+1,z),(x+1,z+1)],[(x,z),(x+1,z+1),(x,z+1)]):
                    cell=patch.intersection(Polygon(half))
                    for polygon in polygons(cell):
                        for triangle in constrained_delaunay_triangles(polygon).geoms:
                            points=list(orient(triangle,sign=1).exterior.coords)[:-1]
                            mesh.face([[px,pz,paving_height(px,pz)+.035] for px,pz in points],'paving')
        for polygon in polygons(patch):
            for ring in (polygon.exterior,*polygon.interiors):
                points=list(ring.coords)
                for a,b in zip(points,points[1:]):
                    if not open_land.boundary.buffer(1e-5).covers(LineString([a,b])): continue
                    count=max(1,math.ceil(math.dist(a,b)))
                    for i in range(count):
                        u=[a[j]+(b[j]-a[j])*i/count for j in (0,1)];v=[a[j]+(b[j]-a[j])*(i+1)/count for j in (0,1)]
                        # Tile boundaries share heights; skirts seal only the
                        # exterior edge and cannot form a lip above the walk.
                        mesh.face([[*u,height(*u)-.25],[*v,height(*v)-.25],
                                   [*v,paving_height(*v)+.035],[*u,paving_height(*u)+.035]],'limestone')
        data=json.dumps(mesh.export((0,0),(1,0),0),separators=(',',':')).encode();sha=hashlib.sha256(data).hexdigest()
        file=directory/(sha+'.json')
        if not file.exists(): file.write_bytes(data)
        key=f'dutch_paving_{tx+150}_{tz+150}'
        surfaces.append(dict(id=key,actorId=key,meshFile=file.relative_to(OUT).as_posix(),meshSha256=sha,
                             position=[0,0,0],materials=list(MATERIALS),palette=0,publicInterior=None,
                             triangles=len(mesh.indices)//3,district='streets',surface=True))

reserved=unary_union([Polygon(s['polygon']) for s in plan['protectedSites']])
combat_cores=unary_union([Polygon(s['polygon']).buffer(-8 if s['purpose']=='combat_market' else -5)
                         for s in plan['gatheringAreas'] if s['purpose'].startswith('combat')])
furniture_land=open_land.difference(roads).difference(reserved).difference(combat_cores).buffer(-.35)
occupied=[];actions=[];conflicts=[]
# The superseded road mesh is a single citywide actor. Keep its triangles
# outside the rebuilt paving domain, but never carry old paving into new rooms.
legacy=next(r for r in survey['actors'] if r['state']['label']=='Crownward source road network')
if set(legacy['state']['tags'])!={'WarCrownwardTerrain','WarZoneObject_aegis_capital_StaticMeshActor_305'} or legacy['state']['transform']!=[0,0,0,0,0,0,1,1,1,1]:
    raise RuntimeError('Legacy road ownership or transform changed')
decks=unary_union([Polygon(d['polygon']).buffer(.1,join_style='mitre') for d in bridge_decks(source)])
# These source triangles are the actual walkable bridge decks. Their separate
# bridge meshes supply architecture, but do not replace this collision surface.
retained=retained_road_region(surface_domain,houses,interiors,decks)
data=clip_legacy_roads(road_surface(),retained)
payload=json.dumps(data,separators=(',',':')).encode();sha=hashlib.sha256(payload).hexdigest()
file=directory/(sha+'.json')
if not file.exists(): file.write_bytes(payload)
surfaces.append(dict(id='dutch_retained_source_roads',actorId='dutch_retained_source_roads',meshFile=file.relative_to(OUT).as_posix(),
                     meshSha256=sha,position=[0,0,0],materials=['/Game/Capitals/aegis_capital/TerrainMaterial_ground'],
                     palette=0,publicInterior=None,triangles=len(data['indices'])//3,district='streets',surface=True))
actions.append(dict(layer=legacy['layer'],name=legacy['name'],action='remove_owned_street',before=legacy['state']))
for row in survey['actors']:
    if row['name']==legacy['name'] and row['layer']==legacy['layer']: continue
    state=row['state'];tags=set(state['tags']);kind=state['class']
    cx,cz,cy,ex,ez,ey=row['bounds'];x,z=cz/100,cx/100;w,d=ez/100,ex/100
    mesh=next((c.get('mesh') for c in state['components'] if c.get('mesh')), '')
    old_house=('/Crownward/SM_MH_02_House_' in mesh or '/CapitalExpansion/' in mesh) and 'WarCapitalInterior' not in tags
    owned=bool(tags.intersection({'WarCapitalBuilding','WarCapitalExpansionV1','WarCrownward','WarCrownwardKit'}))
    if old_house and owned:
        actions.append(dict(layer=row['layer'],name=row['name'],action='remove_owned_house',before=state));continue
    if row['parent']: continue
    footprint=box(x-w,z-d,x+w,z+d)
    # Canal walls, city walls, bridges and terrain remain exactly where authored.
    anchor=any(t in mesh for t in ('Stone_Wall','Stone_Floor','Terrain_','bridge','canal')) or not domain.covers(Point(x,z))
    if anchor: continue
    blocking=kind=='StaticMeshActor' and 'WarCapitalInterior' not in tags and (
        houses.intersection(footprint).area>.01 or roads.intersection(footprint).area>.01 or combat_cores.intersection(footprint).area>.01)
    destination=None
    if blocking:
        for radius in range(2,81,2):
            choices=[]
            for step in range(max(12,round(radius*3))):
                angle=step*math.tau/max(12,round(radius*3));px=x+math.cos(angle)*radius;pz=z+math.sin(angle)*radius
                bounds=box(px-w-.15,pz-d-.15,px+w+.15,pz+d+.15)
                if furniture_land.covers(bounds) and not any(bounds.intersects(p) for p in occupied): choices.append((abs(paving_height(px,pz)-height(x,z)),px,pz,bounds))
            if choices:
                _,px,pz,bounds=min(choices,key=lambda v:v[:3]);destination=(px,pz);occupied.append(bounds);break
        if destination is None:
            conflicts.append(dict(actor=row['name'],reason='No clear scenery relocation',mesh=mesh));continue
    transform=state['transform'];px,pz=destination or (x,z)
    grounded=abs((cy-ey)/100-height(x,z))<1 or kind in ('WarCityNpc','WarQuestNpc','WarCraftingStation','PlayerStart')
    if destination or grounded:
        location=[transform[0]+(pz-z)*100,transform[1]+(px-x)*100,
                  transform[2]+(paving_height(px,pz)-height(x,z)+.035)*100]
        if math.dist(location,transform[:3])>.1:
            actions.append(dict(layer=row['layer'],name=row['name'],action='relocate_scenery' if destination else 'ground_on_paving',
                                before=state,location=location))
result=dict(planSignature=digest(plan),sourceHashes=survey['sourceHashes'],surfaces=surfaces,actions=actions,conflicts=conflicts,
            coverage=dict(blocks=len(plan['blocks']),lots=sum(len(b['lots']) for b in plan['blocks']),
                          buildingArea=houses.area,cityArea=domain.area,openArea=open_land.intersection(domain).area,
                          approachPavingArea=open_land.difference(domain).area))
(OUT/'city-placement.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(surfaces=len(surfaces),actions=len(actions),conflicts=len(conflicts),coverage=result['coverage'])))
