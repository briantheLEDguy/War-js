"""Deterministic Sunmeadow understorey studies; cosmetic planting preserves travel and service reserves."""
import math
from t1_landscape_ecology import inside, random_unit, segment_distance
from t1_habitat_surface import habitat_masks

PLANTS=('SM_Grass_01','SM_Grass_Long_01','SM_Fern_01','SM_White_Oak_Sapling_01')


def understorey_layout(source,height_cm,pockets,meadow,canopies):
    if source['id']!='sunmeadow_march' or len(meadow)>12000 or len(canopies)>500:
        raise ValueError('Understorey requires a bounded Sunmeadow ecology study')
    outline=source['spatial']['playableOutline'];terrain=source['orvrLayout']['terrain']
    anchors=[*source.get('npcs',[]),*source.get('enemies',[]),*source.get('resourceNodes',[]),*source.get('craftingStations',[]),*source.get('zoneTriggers',[])]
    roads=[*source['paths'],*[dict(width=7,points=p['approach']) for p in pockets]]
    reserved=[a for a in terrain['flattenAreas'] if a.get('preserveFooting') and '_pocket_' not in a['id']]
    seeds=[]
    for row in meadow:
        z,x,y=row['location'];x/=100;z/=100
        if any(not math.isfinite(v) for v in (x,y,z)):raise ValueError('Nonfinite meadow seed')
        if random_unit(x,z,187)<.1:seeds.append((x,z,False,4.5,6))
    for row in canopies:
        z,x,y=row['location'];x/=100;z/=100
        if any(not math.isfinite(v) for v in (x,y,z)):raise ValueError('Nonfinite canopy seed')
        seeds.append((x,z,True,7.5,96))
    result={p:[] for p in PLANTS};occupied={}
    def key(x,z):return math.floor(x/.6),math.floor(z/.6)
    for index,(sx,sz,shade,radius,count) in enumerate(seeds):
        for sample in range(count):
            angle=random_unit(index,sample,197)*math.tau;r=math.sqrt(random_unit(index,sample,199))*radius
            x=sx+math.cos(angle)*r;z=sz+math.sin(angle)*r;p=dict(x=x,z=z)
            if not inside(p,outline):continue
            cell=key(x,z)
            if any(math.hypot(x-a,z-b)<.6 for dx in (-1,0,1) for dz in (-1,0,1) for a,b in occupied.get((cell[0]+dx,cell[1]+dz),[])):continue
            road_distance=min((segment_distance(p,a,b)-road['width']/2 for road in roads for a,b in zip(road['points'],road['points'][1:])),default=1000)
            if road_distance<1.5 or random_unit(index,sample,211)>min(1,(road_distance-1.5)/3.5):continue
            if any(math.hypot(x-a['x'],z-a['z'])<a['radius']+3 for a in reserved):continue
            if any(math.hypot(x-a['x'],z-a['z'])<10 for a in anchors):continue
            y=height_cm(x,z)
            if not math.isfinite(y):raise ValueError('Nonfinite understorey footing')
            if any(q['cosmeticWater'] and math.hypot(x-q['x'],z-q['z'])<q['radius']+60 and y<q['waterY']*100+5 for q in pockets):continue
            gx=(height_cm(x+1,z)-height_cm(x-1,z))/200;gz=(height_cm(x,z+1)-height_cm(x,z-1))/200
            if any(not math.isfinite(v) for v in (gx,gz)):raise ValueError('Nonfinite understorey grade')
            if math.hypot(gx,gz)>.38:continue
            soil,macro,moisture=habitat_masks(x,z,source['id'])
            if random_unit(index,sample,223)>.25+.7*moisture:continue
            choice=random_unit(index,sample,227)
            plant=('SM_White_Oak_Sapling_01' if choice<.035 else 'SM_Fern_01' if choice<.36 else 'SM_Grass_Long_01' if choice<.65 else 'SM_Grass_01') if shade else ('SM_Grass_Long_01' if choice<.35 else 'SM_Grass_01')
            scale=(.5+random_unit(index,sample,229)*.6) if plant=='SM_Fern_01' else (.85+random_unit(index,sample,229)*.9)
            result[plant].append(dict(location=[z*100,x*100,y],yaw=random_unit(index,sample,233)*360,scale=scale,shade=shade))
            occupied.setdefault(cell,[]).append((x,z))
    if sum(len(v) for v in result.values())>24000:raise ValueError('Understorey exceeds the native study budget')
    return result
