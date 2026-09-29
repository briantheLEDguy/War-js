"""City authoring admission checks; these do not replace native traversal."""
import math
import sys
from dutch_bastion import OUT, digest
sys.path.insert(0,str(OUT/'python'))
from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import unary_union
from shapely import affinity
from capital_geography import height


def bridge_decks(source):
    rows=[]
    for prop in source['props']:
        if 'bridge' not in prop.get('kind',''): continue
        for index,surface in enumerate(prop.get('walkableSurfaces',[])):
            scale=prop.get('scale',1)
            width=surface['width']*scale*prop.get('scaleX',1)
            depth=surface['depth']*scale*prop.get('scaleZ',1)
            deck=box(-width/2,-depth/2,width/2,depth/2)
            deck=affinity.rotate(deck,-prop.get('rotY',0),origin=(0,0),use_radians=True)
            deck=affinity.translate(deck,prop['x'],prop['z'])
            rows.append(dict(id=f"{prop['id']}_deck_{index}",polygon=list(deck.exterior.coords)[:-1]))
    return rows


def canonical_block_id(polygon):
    # Coordinate ownership makes unaffected IDs independent of enumeration or
    # the insertion of a new street/block elsewhere in the capital.
    points=[(round(x,6),round(y,6)) for x,y in list(polygon.exterior.coords)[:-1]]
    variants=[points[i:]+points[:i] for i in range(len(points))]
    reverse=list(reversed(points));variants.extend(reverse[i:]+reverse[:i] for i in range(len(reverse)))
    return 'city_block_'+digest(min(variants))[:12]


def validate_block(block):
    boundary=Polygon(block['boundary'])
    if not boundary.is_valid: raise ValueError('Invalid closed block')
    court=shape(block['courts']) if 'courts' in block else Polygon(block['court'])
    lots=[Polygon(row['polygon']) for row in block['lots']]
    openings=[Polygon(row['polygon']) for row in block['openings']]
    regions=lots+openings+([court] if not court.is_empty else [])
    if any(not p.is_valid or p.is_empty for p in regions): raise ValueError('Invalid lot, passage or court')
    union=unary_union(regions)
    if boundary.symmetric_difference(union).area>1e-3: raise ValueError('Accidental block gap or overshoot')
    if abs(sum(p.area for p in regions)-union.area)>1e-4: raise ValueError('Overlapping lots')
    # Check coverage on the wall plane independently of area. One-centimetre
    # shifts at a corner can hide in an otherwise close total-area comparison.
    covered=unary_union([p.boundary for p in lots+openings]).buffer(1e-5)
    if boundary.boundary.difference(covered).length>1e-4: raise ValueError('Unfilled street frontage')
    for opening in block['openings']:
        if opening['kind']!='court_passage' or opening['width']<2: raise ValueError('Undeclared or narrow opening')
        p=Polygon(opening['polygon'])
        if p.distance(court)>1e-5 or p.distance(boundary.boundary)>1e-5:
            raise ValueError('Passage does not join street to court')
        if 'centreline' in opening:
            centreline=LineString(opening['centreline'])
        else:
            a,b,c,d=opening['polygon']
            centreline=LineString([[(a[i]+b[i])/2 for i in (0,1)],[(c[i]+d[i])/2 for i in (0,1)]])
        if unary_union(lots).distance(centreline)<1-1e-5:
            raise ValueError('Court passage pinches below two metres between actual wall planes')
    if not court.is_empty and not openings: raise ValueError('Enclosed court has no intentional entrance')
    ids=[r['id'] for r in block['lots']+block['openings']]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate lot identity')
    return dict(block=block['id'],frontageMetres=boundary.length,lotCount=len(lots),coverage=True)


def validate_streets(streets,source,canals,ground=height):
    ids=[r['id'] for r in streets]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate street identity')
    decks=bridge_decks(source)
    road=unary_union([LineString(s['points']).buffer(s['width']/2,join_style='mitre') for s in streets])
    walkable=unary_union([road.difference(canals),*[Polygon(d['polygon']) for d in decks]])
    capsule=walkable.buffer(-.42,join_style='mitre')
    pending=[]
    for street in streets:
        line=LineString(street['points'])
        uncovered=line.difference(capsule.buffer(1e-5))
        if uncovered.length>.01:
            pending.append(dict(id=street['id'],reason='Centreline leaves capsule-clear land or an existing bridge',length=uncovered.length))
        max_grade=0
        for a,b in zip(street['points'],street['points'][1:]):
            length=math.dist(a,b);count=max(1,math.ceil(length))
            samples=[[a[j]+(b[j]-a[j])*i/count for j in (0,1)] for i in range(count+1)]
            for p,q in zip(samples,samples[1:]):
                # Canal beds are not bridge deck heights.
                if any(Polygon(d['polygon']).buffer(.1).intersects(LineString([p,q])) for d in decks): continue
                max_grade=max(max_grade,abs(ground(*q)-ground(*p))/math.dist(p,q))
        # Below the native capsule's 45-degree limit, including grid diagonals.
        if max_grade>.8: pending.append(dict(id=street['id'],reason='Steep retained terrain requires native route review',maxGrade=max_grade))
    components=len(capsule.geoms) if hasattr(capsule,'geoms') else 1
    if components!=1: pending.append(dict(id='street_network',reason='Disconnected capsule-clear walking regions',components=components))
    return dict(bridges=decks,connected=components==1,components=components,pending=pending,
                capsuleRadiusMetres=.42,geometryApproved=not pending)


def validate_retained_clearance(streets,sites):
    # The recorded reservation includes a two-metre perimeter outside the
    # existing native interior bounds. Roads must clear the actual building.
    interiors=[(s['id'],Polygon(s['polygon']).buffer(-2,join_style='mitre'))
               for s in sites if s['kind']=='existing_interior']
    for street in streets:
        corridor=LineString(street['points']).buffer(street['width']/2+.1,cap_style='flat')
        for key,building in interiors:
            if corridor.intersection(building).area>1e-4:
                raise ValueError('Street '+street['id']+' intersects preserved interior '+key)
