"""Deterministic cosmetic ecology and bounded, terrain-clipped shallow water geometry."""
from t1_battlefield import terrain_sampling_bounds
import hashlib
import json
import math
from world_static import read_glb, combine_parts

MODELS = dict(sunmeadow_march='frontier_sunmeadow_meadow_lod0.glb',cinderfen_outskirts='frontier_cinderfen_sedge_horsetail_lod0.glb')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def admitted_cover(root, identity):
    if identity not in MODELS: raise ValueError('No reviewed regional cover')
    registry=root/'public/assets/models/asset-index.json'; model=MODELS[identity]; source=root/'public/assets/models'/model
    rows=json.loads(registry.read_text())['staticProps'].values(); fingerprint=sha(source)
    if not any(r.get('model')==model and r.get('runtimeReady') is True and r.get('approvalState')=='approved' and r.get('modelSha256')==fingerprint for r in rows):
        raise ValueError('Ground cover source is not currently admitted')
    data=combine_parts(read_glb(source)['parts']); inputs={p.relative_to(root).as_posix():sha(p) for p in (registry,source)}
    for material in data['materials']:
        for channel in material.get('textures',{}).values():
            if sha(root/channel['path'])!=channel['sha256']: raise ValueError('Ground cover channel changed')
            inputs[channel['path']]=channel['sha256']
    return data,inputs


def segment_distance(p,a,b):
    dx,dz=b['x']-a['x'],b['z']-a['z']; length=dx*dx+dz*dz
    if length<=0: return math.hypot(p['x']-a['x'],p['z']-a['z'])
    t=max(0,min(1,((p['x']-a['x'])*dx+(p['z']-a['z'])*dz)/length))
    return math.hypot(p['x']-a['x']-t*dx,p['z']-a['z']-t*dz)


def inside(p,outline):
    result=False
    for a,b in zip(outline,outline[1:]+outline[:1]):
        if (a['z']>p['z'])!=(b['z']>p['z']) and p['x']<(b['x']-a['x'])*(p['z']-a['z'])/(b['z']-a['z'])+a['x']: result=not result
    return result and min(segment_distance(p,a,b) for a,b in zip(outline,outline[1:]+outline[:1]))>4


def random_unit(x,z,salt):
    value=math.sin(x*127.1+z*311.7+salt*74.7)*43758.5453123
    return value-math.floor(value)


def cover_layout(source, height_cm, pockets):
    if source['id'] not in MODELS: raise ValueError('No admitted cover region')
    b=terrain_sampling_bounds(source['spatial']); outline=source['spatial']['playableOutline']; terrain=source['orvrLayout']['terrain']; result=[]
    anchors=[*source.get('npcs',[]),*source.get('enemies',[]),*source.get('resourceNodes',[]),*source.get('craftingStations',[]),*source.get('zoneTriggers',[])]
    # The high-detail source clumps use bounded density and 120m native culling; no collision or harvest behavior.
    spacing=11 if source['id']=='sunmeadow_march' else 12
    for ix in range(math.ceil(b['minX']/spacing),math.floor(b['maxX']/spacing)):
        for iz in range(math.ceil(b['minZ']/spacing),math.floor(b['maxZ']/spacing)):
            x=(ix+.15+.7*random_unit(ix,iz,1))*spacing; z=(iz+.15+.7*random_unit(ix,iz,2))*spacing; p=dict(x=x,z=z)
            if not inside(p,outline): continue
            near=min((math.hypot(x-q['x'],z-q['z'])-q['radius'] for q in pockets),default=1000)
            clump=(math.sin(x/24+math.sin(z/38))*.5+math.cos(z/31-x/79)*.5+2)/4
            if random_unit(ix,iz,3)>min(.92,.15+clump*.7+(.16 if near<30 else 0)): continue
            if any(segment_distance(p,a,c)<road['width']/2+2 for road in source['paths'] for a,c in zip(road['points'],road['points'][1:])): continue
            if any(a.get('preserveFooting') and '_pocket_' not in a['id'] and math.hypot(x-a['x'],z-a['z'])<a['radius']+5 for a in terrain['flattenAreas']): continue
            if any(math.hypot(x-a['x'],z-a['z'])<10 for a in anchors): continue
            y=height_cm(x,z)
            if any(q['cosmeticWater'] and math.hypot(x-q['x'],z-q['z'])<q['radius']+60 and y<q['waterY']*100+4 for q in pockets): continue
            gx=(height_cm(x+1,z)-height_cm(x-1,z))/200; gz=(height_cm(x,z+1)-height_cm(x,z-1))/200
            if math.hypot(gx,gz)>.4: continue
            scale=.48+random_unit(ix,iz,4)*.38
            result.append(dict(location=[z*100,x*100,y-2],yaw=random_unit(ix,iz,5)*360,scale=scale))
    for pocket_index,pocket in enumerate(pockets):
        for ix in range(-18,19):
            for iz in range(-18,19):
                salt=71+pocket_index*13
                x=pocket['x']+(ix+.6*random_unit(ix,iz,salt))*2.8;z=pocket['z']+(iz+.6*random_unit(ix,iz,salt+1))*2.8;p=dict(x=x,z=z)
                if math.hypot(x-pocket['x'],z-pocket['z'])>pocket['radius']+45 or not inside(p,outline):continue
                y=height_cm(x,z);relative=y/100-(pocket['waterY'] if pocket['cosmeticWater'] else pocket['bedY'])
                if not (.02 if pocket['cosmeticWater'] else .1)<relative<1.5:continue
                if random_unit(ix,iz,salt+2)>(math.sin(x/8+math.cos(z/13))+math.cos(z/10)+2)/4:continue
                if any(segment_distance(p,a,c)<road['width']/2+2 for road in source['paths'] for a,c in zip(road['points'],road['points'][1:])):continue
                if any(segment_distance(p,a,c)<3.5 for a,c in zip(pocket['approach'],pocket['approach'][1:])):continue
                if any(math.hypot(x-a['x'],z-a['z'])<10 for a in anchors):continue
                if any(a.get('preserveFooting') and '_pocket_' not in a['id'] and math.hypot(x-a['x'],z-a['z'])<a['radius']+5 for a in terrain['flattenAreas']):continue
                gx=(height_cm(x+1,z)-height_cm(x-1,z))/200;gz=(height_cm(x,z+1)-height_cm(x,z-1))/200
                if math.hypot(gx,gz)>.4:continue
                scale=.42+random_unit(ix,iz,salt+3)*.44
                result.append(dict(location=[z*100,x*100,y-2],yaw=random_unit(ix,iz,salt+4)*360,scale=scale))
    if not result or len(result)>12000: raise ValueError('Ground cover exceeds native batch bounds or is empty')
    return result


def pocket_water(pocket,height_cm):
    if not pocket['cosmeticWater']: raise ValueError('Dry exploration hollow has no admitted water')
    x,z,y=pocket['x'],pocket['z'],pocket['waterY']*100; positions=[[z*100,x*100,y]]
    for i in range(96):
        angle=i*math.tau/96
        shoreline=next((r*.5 for r in range(2,2*int(pocket['radius']+60)+1) if height_cm(x+math.cos(angle)*r*.5,z+math.sin(angle)*r*.5)>y+3),None)
        if shoreline is None: raise ValueError('Water surface needs a closed terrain shoreline: '+pocket['id'])
        radius=shoreline+1
        positions.append([(z+math.sin(angle)*radius)*100,(x+math.cos(angle)*radius)*100,y])
    # Native front faces use clockwise winding, with explicit upward normals.
    indices=[v for i in range(96) for v in (0,1+i,1+(i+1)%96)]
    return dict(positions=positions,indices=indices,normals=[[0,0,1]]*len(positions),uvs=[[p[0]/100,p[1]/100] for p in positions])
