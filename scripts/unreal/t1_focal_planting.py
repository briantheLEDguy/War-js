"""Bounded focal colonies on natural ground, with shared travel/service and existing-plant reserves."""
import math
from t1_landscape_ecology import inside,random_unit,segment_distance
from t1_understorey import PLANTS

PATCHES=((-490,125,60),(-235,75,35),(60,300,45),(250,-245,38))
SPACING=.6


def focal_layout(source,height_cm,pockets,existing,patches=PATCHES):
    if source['id']!='sunmeadow_march' or len(existing)>60000 or len(pockets)>16 or not 1<=len(patches)<=16:
        raise ValueError('Focal planting requires a bounded Sunmeadow study')
    if any(len(p)!=3 or any(not math.isfinite(v) for v in p) or not 1<=p[2]<=100 for p in patches):
        raise ValueError('Invalid focal planting patch')
    anchors=[*source.get('npcs',[]),*source.get('enemies',[]),*source.get('resourceNodes',[]),*source.get('craftingStations',[]),*source.get('zoneTriggers',[])]
    roads=[*source['paths'],*[dict(width=7,points=p['approach']) for p in pockets]]
    reserved=[a for a in source['orvrLayout']['terrain']['flattenAreas'] if a.get('preserveFooting') and '_pocket_' not in a['id']]
    if len(anchors)>4096 or len(roads)>128 or len(reserved)>256 or any(len(r['points'])>512 for r in roads):
        raise ValueError('Focal planting reserve inventory exceeds bounds')
    result={n:[] for n in PLANTS};step=1.15;seen=set();occupied={}
    def key(x,z):return math.floor(x/SPACING),math.floor(z/SPACING)
    def occupy(x,z):occupied.setdefault(key(x,z),[]).append((x,z))
    for row in existing:
        p=row['location']
        if len(p)!=3 or any(not math.isfinite(v) for v in p):raise ValueError('Nonfinite existing planting')
        occupy(p[1]/100,p[0]/100)
    for px,pz,radius in patches:
        for ix in range(math.floor((px-radius)/step),math.ceil((px+radius)/step)):
            for iz in range(math.floor((pz-radius)/step),math.ceil((pz+radius)/step)):
                if (ix,iz) in seen:continue
                seen.add((ix,iz));x=(ix+.1+.8*random_unit(ix,iz,991))*step;z=(iz+.1+.8*random_unit(ix,iz,997))*step;p=dict(x=x,z=z)
                edge=max(0,min(1,(radius-math.hypot(x-px,z-pz))/8))
                if not edge or not inside(p,source['spatial']['playableOutline']):continue
                cell=key(x,z)
                if any(math.hypot(x-a,z-b)<SPACING for dx in (-1,0,1) for dz in (-1,0,1) for a,b in occupied.get((cell[0]+dx,cell[1]+dz),[])):continue
                moisture=(math.sin(x/6+math.sin(z/9))*.5+math.cos(z/11-x/17)*.5+2)/4
                if random_unit(ix,iz,1003)>edge*(.35+moisture*.6):continue
                distance=min((segment_distance(p,a,b)-road['width']/2 for road in roads for a,b in zip(road['points'],road['points'][1:])),default=1000)
                if distance<1.5 or random_unit(ix,iz,1013)>min(1,(distance-1.5)/3.5):continue
                if any(math.hypot(x-a['x'],z-a['z'])<a['radius']+3 for a in reserved) or any(math.hypot(x-a['x'],z-a['z'])<10 for a in anchors):continue
                y=height_cm(x,z);samples=[height_cm(x+1,z),height_cm(x-1,z),height_cm(x,z+1),height_cm(x,z-1)]
                if any(not math.isfinite(v) for v in [y,*samples]):raise ValueError('Nonfinite focal planting ground')
                if any(q['cosmeticWater'] and math.hypot(x-q['x'],z-q['z'])<q['radius']+60 and y<q['waterY']*100+8 for q in pockets):continue
                if math.hypot((samples[0]-samples[1])/200,(samples[2]-samples[3])/200)>.38:continue
                choice=random_unit(ix,iz,1019);plant='SM_Grass_01' if choice<.55 else 'SM_Grass_Long_01' if choice<.92 else 'SM_Fern_01'
                scale=(.45+random_unit(ix,iz,1021)*.45) if plant=='SM_Fern_01' else (.85+random_unit(ix,iz,1021)*.65)
                result[plant].append(dict(location=[z*100,x*100,y],yaw=random_unit(ix,iz,1031)*360,scale=scale));occupy(x,z)
                if len(result[plant])>12000 or sum(map(len,result.values()))>24000:raise ValueError('Focal planting exceeds native batch bounds')
    return result
