"""Irregular short-grass colonies around admitted cover, with explicit travel/service reserves."""
import copy,math
from t1_landscape_ecology import MODELS,inside,random_unit,segment_distance


def clustered_cover(source,height_cm,pockets,base):
    if source['id'] not in MODELS or not base or len(base)>12000:
        raise ValueError('Regional clusters require a bounded admitted base cover')
    result=copy.deepcopy(base);outline=source['spatial']['playableOutline'];terrain=source['orvrLayout']['terrain']
    anchors=[*source.get('npcs',[]),*source.get('enemies',[]),*source.get('resourceNodes',[]),*source.get('craftingStations',[]),*source.get('zoneTriggers',[])]
    roads=[*source['paths'],*[dict(width=7,points=p['approach']) for p in pockets]]
    reserved=[a for a in terrain['flattenAreas'] if a.get('preserveFooting') and '_pocket_' not in a['id']]
    occupied={}
    def cell(x,z):return math.floor(x/1.4),math.floor(z/1.4)
    def add(x,z):occupied.setdefault(cell(x,z),[]).append((x,z))
    for row in base:
        if len(row.get('location',[]))!=3 or any(not math.isfinite(n) for n in row['location']):raise ValueError('Nonfinite cover seed')
        add(row['location'][1]/100,row['location'][0]/100)
    limit=.2 if source['id']=='sunmeadow_march' else .28
    for index,seed in enumerate(base):
        sx,sz=seed['location'][1]/100,seed['location'][0]/100
        if random_unit(sx,sz,113)>limit:continue
        for sample in range(7):
            angle=random_unit(index,sample,114)*math.tau
            radius=2+math.sqrt(random_unit(index,sample,115))*5.5
            x=sx+math.cos(angle)*radius;z=sz+math.sin(angle)*radius;p=dict(x=x,z=z)
            if not inside(p,outline):continue
            key=cell(x,z)
            if any(math.hypot(x-qx,z-qz)<1.4 for dx in (-1,0,1) for dz in (-1,0,1) for qx,qz in occupied.get((key[0]+dx,key[1]+dz),[])):continue
            if any(segment_distance(p,a,b)<road['width']/2+1.25 for road in roads for a,b in zip(road['points'],road['points'][1:])):continue
            if any(math.hypot(x-a['x'],z-a['z'])<a['radius']+5 for a in reserved):continue
            if any(math.hypot(x-a['x'],z-a['z'])<10 for a in anchors):continue
            y=height_cm(x,z)
            if not math.isfinite(y):raise ValueError('Nonfinite colony terrain support')
            if any(q['cosmeticWater'] and math.hypot(x-q['x'],z-q['z'])<q['radius']+60 and y<q['waterY']*100+4 for q in pockets):continue
            gx=(height_cm(x+1,z)-height_cm(x-1,z))/200;gz=(height_cm(x,z+1)-height_cm(x,z-1))/200
            if not math.isfinite(gx) or not math.isfinite(gz):raise ValueError('Nonfinite colony grade')
            if math.hypot(gx,gz)>.35:continue
            result.append(dict(location=[z*100,x*100,y-2],yaw=random_unit(index,sample,116)*360,scale=.38+random_unit(index,sample,117)*.34))
            add(x,z)
    if len(result)>12000:raise ValueError('Regional clusters exceed the retained native instance budget')
    return result
