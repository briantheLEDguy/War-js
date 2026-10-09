"""Bounded read-only counter-climb planning over saved native terrain; no terrain or rules edits."""
import heapq
import math
from t1_landscape_ecology import inside


def ground_walk(height_cm,start,goal,bounds,clear,maximum_grade=.45):
    if not 0<maximum_grade<=.45 or any(not math.isfinite(v) for p in (start,goal) for v in p):raise ValueError('Invalid counter-walk controls')
    step=5;origin=(bounds['minX'],bounds['minZ']);cache={}
    node=lambda p:(round((p[0]-origin[0])/step),round((p[1]-origin[1])/step))
    point=lambda n:(origin[0]+n[0]*step,origin[1]+n[1]*step)
    def admitted(p):
        if p in cache:return cache[p]
        x,z=p
        if not bounds['minX']<=x<=bounds['maxX'] or not bounds['minZ']<=z<=bounds['maxZ'] or not clear(x,z):cache[p]=False;return False
        gx=(height_cm(x+1.5,z)-height_cm(x-1.5,z))/300;gz=(height_cm(x,z+1.5)-height_cm(x,z-1.5))/300
        cache[p]=math.hypot(gx,gz)<=maximum_grade
        return cache[p]
    def linked(a,b):
        length=math.dist(a,b)
        if length<.001:return admitted(a)
        n=max(1,math.ceil(length/2));previous=height_cm(*a)/100
        for i in range(n+1):
            p=(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n)
            if not admitted(p):return False
            y=height_cm(*p)/100
            if i and abs(y-previous)/(length/n)>maximum_grade:return False
            previous=y
        return True
    first,last=node(start),node(goal)
    if not linked(start,point(first)) or not linked(point(last),goal):raise ValueError('Counter-walk endpoints are unsupported')
    queue=[(math.dist(start,goal),0,first)];costs={first:0};parents={};visited=0
    while queue:
        _,cost,current=heapq.heappop(queue)
        if cost>costs[current]+1e-9:continue
        visited+=1
        if visited>12000:raise ValueError('Counter-walk search exceeds bounded inventory')
        if current==last:
            chain=[current]
            while chain[-1]!=first:chain.append(parents[chain[-1]])
            points=[start,*[point(n) for n in reversed(chain)],goal]
            points=[p for i,p in enumerate(points) if i==0 or math.dist(p,points[i-1])>.01]
            return [[z*100,x*100,height_cm(x,z)] for x,z in points]
        a=point(current)
        for dx,dz in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
            neighbor=(current[0]+dx,current[1]+dz);b=point(neighbor)
            if not linked(a,b):continue
            distance=math.dist(a,b);grade=abs(height_cm(*a)-height_cm(*b))/(100*distance)
            next_cost=cost+distance*(1+grade*grade*8)
            if next_cost>=costs.get(neighbor,math.inf):continue
            costs[neighbor]=next_cost;parents[neighbor]=current
            heapq.heappush(queue,(next_cost+math.dist(b,goal),next_cost,neighbor))
    raise ValueError('No counter-climb preserves the grade and clearance limits')


def landscape_walks(source,height_cm,occupied,native_clear):
    identity=source['id'];sun=identity=='sunmeadow_march'
    if not sun and identity!='cinderfen_outskirts':raise ValueError('No admitted scarp study')
    climbs=[c for c in source.get('orvrLayout',{}).get('terrain',{}).get('clearCorridors',[]) if c['id'].startswith(identity+'_scarp_') and c['id'].endswith('_climb')]
    if climbs:
        if len(climbs)!=2:raise ValueError('Authored scarp requires exactly two climbs')
        starts=[(-285,-70),(-60,-15)] if sun else [(-280,-190),(-60,-125)];result=[]
        for i,(start,climb) in enumerate(zip(starts,climbs)):
            vertex=source['paths'][1]['points'][2 if i==0 else 3]
            coordinates=[start,(vertex['x'],vertex['z']),*[(p['x'],p['z']) for p in climb['points']]]
            points=[[z*100,x*100,height_cm(x,z)] for x,z in coordinates]
            for a,b in zip(coordinates,coordinates[1:]):
                length=math.dist(a,b)
                if length<.001:
                    if not native_clear(*a):raise ValueError('Authored scarp climb endpoint is blocked: '+climb['id'])
                    continue
                steps=max(1,math.ceil(length/2));previous=height_cm(*a)
                for j in range(steps+1):
                    x=a[0]+(b[0]-a[0])*j/steps;z=a[1]+(b[1]-a[1])*j/steps;y=height_cm(x,z)
                    if not native_clear(x,z) or j and abs(y-previous)/(100*length/steps)>.45:raise ValueError('Authored scarp climb is blocked or too steep: '+climb['id'])
                    previous=y
            result.append(dict(id=climb['id']+'_walk',points=points,maximumSourceGrade=.45,terrainAndCapsuleChecked=True,
                walkingAccepted=False,drivingAccepted=False,appearanceApproved=False))
        return result
    nominal=(-145,75 if sun else -25);outline=source['spatial']['playableOutline']
    native_cache={};blocked=[]
    def clear_source(x,z):
        if not inside(dict(x=x,z=z),outline):return False
        if any(math.hypot(x-r['x'],z-r['z'])<math.hypot(r['width'],r['depth'])/2+1.5 for r in occupied):return False
        return not any(math.hypot(x-a,z-b)<3 for a,b in blocked)
    def checked_native(x,z):
        key=(round(x,3),round(z,3))
        if key not in native_cache:native_cache[key]=native_clear(x,z)
        return native_cache[key]
    choices=[(nominal[0]+dx,nominal[1]+dz) for dx in range(-15,16,5) for dz in range(-15,16,5)]
    choices.sort(key=lambda p:height_cm(*p),reverse=True)
    starts=[(-285,-70),(-60,-15)] if sun else [(-280,-190),(-60,-125)]
    for goal in choices:
        if not clear_source(*goal) or not checked_native(*goal):continue
        routes=[]
        for i,start in enumerate(starts):
            bounds=dict(minX=min(start[0],goal[0])-100,maxX=goal[0]+25,minZ=min(start[1],goal[1])-25,maxZ=goal[1]+125) if i==0 else dict(
                minX=goal[0]-25,maxX=max(start[0],goal[0])+100,minZ=min(start[1],goal[1])-25,maxZ=goal[1]+125)
            points=None
            for attempt in range(8):
                try:planned=ground_walk(height_cm,start,goal,bounds,clear_source)
                except ValueError:break
                failures=[]
                for a,b in zip(planned,planned[1:]):
                    distance=math.hypot(b[0]-a[0],b[1]-a[1]);count=max(1,math.ceil(distance/200))
                    for j in range(count+1):
                        x=(a[1]+(b[1]-a[1])*j/count)/100;z=(a[0]+(b[0]-a[0])*j/count)/100
                        if not checked_native(x,z):failures.append((x,z))
                if not failures:points=planned;break
                blocked.extend(failures)
            if points is None:break
            routes.append(dict(id=identity+'_scarp_'+('west' if i==0 else 'east')+'_counter',points=points,maximumSourceGrade=.45,
                terrainAndCapsuleChecked=True,walkingAccepted=False,drivingAccepted=False,appearanceApproved=False))
        if len(routes)==2:return routes
    raise ValueError('Scarp requires two independent clear counter-climbs')
