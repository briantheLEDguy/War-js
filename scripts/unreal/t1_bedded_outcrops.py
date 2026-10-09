"""Broken bedrock bands follow exposed source ridges while reserving all travel and gameplay anchors."""
import math
from t1_landscape_ecology import inside,random_unit,segment_distance


def outcrop_footing(height_cm,p):
    if any(not math.isfinite(p[k]) for k in ('x','z','width','depth','yawDegrees')) or not 0<p['width']<=100 or not 0<p['depth']<=100:
        raise ValueError('Invalid geological footprint')
    angle=-math.radians(p['yawDegrees']);c,s=math.cos(angle),math.sin(angle);samples=[]
    for u in range(-3,4):
        for v in range(-3,4):
            a,b=p['width']*u/6,p['depth']*v/6
            samples.append(height_cm(p['x']+a*c-b*s,p['z']+a*s+b*c))
    if any(not math.isfinite(h) for h in samples):raise ValueError('Nonfinite geological footing')
    return min(samples)-20


def bedded_outcrops(source,height_cm,occupied):
    identity=source['id'];sun=identity=='sunmeadow_march'
    if not sun and identity!='cinderfen_outskirts':raise ValueError('Outcrops require an admitted first-pair region')
    terrain=source['orvrLayout']['terrain'];result=[]
    ridges=[r for r in terrain['naturalField']['ridges'] if r['profile']=='escarpment' or (not sun and r['profile']=='shelf') or (sun and r['id'] in ('barrow_finger','eastern_shoulder'))]
    anchors=[*source.get('npcs',[]),*source.get('enemies',[]),*source.get('resourceNodes',[]),*source.get('craftingStations',[]),*source.get('zoneTriggers',[])]
    for ri,ridge in enumerate(ridges):
        for si,(a,b) in enumerate(zip(ridge['points'],ridge['points'][1:])):
            dx,dz=b['x']-a['x'],b['z']-a['z'];length=math.hypot(dx,dz)
            if length<1:raise ValueError('Degenerate geological ridge')
            for index in range(max(1,math.floor(length/14))):
                salt=ri*79+si*13+191;t=(index+.2+.6*random_unit(index,ri,salt))/max(1,math.floor(length/14))
                width=a['width']+(b['width']-a['width'])*t
                for band in range(2):
                    if random_unit(index,band,salt+1)<.24:continue
                    offset=width*((.5 if ridge['profile']=='escarpment' else .85)+band*.23+(random_unit(index,band,salt+2)-.5)*.2)
                    sign=-1 if ridge['profile']=='escarpment' or band==0 else 1
                    x=a['x']+dx*t-dz/length*offset*sign;z=a['z']+dz*t+dx/length*offset*sign
                    scale=1.25+random_unit(index,band,salt+3)*.95
                    axes=[scale*(2.0+random_unit(index,band,salt+4)*.5),scale*.6,scale*(1.2+random_unit(index,band,salt+5)*.3)]
                    dimensions=[7,5,3] if sun else [6,5,3];w,d,h=[v*s for v,s in zip(dimensions,axes)];radius=math.hypot(w,d)/2;p=dict(x=x,z=z)
                    if not inside(p,source['spatial']['playableOutline']):continue
                    if min(segment_distance(p,c,e) for c,e in zip(source['spatial']['playableOutline'],source['spatial']['playableOutline'][1:]+source['spatial']['playableOutline'][:1]))<radius+3:continue
                    if any(segment_distance(p,c,e)<c0['radius']+radius+3 for c0 in terrain['clearCorridors'] for c,e in zip(c0['points'],c0['points'][1:])):continue
                    if any(segment_distance(p,c,e)<path['width']/2+radius+3 for path in source['paths'] for c,e in zip(path['points'],path['points'][1:])):continue
                    if any((q.get('preserveFooting') or q['id'].endswith('_scarp_overlook')) and math.hypot(x-q['x'],z-q['z'])<radius+q['radius']+8 for q in terrain['flattenAreas']):continue
                    if any(math.hypot(x-q['x'],z-q['z'])<radius+12 for q in anchors):continue
                    if any(math.hypot(x-q['x'],z-q['z'])<radius+math.hypot(q['width'],q['depth'])/2+2 for q in [*occupied,*result]):continue
                    gx=(height_cm(x+1,z)-height_cm(x-1,z))/200;gz=(height_cm(x,z+1)-height_cm(x,z-1))/200
                    if not math.isfinite(gx) or not math.isfinite(gz):raise ValueError('Nonfinite outcrop support')
                    if not .28<=math.hypot(gx,gz)<=1.25:continue
                    # Match the native embedding samples; reject slabs that would vanish beneath their hillside.
                    yaw=-math.degrees(math.atan2(dz,dx))+(random_unit(index,band,salt+6)-.5)*16
                    base=outcrop_footing(height_cm,dict(x=x,z=z,width=w,depth=d,yawDegrees=yaw))
                    visible=h-(height_cm(x,z)-base)/100
                    if visible<h*.35:continue
                    # Source width is native local Y: negate the source ridge heading to align bedding.
                    result.append(dict(id=identity+'_bedrock_'+ridge['id']+'_'+str(si)+'_'+str(index)+'_'+str(band),sourceLabel=identity+('_barrow_ridge_8' if sun else '_basalt_shelf_1'),x=x,z=z,
                        width=w,depth=d,height=h,scaleAxes=axes,yawDegrees=yaw,
                        tiltDegrees=[0,0],grounding='embed',embedding='orientedFootprint',sourceRidge=ridge['id'],estimatedCentreExposureMetres=visible))
    if len(result)>160:raise ValueError('Geological dressing exceeds its bounded inventory')
    return result
