"""Bounded contact-aware burial from native mesh vertices, without changing terrain or footprints."""
import math


def rock_contact(positions,origin,location,scale,yaw,height_cm):
    if not 4<=len(positions)<=20000 or len(origin)!=3 or len(location)!=3 or not .2<=scale<=8 or not all(math.isfinite(v) for v in [*origin,*location,scale,yaw]):raise ValueError('Invalid bounded rock contact input')
    points=[]
    for p in positions:
        if len(p)!=3 or not all(math.isfinite(v) for v in p):raise ValueError('Invalid native rock vertex')
        points.append(tuple(p))
    points=sorted(set(points))
    if len(points)<4:raise ValueError('Insufficient unique rock vertices')
    angle=math.radians(yaw);c,s=math.cos(angle),math.sin(angle);clearances=[];quadrants={}
    for x,y,z in points:
        wx=location[0]+scale*(x*c-y*s);wy=location[1]+scale*(x*s+y*c)
        ground=height_cm(wy/100,wx/100)
        if not math.isfinite(ground):raise ValueError('Nonfinite native rock contact ground')
        clearance=location[2]+z*scale-ground;clearances.append(clearance)
        q=(x>=origin[0],y>=origin[1]);quadrants[q]=min(quadrants.get(q,math.inf),clearance)
    buried=sum(v<=-2 for v in clearances)
    return dict(uniqueVertices=len(points),buriedVertices=buried,buriedFraction=buried/len(points),contactQuadrants=sum(v<=-2 for v in quadrants.values()),minimumClearanceCm=min(clearances),maximumClearanceCm=max(clearances),requiredAdditionalBurialCm=max(0,sorted(clearances)[math.ceil(len(points)*.08)-1]+3,sorted(quadrants.values())[1]+3) if len(quadrants)>=2 else math.inf)


def bed_rock_body(body,mesh,height_cm):
    if 'positions' not in mesh:raise ValueError('Contact bedding requires native surface vertices')
    if len(mesh.get('boundsExtent',[]))!=3 or not all(math.isfinite(v) and v>0 for v in mesh['boundsExtent']):raise ValueError('Invalid native rock extent')
    result={**body,'location':list(body['location'])};height=mesh['boundsExtent'][2]*2*body['scale']
    contact=rock_contact(mesh['positions'],mesh['boundsOrigin'],result['location'],body['scale'],body['yawDegrees'],height_cm)
    required=contact['requiredAdditionalBurialCm'];limit=max(0,min(150,height*.25,body['centreExposureCm']-height*.2))
    if required>limit:return None
    previous=body.get('burialDepthCm',15)
    if not math.isfinite(previous) or previous<0:raise ValueError('Invalid previous rock burial')
    # A small visible tip can satisfy vertex counts; scaled bedding also seats the broader silhouette.
    required=max(required,min(limit,max(0,max(15,min(100,height*.18))-previous)))
    result['location'][2]-=required;result['centreExposureCm']-=required;result['burialDepthCm']=previous+required
    result['contact']=rock_contact(mesh['positions'],mesh['boundsOrigin'],result['location'],body['scale'],body['yawDegrees'],height_cm)
    if result['contact']['buriedFraction']<.08 or result['contact']['contactQuadrants']<2:raise ValueError('Rock contact bedding failed its bounded support contract')
    return result
