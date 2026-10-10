"""Bounded cosmetic meadow patches with irregular edges and retained movement/service reserves."""
import math,zlib
from t1_landscape_ecology import inside,random_unit,segment_distance


def _smooth(value):
    value=max(0,min(1,value));return value*value*(3-2*value)


def meadow_weight(a,b,radius_x,radius_z,coarse,fine):
    """Continuous radial edge; noise changes the outline rather than drawing a rectangular patch."""
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (a,b,radius_x,radius_z,coarse,fine)) or min(radius_x,radius_z)<=0 or not 0<=coarse<=1 or not 0<=fine<=1:raise ValueError('Invalid meadow weight sample')
    radius=.78+.16*coarse
    return _smooth((radius-math.hypot(a/radius_x,b/radius_z))/.18)*(.72+.28*fine)


def _noise(x,z,salt):
    ix,iz=math.floor(x),math.floor(z);u,v=_smooth(x-ix),_smooth(z-iz)
    return (random_unit(ix,iz,salt)*(1-u)+random_unit(ix+1,iz,salt)*u)*(1-v)+(random_unit(ix,iz+1,salt)*(1-u)+random_unit(ix+1,iz+1,salt)*u)*v


def meadow_layout(source,height_cm,patches,visible_widths=None,limit=24000):
    """Authoring only; original gameplay ground widths are retained even when visible tracks are narrower."""
    if source.get('id')!='sunmeadow_march' or not isinstance(patches,list) or not 1<=len(patches)<=8 or isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=24000:raise ValueError('Invalid bounded meadow inventory')
    widths={} if visible_widths is None else visible_widths;paths=source['paths'];outline=source['spatial']['playableOutline'];terrain=source['orvrLayout']['terrain']
    if not isinstance(widths,dict) or any(key not in {p['id'] for p in paths} for key in widths):raise ValueError('Unknown meadow visual route')
    roads=[]
    for road in paths:
        width=widths.get(road['id'],road['width'])
        if isinstance(width,bool) or not isinstance(width,(int,float)) or not math.isfinite(width) or not 2<=width<=road['width']:raise ValueError('Invalid meadow visual route width')
        for a,b in zip(road['points'],road['points'][1:]):
            radius=width/2+4;roads.append((a,b,width/2,min(a['x'],b['x'])-radius,max(a['x'],b['x'])+radius,min(a['z'],b['z'])-radius,max(a['z'],b['z'])+radius))
    pads=[p for p in terrain['flattenAreas'] if p.get('preserveFooting')];anchors=[*source.get('npcs',[]),*source.get('enemies',[]),*source.get('resourceNodes',[]),*source.get('craftingStations',[]),*source.get('zoneTriggers',[]),*source['orvrLayout']['keeps'],*source['orvrLayout']['battlefieldObjectives'],*source['orvrLayout']['stagingCamps']]
    scans=0;ids=set()
    for p in patches:
        keys=('x','z','radiusX','radiusZ','angle','spacing')
        if not isinstance(p,dict) or not isinstance(p.get('id'),str) or not p['id'] or p['id'] in ids or any(isinstance(p.get(k),bool) or not isinstance(p.get(k),(int,float)) or not math.isfinite(p[k]) for k in keys) or max(abs(p['x']),abs(p['z']))>10000 or not 2<=min(p['radiusX'],p['radiusZ'])<=max(p['radiusX'],p['radiusZ'])<=100 or not .3<=p['spacing']<=2:raise ValueError('Invalid meadow patch recipe')
        ids.add(p['id']);scans+=(2*math.ceil(p['radiusX']/p['spacing'])+1)*(2*math.ceil(p['radiusZ']/p['spacing'])+1)
    if scans>250000:raise ValueError('Meadow candidate sampling budget exceeded')
    rows=[];occupied=set()
    for patch in sorted(patches,key=lambda p:p['id']):
        salt=zlib.crc32(patch['id'].encode())&0xffff;step=patch['spacing'];rx,rz=patch['radiusX'],patch['radiusZ'];c,s=math.cos(patch['angle']),math.sin(patch['angle'])
        for ix in range(-math.ceil(rx/step),math.ceil(rx/step)+1):
            for iz in range(-math.ceil(rz/step),math.ceil(rz/step)+1):
                a=(ix+(random_unit(ix,iz,salt+1)-.5)*.8)*step;b=(iz+(random_unit(ix,iz,salt+2)-.5)*.8)*step
                density=meadow_weight(a,b,rx,rz,_noise(a/11,b/11,salt+3),_noise(a/7,b/7,salt+4))
                if random_unit(ix,iz,salt+5)>=density:continue
                x=patch['x']+a*c-b*s;z=patch['z']+a*s+b*c;p=dict(x=x,z=z)
                if not inside(p,outline):continue
                verge=min((segment_distance(p,a,b)-half for a,b,half,l,r,low,high in roads if l<=x<=r and low<=z<=high),default=4)
                if verge<1 or random_unit(ix,iz,salt+6)>_smooth((verge-1)/3):continue
                if any(math.hypot(x-a['x'],z-a['z'])<a['radius']+4 for a in pads) or any(math.hypot(x-a['x'],z-a['z'])<12 for a in anchors):continue
                samples=[height_cm(x,z),height_cm(x+1,z),height_cm(x-1,z),height_cm(x,z+1),height_cm(x,z-1)]
                if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or not -10000<=v<=35000 for v in samples):raise ValueError('Invalid meadow terrain sample')
                y,xp,xm,zp,zm=samples;grade=math.hypot((xp-xm)/200,(zp-zm)/200)
                if grade>.35:continue
                cell=(round(x*4),round(z*4))
                if cell in occupied:continue
                occupied.add(cell);rows.append(dict(x=x,z=z,y=y,scale=.8+.35*random_unit(ix,iz,salt+7),yaw=random_unit(ix,iz,salt+8)*360,mesh='SM_Grass_01' if random_unit(ix,iz,salt+9)<.8 else 'SM_Grass_Long_01',patch=patch['id'],grade=grade))
                if len(rows)>limit:raise ValueError('Meadow instance budget exceeded')
    return dict(rows=rows,instances=len(rows),candidateSamples=scans,maximumGrade=max((r['grade'] for r in rows),default=0),collision='NoCollision',authoritativeRouteWidthsPreserved=True,nativeIntegrated=False,appearanceApproved=False,performanceAccepted=False,combatCoverAccepted=False)
