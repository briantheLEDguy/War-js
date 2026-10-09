"""Terrain-led exploration-pocket planting using existing admitted parent meshes."""
import math
from t1_landscape_ecology import inside,random_unit,segment_distance


def pocket_dressing(source,height_cm,pockets,occupied):
    identity=source['id'];sun=identity=='sunmeadow_march'
    if not sun and identity!='cinderfen_outskirts':raise ValueError('No admitted pocket dressing region')
    terrain=source['orvrLayout']['terrain'];result=[]
    anchors=[*source.get('npcs',[]),*source.get('enemies',[]),*source.get('resourceNodes',[]),*source.get('craftingStations',[]),*source.get('zoneTriggers',[])]
    for pocket_index,pocket in enumerate(pockets):
        count=0;cx,cz=pocket['x'],pocket['z'];extent=pocket['radius']+48
        for ix in range(-12,13):
            for iz in range(-12,13):
                salt=37+pocket_index*19
                x=cx+(ix+random_unit(ix,iz,salt)*.7)*4.5;z=cz+(iz+random_unit(ix,iz,salt+1)*.7)*4.5
                p=dict(x=x,z=z)
                if math.hypot(x-cx,z-cz)>extent or not inside(p,source['spatial']['playableOutline']):continue
                y=height_cm(x,z)/100;relative=y-(pocket['waterY'] if pocket['cosmeticWater'] else pocket['bedY'])
                if not (-.03 if pocket['cosmeticWater'] else .05)<=relative<=2.5:continue
                # Uneven moisture-following patches leave open banks; no decorative circular ring.
                patch=(math.sin(x/7+math.cos(z/11))+math.cos(z/9-x/23)+2)/4
                if random_unit(ix,iz,salt+2)>.18+.65*patch:continue
                rock=random_unit(ix,iz,salt+3)<.23
                scale=(.32+.38*random_unit(ix,iz,salt+4)) if rock else (.35+.4*random_unit(ix,iz,salt+4))
                dimensions=[7,5,3] if rock and sun else [6,5,3] if rock else [6,2,3] if sun else [5,4,4]
                axes=[scale*1.3,scale,scale*.7] if rock else [scale]*3
                radius=math.hypot(dimensions[0]*axes[0],dimensions[1]*axes[1])/2
                if any(segment_distance(p,a,b)<c['radius']+radius+2 for c in terrain['clearCorridors'] for a,b in zip(c['points'],c['points'][1:])):continue
                if any(a.get('preserveFooting') and '_pocket_' not in a['id'] and math.hypot(x-a['x'],z-a['z'])<a['radius']+radius+4 for a in terrain['flattenAreas']):continue
                if any(math.hypot(x-a['x'],z-a['z'])<radius+12 for a in anchors):continue
                if any(math.hypot(x-a['x'],z-a['z'])<radius+math.hypot(a['width'],a['depth'])/2+1 for a in [*occupied,*result]):continue
                gx=(height_cm(x+1,z)-height_cm(x-1,z))/200;gz=(height_cm(x,z+1)-height_cm(x,z-1))/200
                if math.hypot(gx,gz)>(.7 if rock else .42):continue
                label='barrow_ridge_8' if rock and sun else 'basalt_shelf_1' if rock else 'advance_hedgerow_8' if sun else 'peat_dyke_16'
                result.append(dict(id=pocket['id']+'_bank_'+str(count),sourceLabel=identity+'_'+label,x=x,z=z,
                    width=dimensions[0]*axes[0],depth=dimensions[1]*axes[1],height=dimensions[2]*axes[2],scaleAxes=axes,
                    yawDegrees=random_unit(ix,iz,salt+5)*360,tiltDegrees=[(random_unit(ix,iz,salt+6)-.5)*10,0] if rock else [0,0],grounding='embed' if rock else 'root'))
                count+=1
    if len(result)>800:raise ValueError('Pocket dressing exceeds bounded native inventory')
    return result
