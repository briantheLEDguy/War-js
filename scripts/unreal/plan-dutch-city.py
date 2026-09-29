"""Compile authored winding streets into closed blocks; record unresolved lots.

Requires requirements-dutch-bastion.txt. This stage cannot publish content.
"""
import json
import math
import sys
import hashlib
from dutch_bastion import ROOT, OUT, block, digest, validate

sys.path.insert(0,str(OUT/'python'))
from shapely.geometry import LineString, Polygon, MultiPoint, box, GeometryCollection
from shapely import voronoi_polygons, set_precision
from shapely.errors import GEOSException
from shapely.ops import unary_union, nearest_points
from shapely.geometry.polygon import orient
from dutch_city_validation import canonical_block_id, validate_block, validate_streets, validate_retained_clearance


def street_edges(parcel,boundary):
    """Overlay arithmetic must not turn a real facade into a zero-length edge."""
    from shapely.geometry import Point
    points=list(parcel.exterior.coords)
    return [LineString([a,b]) for a,b in zip(points,points[1:])
            if boundary.distance(Point(a))<2e-6 and boundary.distance(Point(b))<2e-6
            and boundary.distance(LineString([a,b]).interpolate(.5,normalized=True))<2e-6]


def assign_venues(blocks,layout,source):
    """Propose actual room lots; a name alone is never an admitted interior."""
    from dutch_polygon_architecture import main_front, terrain_samples
    assigned=[];pending=[]
    for district,names in layout['publicVenues'].items():
        centre=next(d for d in source['cityDistricts'] if d['id']==district)
        candidates=[]
        for b in blocks:
            if b['district']!=district: continue
            for lot in b['lots']:
                try:
                    polygon,_,_,a,z=main_front(lot);width=math.dist(a,z)
                    if not 5<=width<=8 or polygon.area<35 or polygon.convex_hull.area-polygon.area>.001: continue
                    heights=terrain_samples(polygon)
                    from dutch_city_ground import paving_height
                    doorstep=paving_height(a[0]+(z[0]-a[0])*.25,a[1]+(z[1]-a[1])*.25)
                    if max(heights)-doorstep>.30: continue
                    distance=math.hypot(polygon.centroid.x-centre['x'],polygon.centroid.y-centre['z'])
                    candidates.append((distance,b['id'],lot))
                except ValueError: continue
        used=set()
        for kind,name in zip(('inn','cafe','shop'),names):
            available=[v for v in candidates if v[2]['publicInterior'] is None]
            if not available:
                pending.append(dict(district=district,name=name,kind=kind,reason='No eligible fitted room on retained terrain'))
                continue
            _,block_id,lot=min(available,key=lambda v:(v[1] in used,v[0],v[2]['id']))
            used.add(block_id)
            lot['publicInterior']=dict(kind=kind,name=name,service='atmosphere_only')
            assigned.append(dict(id=lot['actorId'],block=block_id,district=district,kind=kind,name=name,
                                 native=False,visual=False,traversal=False))
    return dict(assigned=assigned,pending=pending)


def corner_parcels(key,district,polygon):
    """Exact cells resolve concave blocks without inserting rectangular fillers.

    Corner parcels can have multiple street-facing wall planes. They need the
    polygonal architecture adapter; a rectangular pilot house is not a substitute.
    """
    polygon=set_precision(polygon,1e-6)
    court=polygon.buffer(-7.2,join_style='mitre')
    if court.area<12: court=Polygon()
    ring=polygon.difference(court)
    openings=[]
    if not court.is_empty:
        candidates=[]
        coords=list(polygon.exterior.coords)
        for index,(a,b) in enumerate(zip(coords,coords[1:])):
            edge=LineString([a,b])
            if edge.length<9: continue
            start=edge.interpolate(.5,normalized=True)
            end=nearest_points(start,court)[1]
            centre=LineString([start,end])
            if centre.length<3 or not polygon.buffer(1e-5).covers(centre): continue
            # Square caps extend into the court and beyond the facade. The
            # intersection records precisely which frontage is intentionally open.
            passage=set_precision(centre.buffer(1.4,cap_style='square'),1e-6).intersection(ring)
            if passage.geom_type!='Polygon' or passage.interiors: continue
            candidates.append((centre.length,index,passage,centre))
        if not candidates: raise ValueError('No safe 2.8m court passage')
        _,index,passage,centre=min(candidates,key=lambda v:(v[0],v[1]))
        openings=[dict(id=key+'_court_passage',kind='court_passage',width=2.8,
                       polygon=list(orient(passage,sign=1).exterior.coords)[:-1],
                       centreline=list(centre.coords))]
        ring=ring.difference(passage)
    perimeter=polygon.exterior.length
    count=max(1,round(perimeter/6.4))
    points=[polygon.exterior.interpolate((i+.5)*perimeter/count) for i in range(count)]
    cells=voronoi_polygons(MultiPoint(points),extend_to=polygon.envelope.buffer(20),ordered=True)
    if sum(c.area for c in cells.geoms)-unary_union(cells).area>.001:
        # Some near-collinear ring sites yield duplicate overlay cells. Clip
        # explicit bisector half-planes instead of accepting overlaps or holes.
        clipped=[];reach=polygon.length*4
        for p in points:
            cell=polygon.envelope.buffer(20)
            for q in points:
                if p.equals(q): continue
                nx,ny=q.x-p.x,q.y-p.y;length=math.hypot(nx,ny);nx/=length;ny/=length
                mx,my=(p.x+q.x)/2,(p.y+q.y)/2;tx,ty=-ny,nx
                half=Polygon([[mx+tx*reach,my+ty*reach],[mx-tx*reach,my-ty*reach],
                              [mx-tx*reach-nx*reach,my-ty*reach-ny*reach],[mx+tx*reach-nx*reach,my+ty*reach-ny*reach]])
                cell=cell.intersection(half)
            clipped.append(cell)
        cells=GeometryCollection(clipped)
    lots=[]
    for index,cell in enumerate(cells.geoms):
        shape=set_precision(cell,1e-6).intersection(ring)
        pieces=list(shape.geoms) if hasattr(shape,'geoms') else [shape]
        for part,p in enumerate(pieces):
            if p.geom_type=='Polygon' and p.area>1e-8: lots.append((f'{key}_parcel_{index:03}_{part}',p))
    # Merge small frontage pieces into their neighbour across an actual shared
    # wall; never drop a wedge or fill it with a visually unrelated primitive.
    while True:
        tiny=next((i for i,(_,p) in enumerate(lots) if sum(e.length for e in street_edges(p,polygon.boundary))<3.9),None)
        if tiny is None: break
        identity,p=lots[tiny]
        neighbours=[(p.boundary.intersection(q.boundary).length,j) for j,(_,q) in enumerate(lots) if j!=tiny]
        length,j=max(neighbours,default=(0,-1))
        if length<1e-6: raise ValueError(f'Disconnected corner parcel: {p.area:.9f}m2 at {p.bounds}')
        other,q=lots[j];merged=p.union(q)
        if merged.geom_type!='Polygon': raise ValueError('Corner merge is not connected')
        lots=[v for n,v in enumerate(lots) if n not in (tiny,j)]+[(min(identity,other),merged)]
        if len(lots)==1: break
    shapes=[p for _,p in lots]
    if abs(sum(p.area for p in shapes)-ring.area)>.001 or ring.symmetric_difference(unary_union(shapes)).area>.001:
        raise ValueError(f'Polygonal frontage coverage failed: area delta {sum(p.area for p in shapes)-ring.area:.9f}, difference {ring.symmetric_difference(unary_union(shapes)).area:.9f}')
    rows=[]
    for identity,p in sorted(lots):
        if not p.is_valid or p.interiors: raise ValueError('Invalid polygonal parcel')
        chains=street_edges(p,polygon.boundary)
        frontage=unary_union(chains)
        chains=[list(g.coords) for g in chains if g.geom_type=='LineString' and g.length>.01]
        rows.append(dict(id=identity,actorId='bastion_dutch_'+identity,
            polygon=[list(c) for c in list(orient(p,sign=1).exterior.coords)[:-1]],
            frontages=chains,width=frontage.length,storeys=2+len(rows)%3,
            courtFrontages=[list(e.coords) for e in street_edges(p,court.boundary)] if not court.is_empty else [],
            gable=('step','bell','triangle')[len(rows)%3],palette=len(rows)%5,
            publicInterior=None,nativeAdapter='polygonal'))
    return dict(id=key,district=district,boundary=list(polygon.exterior.coords)[:-1],
                courts=court.__geo_interface__,lots=rows,openings=openings,
                geometry='exact_polygonal_partition',nativeReady=False)


def compile_city(write=True):
    source=json.loads((ROOT/'public/assets/maps/aegis_capital.json').read_text())
    layout=json.loads((ROOT/'scripts/campaign/dutch-bastion-layout.json').read_text())
    streets=list(layout['streets'])
    for row in source['paths']:
        if row['id'] in layout['retainPaths']:
            endpoint=layout.get('retainedNativeEndpoints',{}).get(row['id'])
            streets.append(dict(id=row['id'],width=row['width'],
                                points=endpoint['points'] if endpoint else [[p['x'],p['z']] for p in row['points']],
                                **(dict(nativeEndpointReason=endpoint['reason']) if endpoint else {})))
    domain=Polygon(layout['boundary'])
    canals=unary_union([box(c['x']-c['width']/2,c['z']-c['depth']/2,c['x']+c['width']/2,c['z']+c['depth']/2) for c in source['canals']])
    road=unary_union([LineString(s['points']).buffer(s['width']/2,join_style='mitre') for s in streets])
    protected=[];links=[]
    for site in layout.get('protectedSites',[])+layout.get('gatheringAreas',[]):
        footprint=Polygon(site['polygon']);protected.append(footprint)
        if not footprint.intersects(road):
            a,b=nearest_points(footprint,road)
            links.append(dict(id='access_'+site['id'],width=3,points=[list(a.coords)[0],list(b.coords)[0]]))
    streets.extend(links)
    road=unary_union([road,*[LineString(s['points']).buffer(s['width']/2,cap_style='square') for s in links]])
    reserves=unary_union(protected)
    # Pavement is one union, avoiding overlapped independent road quads at bends.
    developable=domain.difference(road.buffer(.6,join_style='mitre')).difference(canals.buffer(2.0,join_style='mitre')).difference(reserves)
    polygons=list(developable.geoms) if hasattr(developable,'geoms') else [developable]
    polygons.sort(key=lambda p:(round(p.centroid.y,3),round(p.centroid.x,3)))
    blocks=[];pending=[];spaces=[]
    intended={r['region']:r for r in layout.get('intentionalSpaces',[])}
    for index,shape in enumerate(polygons):
        key=canonical_block_id(shape)
        district=min(source['cityDistricts'],key=lambda d:math.hypot(d['x']-shape.centroid.x,d['z']-shape.centroid.y))['id']
        if key in intended or (layout['revision']=='dutch-blocks-v2' and shape.area<180):
            space=intended.get(key,dict(id='paved_'+key,region=key,kind='junction_paving',name=district.replace('_',' ').title()+' Paved Court'))
            if shape.area>=180 or space['kind'] not in ('canal_walk','square','junction_paving'):
                raise ValueError('Intentional public space changed; reconcile its boundary')
            spaces.append(dict(**space,district=district,polygon=list(orient(shape,sign=1).exterior.coords)[:-1],
                               native=False,visual=False,traversal=False))
            continue
        # Simplification is a proposal only. Neither a changed wall edge nor an
        # unbuildable sliver is silently accepted or turned into placeholder art.
        polygon=orient(shape.simplify(.4,preserve_topology=True),sign=1)
        boundary=[list(p) for p in list(polygon.exterior.coords)[:-1]]
        try:
            if shape.area<180 or len(polygon.interiors): raise ValueError('Small or multiply connected block needs authored resolution')
            b=block(key,district,boundary,7.2,0)
            validate(dict(zone='aegis_capital',blocks=[b]))
            court=Polygon(b['court']);lots=[Polygon(r['polygon']) for r in b['lots']+b['openings']]
            if not court.is_valid or not polygon.covers(court): raise ValueError('Inset court escapes block')
            if any(not p.is_valid or p.area<10 for p in lots): raise ValueError('Invalid corner lot')
            if abs(unary_union(lots).area-sum(p.area for p in lots))>.001: raise ValueError('Overlapping corner lots')
            if polygon.symmetric_difference(unary_union(lots+[court])).area>.001: raise ValueError('Unfilled ring')
            if polygon.intersection(road).area>.01 or polygon.intersection(canals.buffer(1.8)).area>.01:
                raise ValueError('Simplified block intrudes into road/quay')
            validate_block(b);blocks.append(b)
        except (ValueError,GEOSException) as error:
            try:
                if shape.area<180 or polygon.interiors: raise ValueError(str(error))
                b=corner_parcels(key,district,orient(shape,sign=1));validate_block(b);blocks.append(b)
                pending.append(dict(id=key,district=district,area=shape.area,
                    reason='Exact polygonal parcels require native visual and traversal review',geometryResolved=True))
            except (ValueError,GEOSException) as corner_error:
                pending.append(dict(id=key,district=district,area=shape.area,boundary=boundary,reason=str(corner_error),geometryResolved=False))
    from dutch_city_ground import paving_height
    street_review=(validate_streets(streets,source,canals,paving_height) if layout['revision']=='dutch-blocks-v2'
                   else validate_streets(streets,source,canals))
    validate_retained_clearance(streets,layout.get('protectedSites',[]))
    venues=assign_venues(blocks,layout,source)
    if layout['revision']!='dutch-blocks-v2' and set(intended)!={s['region'] for s in spaces}: raise ValueError('An authored public-space boundary changed')
    result=dict(schemaVersion=1,zone='aegis_capital',stage='city_layout_proposal',sourceRevision=layout['revision'],
                sourceSha256=hashlib.sha256((ROOT/'public/assets/maps/aegis_capital.json').read_bytes()).hexdigest(),
                layoutSignature=digest(layout),streets=streets,blocks=blocks,pendingBlocks=pending,
                streetReview=street_review,
                publicVenues=venues,
                intentionalSpaces=spaces,
                protectedSites=layout.get('protectedSites',[]),gatheringAreas=layout.get('gatheringAreas',[]),
                groundSignature=json.loads((OUT/'city-ground.json').read_text())['signature'] if layout['revision']=='dutch-blocks-v2' else None,
                roadSurface=road.intersection(domain).difference(canals).__geo_interface__,
                acceptance=dict(geometry=not pending and street_review['geometryApproved'],visual=False,traversal=False,live=False))
    if write:
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/'city-plan.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(streets=len(streets),closedBlocks=len(blocks),houses=sum(len(b['lots']) for b in blocks),pending=len(pending))))
    return result


if __name__=='__main__': compile_city()
