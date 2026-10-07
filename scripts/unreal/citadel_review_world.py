"""Private review composition; campaign topology and shared scenery stay distinct."""
import datetime
import math
import re

FARMER='npc_frontier_sunmeadow_empire_farmer'
HERBALIST='npc_frontier_sunmeadow_empire_herbalist'


def review_packages(revision, date):
    if not re.fullmatch('[a-f0-9]{12}', revision) or not re.fullmatch('[0-9]{8}', date):
        raise ValueError('Exact private revision and calendar date required')
    datetime.datetime.strptime(date,'%Y%m%d')
    prefix='/Game/WorldRebuild/CitadelHumanReview_'+date+'_'+revision
    # Editor selection uses short FNames. A generic Population name aliases the
    # retained lower-city population layer because FNames ignore letter case.
    return dict(map=prefix+'/Walkthrough',routing=prefix+'/ReviewRouting',population=prefix+'/Residents_'+revision)


def residents():
    rows=[
        ('forehall_porter','Hale Fenwick',FARMER,[26900,-1400,6010],90),
        ('forehall_steward','Rena Ashwell',HERBALIST,[26900,1400,6010],-90),
        ('hall_attendant_west','Lysa Greyhaven',HERBALIST,[29950,-2750,6010],90),
        ('hall_attendant_east','Orin Valecrest',FARMER,[29950,2750,6010],-90),
        ('archive_scribe','Nella Reedmere',HERBALIST,[29000,-5700,6010],-90),
        ('treasury_factor','Bren Aldermark',FARMER,[29600,5570,6010],90),
        ('west_terrace_visitor','Tessa Highbrook',HERBALIST,[19600,-2950,4210],180),
        ('east_terrace_visitor','Galen Mossford',FARMER,[19600,2950,4210],180),
    ]
    return [dict(id='aegis_citadel_'+identity,name=name,profile=profile,pointCm=point,
        yawDegrees=yaw,role='resident',clearanceRadiusCm=100,heightCm=240) for identity,name,profile,point,yaw in rows]


def checked_residents(plan, furnishing_bounds):
    from aegis_citadel_blueprint import route_clearance
    rows=residents()
    if len({row['id'] for row in rows})!=len(rows):raise ValueError('Duplicate resident identity')
    for row in rows:
        p=row['pointCm'];radius=row['clearanceRadiusCm'];height=row['heightCm']
        if not route_clearance(plan,p,radius,height):raise ValueError('Resident enters a signed route: '+row['id'])
        if any(abs(p[2]-q[2])<height and math.dist(p[:2],q[:2])<650+radius
                for objective in plan['objectives']+plan['optionalObjectives']
                for q in [objective['point'] if isinstance(objective,dict) else objective]):
            raise ValueError('Resident enters an objective: '+row['id'])
        for bounds in furnishing_bounds:
            if all(p[i]+radius>bounds[0][i] and p[i]-radius<bounds[1][i] for i in range(2)) and p[2]<bounds[1][2] and p[2]+height>bounds[0][2]:
                raise ValueError('Resident overlaps furnishings: '+row['id'])
        if any(other is not row and abs(p[2]-other['pointCm'][2])<height
                and math.dist(p[:2],other['pointCm'][:2])<2*radius for other in rows):
            raise ValueError('Residents overlap: '+row['id'])
    return rows


def routing_bindings(actors):
    """Actor snapshots omit these gameplay fields; record them explicitly."""
    rows=[]
    for actor in actors:
        cls=actor.get_class().get_name()
        if cls=='WarZoneAnchor':
            p=actor.get_editor_property('zone_origin');definition=actor.get_editor_property('city_definition')
            rows.append(dict(actor=actor.get_name(),kind=cls,zone=str(actor.get_editor_property('zone_id')),
                origin=[p.x,p.y,p.z],halfSize=actor.get_editor_property('half_size'),
                definition=definition.get_path_name() if definition else None,
                levels=list(map(str,actor.get_editor_property('content_levels')))))
        elif cls=='WarZonePortal':
            p=actor.get_editor_property('arrival_location')
            rows.append(dict(actor=actor.get_name(),kind=cls,route=str(actor.get_editor_property('route_id')),
                destination=str(actor.get_editor_property('destination_route_id')),arrival=[p.x,p.y,p.z],
                radius=actor.get_editor_property('radius'),built=actor.get_editor_property('destination_built')))
    return sorted(rows,key=lambda row:(row['kind'],row['actor']))
