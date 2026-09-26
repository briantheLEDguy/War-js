"""Authored capital recipes and deterministic spatial planning (no Unreal dependency).

Coordinates are centimetres. Recipes use bounds-centre XY / bottom Z anchors;
native asset adaptation resolves the purchased mesh pivots once, before merging.
"""
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ZONES = ('aegis_capital', 'riftspire_capital')
VERSION = 1
INTERIORS = ('home', 'home', 'home', 'home', 'shop', 'shop', 'workshop', 'workshop',
             'inn', 'inn', 'guild', 'civic')
HOUSE_NAMES = ('House_01', 'House_02', 'House_03', 'House_04a', 'House_04b', 'House_04c',
               'Viking_House_01', 'Viking_House_02', 'Viking_House_04', 'Viking_House_05',
               'Viking_House_06', 'Viking_House_08')
DISTRICTS = {
    'aegis_capital': ('gateward', 'cinderbank', 'lantern_quays', 'bellfound', 'crownwatch'),
    'riftspire_capital': ('ashgate', 'market', 'warrens', 'commons', 'works', 'crown'),
}
# Independent roles avoid washing timber, slate and plaster with the same tint.
PALETTES = {
    'gateward': ((.76,.73,.64), (.19,.25,.32), (.31,.40,.46)),
    'cinderbank': ((.43,.45,.46), (.24,.25,.28), (.45,.24,.18)),
    'lantern_quays': ((.62,.67,.64), (.23,.31,.34), (.25,.42,.40)),
    'bellfound': ((.78,.77,.68), (.27,.33,.39), (.39,.46,.31)),
    'crownwatch': ((.68,.72,.74), (.19,.24,.32), (.29,.35,.49)),
    'ashgate': ((.33,.32,.34), (.16,.18,.22), (.40,.20,.18)),
    'market': ((.48,.43,.42), (.23,.19,.25), (.40,.24,.34)),
    'warrens': ((.39,.40,.35), (.20,.24,.24), (.27,.36,.30)),
    'commons': ((.45,.46,.48), (.19,.23,.26), (.39,.21,.24)),
    'works': ((.32,.36,.36), (.16,.20,.22), (.25,.40,.36)),
    'crown': ((.49,.47,.53), (.18,.18,.25), (.37,.27,.44)),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def admit_mesh(inventory, name):
    """Admit a fingerprinted static-mesh inventory entry, never a Blueprint path."""
    matches=[row for row in inventory if row['name']==name]
    if len(matches)!=1: raise ValueError('Missing/ambiguous mesh: '+name)
    row=matches[0]
    if (not name.startswith('SM_') or '..' in row['path']
            or not row['path'].startswith(('/Game/Medieval_Environment/','/Game/Medieval_Mod_Town/'))
            or row['path'].rsplit('.',1)[-1]!=name or not row.get('materials')
            or not all(row['materials']) or len(row.get('sha256',''))!=64
            or any(c not in '0123456789abcdef' for c in row['sha256'])):
        raise ValueError('Unreviewed mesh: '+name)
    return row


def piece(mesh, x, y, z=0, yaw=0, scale=(1,1,1), role='original', **extra):
    return dict(mesh=mesh, anchor=[x,y,z], yaw=yaw, scale=list(scale), role=role, **extra)


def interior_recipe(index, realm, dimensions=None):
    """Twelve different plans, open entrances, furnished circulation and real stairs."""
    nx, ny, floors = ((2,3,1),(3,3,1),(2,4,2),(3,3,2),(4,3,1),(3,4,2),
                      (3,4,1),(4,3,1),(3,4,2),(4,4,2),(3,3,2),(4,3,2))[index]
    if dimensions: nx,ny,floors=dimensions
    w, d = nx*300, ny*300
    rows = []
    def add(name,x,y,z=0,yaw=0,scale=(1,1,1),role='wall'):
        rows.append(piece('SM_MH_02_'+name,x,y,z,yaw,scale,role))
    xs = [(i+.5)*300-w/2 for i in range(nx)]
    ys = [(i+.5)*300-d/2 for i in range(ny)]
    entrance_x = xs[-1]
    for f in range(floors):
        for x in xs:
            for y in ys:
                # The complete 3-bay stairwell remains open above its walking run.
                if not dimensions and f and x == xs[0] and y < ys[0]+600:
                    continue
                add('Stone_Floor_01' if f==0 else 'Wood_Floor_01',x,y,f*300,role='floor')
        for x in xs:
            for side in (-1,1):
                name = 'Stone_Wall_Window_01' if (x != xs[0] or f) else 'Stone_Wall_01'
                if f==0 and side==-1 and x==entrance_x:
                    name = 'Stone_Wall_Door_01'
                add(name,x,side*d/2,10+f*300,0 if side==-1 else 180)
        for y in ys:
            for side in (-1,1):
                add('Wood_Wall_Window_01' if f else 'Stone_Wall_Window_01',side*w/2,y,10+f*300,90)
    # Slate roofs replace the repeated thatch blanket. Roof run/rise change
    # together, preserving pitch while accommodating different building depths.
    roof_z = 10+floors*300
    for x in xs:
        for side in (-1,1):
            add('Slate_Roof_01',x,side*d/4,roof_z,180 if side==-1 else 0,
                (1,d/600,d/600),'roof')
    # Gable infill retains kit geometry, including end-wall windows.
    for side in (-1,1):
        for half in (-1,1):
            add('Stone_Wall_Roof_L_01' if half==-1 else 'Stone_Wall_Roof_R_01',
                side*w/2,half*d/4,roof_z,90,(d/600,1,d/600))
    routes = [[entrance_x,-d/2-180,10],[entrance_x,-d/2+160,10],
              [entrance_x,0,10],[0,0,10],[entrance_x,-d/2-180,10]]
    if floors>1 and not dimensions:
        # Stone stair modules rise along negative Y: 3 x 100 cm gives 300 cm.
        for step in range(3):
            add('Stone_Stairs_02',xs[0],ys[0]+75+step*150,10+step*100,180,role='floor')
        routes += [[xs[0],ys[0]-50,10]]
        routes += [[xs[0],ys[0]+step*75,10+step*50] for step in range(7)]
        routes += [[xs[0],ys[0]+650,310],[0,ys[0]+650,310]]
    # Furnish the right-hand strip behind the entrance, leaving the central
    # circulation and the western staircase clear. Each role has a unique scene.
    function = INTERIORS[index]
    furniture = {
        'home': ('SM_Bed','SM_Bookshelf','SM_Crate','SM_Table_Round'),
        'shop': ('SM_Counter','SM_Bookshelf','SM_Market_Table','SM_Crate'),
        'workshop': ('SM_Market_Table','SM_Crate_2','SM_Barrel','SM_Bench_2'),
        'inn': ('SM_Table_Round','SM_Bench','SM_Barrel','SM_Counter'),
        'guild': ('SM_Table','SM_Bookshelf','SM_Bookshelf','SM_Bench_2'),
        'civic': ('SM_Counter','SM_Bookshelf','SM_Table','SM_Bench'),
    }[function]
    positions = [(w/2-145,d/2-170,90),(0,d/2-70,180),
                 (w/2-110,70,90),(-w/2+110,d/2-130,270)]
    for n,(mesh,(x,y,yaw)) in enumerate(zip(furniture,positions)):
        rows.append(piece(mesh,x,y,10,yaw,role='furniture'))
        if mesh in ('SM_Table','SM_Table_Round','SM_Market_Table','SM_Counter'):
            rows.append(piece(('SM_Book','SM_Bottle','SM_Cup')[index%3],x,y,100,role='furniture',support=n))
    if floors>1:
        rows += [piece('SM_Bed_2',w/2-140,d/2-160,310,90,role='furniture'),
                 piece('SM_Bookshelf',w/2-70,0,310,90,role='furniture')]
    if not dimensions:
        rows += [piece('SM_Torch',w/2-40,d/4,180+floor*300,270) for floor in range(floors)]
    # Authored porch, roofed on alternating buildings; no closed door component.
    for x in xs[-2:]:
        add('Stone_Floor_01',x,-d/2-150,0,role='floor')
        if index%2:
            add('Slate_Porch_Roof_01',x,-d/2-150,270,180,role='roof')
    rows += [piece('SM_Chimney_2',xs[0]+80,d/4,roof_z+d/2-120,role='original'),
             piece('SM_Barrel' if index%2 else 'SM_Crate',-w/2+70,-d/2-90,10,role='furniture')]
    return {'id': f'{realm}_interior_{index:02d}_{function}', 'kind':function, 'interior': True,
            'roomSize':[w,d],
            'upperFloor': floors>1, 'components':rows, 'routes':routes,
            'size':[w+120,d+650], 'entrance':[entrance_x,-d/2-180,10]}


def recipes():
    result = []
    for zone in ZONES:
        realm = 'aegis' if zone=='aegis_capital' else 'riftspire'
        for i,name in enumerate(HOUSE_NAMES):
            # Realm character uses its authored native house set wherever available.
            mesh = f'riftspire_house_{i+1}' if realm=='riftspire' and i<8 else 'SM_MH_02_'+name
            result.append({'id':f'{realm}_residence_{i:02d}', 'kind':'residence','interior':False,
                           'upperFloor':False,'components':[piece(mesh,0,0)],'routes':[],
                           'size':None,'entrance':None})
        result.extend(interior_recipe(i,realm) for i in range(12))
        for i,dimensions in enumerate(((1,2,2),(2,2,1),(2,3,1),(1,3,3),(2,2,2),(3,2,1),
                                        (2,2,3),(2,3,2),(3,3,1),(1,2,3),(3,2,2),(2,3,3))):
            compact=interior_recipe(i,realm,dimensions)
            compact.update(id=f'{realm}_compact_{i:02d}',kind='residence',interior=False,upperFloor=False,routes=[],entrance=None)
            compact['components']=[p for p in compact['components'] if p['role']!='furniture']
            result.append(compact)
    return result


def rotate(x,y,yaw):
    angle=math.radians(yaw)
    return x*math.cos(angle)-y*math.sin(angle), x*math.sin(angle)+y*math.cos(angle)


def walking_route(template):
    """Continuous doorway/stair route; diagonal shortcuts can hit door frames."""
    w,d=template['roomSize']; door_x=template['entrance'][0]; west=-w/2+150
    entrance=[[door_x,-d/2-180,10],[door_x,-d/2+85,10],[door_x,0,10],[0,0,10]]
    if not template['upperFloor']: return entrance+list(reversed(entrance[:-1]))
    approach=[[door_x,0,10],[door_x,-d/2+85,10],[west,-d/2+85,10]]
    stair=[[west,-d/2+150+i*75,10+i*50] for i in range(7)]
    landing=[[west,-d/2+800,310],[0,-d/2+800,310]]
    ascent=approach+stair+landing
    return entrance+ascent+list(reversed(ascent[:-1]))+[[door_x,-d/2+85,10],entrance[0]]


def rectangle(center, size, yaw, padding=0):
    return [(center[0]+x,center[1]+y) for x,y in
            (rotate(sx*(size[0]/2+padding),sy*(size[1]/2+padding),yaw)
             for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1)))]


def overlaps(a,b):
    """Separating-axis test; unlike AABBs this preserves diagonal street space."""
    for polygon in (a,b):
        for p,q in zip(polygon,polygon[1:]+polygon[:1]):
            axis = (p[1]-q[1],q[0]-p[0])
            pa=[x*axis[0]+y*axis[1] for x,y in a]
            pb=[x*axis[0]+y*axis[1] for x,y in b]
            if max(pa)<=min(pb) or max(pb)<=min(pa): return False
    return True


def source_obstacles(source):
    obstacles=[]
    for p in source.get('props',[]):
        # Surface geometry supports the city, so never treat its overall bounds
        # as a building blocker. Authored colliders still protect walls and houses.
        if any(word in p['kind'] for word in ('rock_sector','rock_infill','deck','terrain','ground')):
            continue
        s=p.get('scale',1)
        for c in p.get('colliders',[]):
            if c.get('maxY',0)-c.get('minY',0)<.6: continue
            yaw=-math.degrees(p.get('rotY',0))
            dx,dy=rotate(c.get('x',0)*100*s*p.get('scaleX',1),c.get('z',0)*100*s*p.get('scaleZ',1),yaw)
            obstacles.append(rectangle((p['x']*100+dx,p['z']*100+dy),
                (c['width']*100*s*p.get('scaleX',1),c['depth']*100*s*p.get('scaleZ',1)),yaw,110))
    for p in source.get('npcs',[])+source.get('zoneTriggers',[]):
        obstacles.append(rectangle((p.get('x',0)*100,p.get('z',0)*100),(900,900),0))
    p=source['spawnPoint']
    obstacles.append(rectangle((p['x']*100,p['z']*100),(1800,1800),0))
    for path in source.get('paths',[]):
        for a,b in zip(path['points'],path['points'][1:]):
            dx,dz=b['x']-a['x'],b['z']-a['z']
            obstacles.append(rectangle(((a['x']+b['x'])*50,(a['z']+b['z'])*50),
                (math.hypot(dx,dz)*100,path['width']*100+200),math.degrees(math.atan2(dz,dx))))
    return obstacles


def validate_plan(plan):
    if 'signature' in plan and plan['signature']!=digest({k:v for k,v in plan.items() if k!='signature'}):
        raise ValueError('Expansion plan fingerprint changed')
    ids=[p['id'] for p in plan['placements']]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate expansion identity')
    for zone in ZONES:
        rows=[p for p in plan['placements'] if p['zone']==zone and not p.get('replacement')]
        if len(rows)!=120: raise ValueError('Expected 120 additions in '+zone)
        interiors=[p for p in rows if p['interior']]
        if Counter(p['kind'] for p in interiors)!=Counter(INTERIORS): raise ValueError('Interior mix changed')
        if len({p['district'] for p in interiors})<4: raise ValueError('Interiors are not distributed')
        if sum(p['upperFloor'] for p in interiors)<4: raise ValueError('Upper floors missing')
        counts=Counter(p['recipe'] for p in rows)
        if len(counts)<12 or max(counts.values())>=len(rows)*.15: raise ValueError('Insufficient architectural variety')
        for i,a in enumerate(rows):
            if not all(math.isfinite(v) for v in a['position']+[a['yaw']]): raise ValueError('Invalid transform')
            for b in rows[:i]:
                if (a['position'][2]<b['position'][2]+b['height'] and b['position'][2]<a['position'][2]+a['height']
                        and overlaps(a['footprint'],b['footprint'])): raise ValueError('Buildings overlap')
                distance=math.dist(a['position'][:2],b['position'][:2])
                if distance<2400 and a['recipe']==b['recipe']: raise ValueError('Repeated adjacent composition')


def require_unchanged(expected, current):
    if expected != current:
        raise ValueError('Saved city changed; preserve owner edits and reconcile the expansion baseline')


def canonical_actor_state(state):
    """Quaternion q and -q encode the same rotation after attachment reload."""
    result=copy.deepcopy(state)
    for row in [result]+result.get('components',[]):
        transform=row.get('transform')
        if not isinstance(transform,list) or len(transform)!=10: continue
        sign=next((transform[i] for i in (6,3,4,5) if transform[i]!=0),1)
        if sign<0: transform[3:7]=[-v for v in transform[3:7]]
    return result


class SpatialIndex:
    """Conservative nearby lookup followed by exact oriented footprint tests."""
    def __init__(self): self.cells={}

    def keys(self, polygon):
        for x in range(math.floor(min(p[0] for p in polygon)/2000),math.floor(max(p[0] for p in polygon)/2000)+1):
            for y in range(math.floor(min(p[1] for p in polygon)/2000),math.floor(max(p[1] for p in polygon)/2000)+1):
                yield x,y

    def add(self, polygon, bottom=-1e9, top=1e9, identity=None):
        row=(polygon,bottom,top,identity)
        for key in self.keys(polygon): self.cells.setdefault(key,[]).append(row)

    def blocked(self, polygon, bottom, top, ignore=None):
        seen=set()
        for key in self.keys(polygon):
            for row in self.cells.get(key,[]):
                if id(row) in seen: continue
                seen.add(id(row))
                shape,low,high,identity=row
                if ignore is not None and identity==ignore: continue
                if bottom<high and top>low and overlaps(polygon,shape): return True
        return False


def city_candidates(zone, source):
    result=[]
    if zone=='aegis_capital':
        from capital_geography import height
        for x in range(-15500,15501,300):
            for z in range(-14000,12501,300):
                district=min(source['cityDistricts'],key=lambda d:(d['x']*100-x)**2+(d['z']*100-z)**2)
                result.append({'xy':[z,x],'z':height(x/100,z/100)*100,'yaw':0,
                               'district':district['id'],'score':math.hypot(district['x']*100-x,district['z']*100-z)})
    else:
        for p in source['props']:
            if p['kind'] not in ('riftspire_deck','riftspire_deck_open'): continue
            for dx in (-650,0,650):
                for dz in (-350,350):
                    rx,rz=rotate(dx,dz,-math.degrees(p.get('rotY',0)))
                    x,z=p['x']*100+rx,p['z']*100+rz
                    district=min(source['cityDistricts'],key=lambda d:
                                 (d['x']*100-x)**2+(d['z']*100-z)**2+4*(d.get('y',0)-p.get('y',0))**2*10000)
                    result.append({'xy':[z,x],'z':p.get('y',0)*100,'yaw':90-math.degrees(p.get('rotY',0)),
                                   'district':district['id'],'score':math.hypot(district['x']*100-x,district['z']*100-z)})
    return sorted(result,key=lambda p:(p['score'],p['xy'],p['yaw']))


def plan_city(zone, source, baseline, templates, support):
    """Fit authored compositions to surveyed city space; support is a native trace callback."""
    origin=baseline['origin']; index=SpatialIndex()
    for actor in baseline['actors']:
        state=actor['state']; label=state['label'].lower()
        components=state['components']
        meshes=[c.get('mesh','') or '' for c in components]
        if not meshes or not any(meshes): continue
        text=' '.join(meshes).lower()
        if any(n in text for n in ('rock_','terrain','ground','mountain','floor','deck','bridge','stairs','path')): continue
        center=actor['center']; extent=actor['extent']
        if max(extent[:2])>6000 or extent[2]<30: continue
        index.add(rectangle([center[0]-origin[0],center[1]-origin[1]],
                            [2*extent[0],2*extent[1]],0,75),center[2]-extent[2]-40,center[2]+extent[2])
    # Preserve source road corridors, services and arrivals independently of mesh bounds.
    road_source={**source,'props':[]}
    for polygon in source_obstacles(road_source): index.add([(y,x) for x,y in polygon])
    candidates=city_candidates(zone,source)
    realm='aegis' if zone=='aegis_capital' else 'riftspire'
    ordered=[templates[f'{realm}_interior_{i:02d}_{kind}'] for i,kind in enumerate(INTERIORS)]
    ordered += [templates[f'{realm}_residence_{(i*5+i//12)%12:02d}'] for i in range(108)]
    placed=[]; failed=[]; native_rejected=set()
    for number,template in enumerate(ordered):
        district=DISTRICTS[zone][number%len(DISTRICTS[zone])]
        size=[2*e for e in template['extent'][:2]]
        selected=None
        preferred=[p for p in candidates if p['district']==district]
        alternatives=[p for p in candidates if p['district']!=district]
        for candidate in preferred+alternatives:
            for turn in (0,90):
                yaw=candidate['yaw']+turn; xy=candidate['xy']; z=candidate['z']
                key=(tuple(xy),yaw,template['id'])
                if key in native_rejected: continue
                polygon=rectangle(xy,size,yaw,100)
                if zone=='aegis_capital' and any(abs(y)>16400 or x<-15100 or x>12900 for x,y in polygon): continue
                if index.blocked(polygon,z+50,z+2*template['extent'][2]):
                    native_rejected.add(key);continue
                if any(p['recipe']==template['id'] and math.dist(p['position'][:2],xy)<2400 for p in placed): continue
                ground=support(xy,yaw,template,z)
                if ground is None:
                    native_rejected.add(key);continue
                selected={'id':f'expansion_v1_{zone}_{number:03d}','zone':zone,'district':candidate['district'],
                          'recipe':template['id'],'kind':template['kind'],'interior':template['interior'],
                          'upperFloor':template['upperFloor'],'position':[xy[0],xy[1],ground],
                          'yaw':yaw,'footprint':polygon,'height':template['extent'][2]*2}
                index.add(polygon,ground-40,ground+2*template['extent'][2]);break
            if selected: break
        if selected: placed.append(selected)
        else: failed.append((number,template['id'],district))
    # Small individually composed townhouses fill remaining urban gaps at native
    # scale. Large kit assemblies are never squeezed to fit a ten-metre pad.
    unresolved=[]
    for number,previous,district in failed:
        if templates[previous]['interior']:
            unresolved.append(previous);continue
        selected=None
        variants=sorted((t for key,t in templates.items() if key.startswith(realm+'_compact_')),
                        key=lambda t:(sum(p['recipe']==t['id'] for p in placed),(int(t['id'].rsplit('_',1)[1])-number)%12))
        for template in variants:
            if sum(p['recipe']==template['id'] for p in placed)>=17: continue
            size=[2*e for e in template['extent'][:2]]
            for candidate in sorted(candidates,key=lambda p:(p['district']!=district,p['score'],p['xy'])):
                for turn in (0,90):
                    xy=candidate['xy'];yaw=candidate['yaw']+turn;z=candidate['z']
                    key=(tuple(xy),yaw,template['id'])
                    if key in native_rejected: continue
                    polygon=rectangle(xy,size,yaw,80)
                    if zone=='aegis_capital' and any(abs(y)>16400 or x<-15100 or x>12900 for x,y in polygon): continue
                    if index.blocked(polygon,z+50,z+2*template['extent'][2]):
                        native_rejected.add(key);continue
                    if any(p['recipe']==template['id'] and math.dist(p['position'][:2],xy)<2400 for p in placed): continue
                    ground=support(xy,yaw,template,z)
                    if ground is None:
                        native_rejected.add(key);continue
                    selected={'id':f'expansion_v1_{zone}_{number:03d}','zone':zone,'district':candidate['district'],
                              'recipe':template['id'],'kind':'residence','interior':False,'upperFloor':False,
                              'position':[xy[0],xy[1],ground],'yaw':yaw,'footprint':polygon,'height':template['extent'][2]*2}
                    index.add(polygon,ground-40,ground+2*template['extent'][2]);break
                if selected: break
            if selected: break
        if selected: placed.append(selected)
        else: unresolved.append(previous)
    return placed,unresolved
