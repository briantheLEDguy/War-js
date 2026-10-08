"""Stronger first-pair landforms with unchanged ground under retained content/routes."""
import math

ZONES=('sunmeadow_march','cinderfen_outskirts')


def relief_recipe(zone):
    if zone not in ZONES: raise ValueError('Relief studies admit the first pair only')
    if zone==ZONES[0]:
        features=[dict(id='north_barrows',points=[[-730,410],[-360,485],[0,475],[390,460],[735,300]],radius=125,height=155),
                  dict(id='south_escarpment',points=[[-755,-535],[-350,-540],[80,-530],[445,-490],[770,-355]],radius=130,height=135),
                  dict(id='east_wall',points=[[710,-360],[800,-70],[745,300]],radius=105,height=165),
                  dict(id='western_spur',points=[[-685,135],[-520,240],[-400,345]],radius=105,height=80),
                  dict(id='valley_shoulders',points=[[-210,95],[-25,110],[210,100]],radius=95,height=45)]
    else:
        features=[dict(id='outer_basalt_arc',points=[[-585,-330],[-430,-480],[-95,-525],[365,-450],[585,-210],[575,180],[330,460]],radius=115,height=135),
                  dict(id='inner_caldera_wall',points=[[-385,130],[-170,315],[80,410],[335,345]],radius=100,height=125),
                  dict(id='southern_basalt_teeth',points=[[-365,-410],[-160,-425],[95,-400],[300,-380]],radius=75,height=70),
                  dict(id='mineral_spine',points=[[-120,80],[20,185],[155,240]],radius=70,height=60)]
    return dict(zone=zone,features=features,routePaddingMetres=20,routeFeatherMetres=85,
        anchorPaddingMetres=20,sceneryPaddingMetres=12,sceneryFeatherMetres=45,
        appearanceApproved=False,offRouteTraversalAccepted=False)


def segment_distance(x,z,a,b):
    dx,dz=b[0]-a[0],b[1]-a[1]; length=dx*dx+dz*dz
    t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/length)) if length else 0
    return math.hypot(x-a[0]-t*dx,z-a[1]-t*dz)


def smooth(value):
    value=max(0,min(1,value)); return value*value*(3-2*value)


def relief_height(x,z,features):
    values=[]
    for feature in features:
        distance=min(segment_distance(x,z,a,b) for a,b in zip(feature['points'],feature['points'][1:]))
        q=distance/feature['radius']
        if q<1:
            # Broad mass with a broken crest, rather than isolated cone props.
            crest=.9+.1*math.sin(x/31+math.sin(z/47))**2
            values.append(feature['height']*(1-q*q)**1.5*crest)
    return max(values,default=0)


def deformation_mask(x,z,corridors,areas,boxes,recipe):
    mask=1
    for points,radius in corridors:
        distance=min(segment_distance(x,z,a,b) for a,b in zip(points,points[1:]))
        mask=min(mask,smooth((distance-radius-recipe['routePaddingMetres'])/recipe['routeFeatherMetres']))
        if mask==0: return 0
    for area in areas:
        distance=math.hypot(x-area['x'],z-area['z'])-area['radius']-area.get('feather',0)-recipe['anchorPaddingMetres']
        mask=min(mask,smooth(distance/recipe['routeFeatherMetres']))
        if mask==0: return 0
    for box in boxes:
        distance=math.hypot(max(box[0]-x,0,x-box[1]),max(box[2]-z,0,z-box[3]))
        mask=min(mask,smooth((distance-recipe['sceneryPaddingMetres'])/recipe['sceneryFeatherMetres']))
        if mask==0: return 0
    return mask


def deform_surface(data,source,boxes,population):
    recipe=relief_recipe(source['id'])
    if data['zoneId']!=source['id'] or len(data['indices'])%3: raise ValueError('Relief surface identity/topology mismatch')
    corridors=[([[p['x'],p['z']] for p in path['points']],path.get('width',12)/2) for path in source['paths']]
    for row in population:
        corridors.append(([[p[1]/100,p[0]/100] for p in row['approach']],6))
    areas=source['orvrLayout']['terrain']['flattenAreas']
    positions=[]; changed=0; maximum=0
    for p in data['positions']:
        if len(p)!=3 or any(not math.isfinite(v) for v in p): raise ValueError('Relief requires finite native vertices')
        height=relief_height(p[1]/100,p[0]/100,recipe['features'])
        delta=height*deformation_mask(p[1]/100,p[0]/100,corridors,areas,boxes,recipe)*100 if height else 0
        positions.append([p[0],p[1],p[2]+delta]); maximum=max(maximum,delta); changed+=delta>.001
    normals=[[0,0,0] for _ in positions]
    for n in range(0,len(data['indices']),3):
        ids=data['indices'][n:n+3]
        if any(not isinstance(i,int) or not 0<=i<len(positions) for i in ids): raise ValueError('Invalid terrain triangle index')
        a,b,c=[positions[i] for i in ids]; u=[b[i]-a[i] for i in range(3)]; v=[c[i]-a[i] for i in range(3)]
        normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        # Existing native terrain exports use clockwise indices after source
        # XZ -> Unreal XY conversion. Keep those indices, orient normals up.
        if normal[2]<0: normal=[-v for v in normal]
        for index in ids:
            for axis in range(3): normals[index][axis]+=normal[axis]
    for i,normal in enumerate(normals):
        length=math.sqrt(sum(v*v for v in normal))
        if length<=1e-9 or normal[2]<=0: raise ValueError('Terrain winding/normals must face upward')
        normals[i]=[v/length for v in normal]
    return {**data,'positions':positions,'normals':normals},dict(recipe=recipe,changedVertices=changed,
        maximumAddedHeightMetres=maximum/100,protectedCorridors=len(corridors),protectedBoxes=len(boxes),
        sourceTopologyPreserved=True,routeGroundPreserved=True,appearanceApproved=False,offRouteTraversalAccepted=False)
