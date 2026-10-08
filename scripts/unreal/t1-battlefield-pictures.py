"""Measured terrain/route drawings. These are authoring diagrams, not Unreal screenshots."""
import json
import math
from pathlib import Path
import sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).parent))
from t1_battlefield import Surface
ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/'artifacts/unreal/t1-redesign'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
font=lambda size:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',size)


def render(bundle,identity):
    directory=ROOT/bundle['directory']; source=read(directory/(identity+'.json')); surface=Surface(source,read(directory/(identity+'_terrain.json')))
    image=Image.new('RGB',(1500,1130),'#172227'); draw=ImageDraw.Draw(image); b=surface.bounds
    panel=(50,115,1450,835); w,h=panel[2]-panel[0],panel[3]-panel[1]
    def p(row): return (50+(row['x']-b['minX'])/(b['maxX']-b['minX'])*w,115+(b['maxZ']-row['z'])/(b['maxZ']-b['minZ'])*h)
    heights=np.array(surface.heights).reshape((surface.nz+1,surface.nx+1))/100
    dz,dx=np.gradient(heights,(b['maxZ']-b['minZ'])/surface.nz,(b['maxX']-b['minX'])/surface.nx)
    light=np.clip((1-dx*.9-dz*.6)/np.sqrt(1+dx*dx+dz*dz)*.75+.28,.25,1.15)
    tint=np.array([128,143,94] if identity=='sunmeadow_march' else [128,108,79]); high=np.array([194,188,154] if identity=='sunmeadow_march' else [108,110,111])
    mix=np.clip(heights/120,0,1)[:,:,None]; color=(tint*(1-mix)+high*mix)*light[:,:,None]
    levels=np.floor(heights/10); edges=np.zeros_like(heights,dtype=bool)
    edges[1:,:]|=levels[1:,:]!=levels[:-1,:]; edges[:,1:]|=levels[:,1:]!=levels[:,:-1]
    color[edges]*=.62
    terrain=Image.fromarray(np.flipud(np.clip(color,0,255).astype('uint8'))).resize((w,h),Image.Resampling.BILINEAR)
    image.paste(terrain,(50,115)); draw.line([p(r) for r in source['spatial']['playableOutline']]+[p(source['spatial']['playableOutline'][0])],fill='#f0e0bd',width=3)
    colors=['#ffe5a1','#79d3e5','#79d3e5','#e8a2d5','#e8a2d5']
    for i,path in enumerate(source['paths']): draw.line([p(r) for r in path['points']],fill=colors[i] if i<5 else '#bbb9aa',width=5 if i<3 else 3,joint='curve')
    for link in read(directory/(identity+'_links.json')):
        for a,bb in zip(link['points'],link['points'][1:]):
            aa,cc=p(a),p(bb); n=max(1,round(math.dist(aa,cc)/12))
            for i in range(0,n,2): draw.line([(aa[0]+(cc[0]-aa[0])*t/n,aa[1]+(cc[1]-aa[1])*t/n) for t in (i,min(i+1,n))],fill='#a8f1bb',width=4)
    def mark(row,label,fill,r=9,offset=(12,-24)):
        x,y=p(row); draw.ellipse((x-r,y-r,x+r,y+r),fill=fill,outline='#eee8d3',width=2)
        draw.text((x+offset[0],y+offset[1]),label,font=font(17),fill='#fff7df',stroke_width=2,stroke_fill='#172227')
    for i,bo in enumerate(source['orvrLayout']['battlefieldObjectives']): mark(bo,f"{i+1}: {['open battle space','saddle / reveal','counterpush meadow'][i]} ({bo['y']} m)",'#c6a055',offset=(-145,20) if i==2 else (-100,-38 if i==0 else -62))
    for keep in source['orvrLayout']['keeps']: mark(keep,keep['realm'].capitalize()+' keep','#244e7b' if keep['realm']=='aegis' else '#842c38',r=12)
    for camp in source['orvrLayout']['stagingCamps']: mark(camp,'Staging','#343b3b',r=6,offset=(-55,-29))
    mark(source['spawnPoint'],'Village / arrival','#8cd8ba',r=13,offset=(-95,22))
    lair=next(t for t in source['zoneTriggers'] if t['targetZoneId'] in ('wardens_hollow','cindermaw_pit')); mark(lair,'Optional lair branch','#897f9e',r=7)
    draw.text((45,23),source['name']+' — connected battlefield terrain',font=font(34),fill='#eee8d3')
    draw.text((45,75),'AUTHORING PROTOTYPE · measured heightfield · 10 m contours · no appearance or gameplay acceptance',font=font(19),fill='#c8cbbc')
    draw.text((50,851),'Gold: advance   Cyan: vehicle flanks   Pink: rotations   Green dashes: unpainted off-road links',font=font(19),fill='#eee8d3')
    chart=(85,920,1430,1050); draw.line([(chart[0],chart[1]),(chart[0],chart[3]),(chart[2],chart[3])],fill='#889693',width=2)
    for i,path in enumerate(source['paths'][:3]):
        samples=[]; distance=0
        for a,bb in zip(path['points'],path['points'][1:]):
            length=math.hypot(bb['x']-a['x'],bb['z']-a['z']); count=math.ceil(length/3)
            for n in range(count+1):
                x=a['x']+(bb['x']-a['x'])*n/count; z=a['z']+(bb['z']-a['z'])*n/count
                samples.append((distance+length*n/count,surface.height_cm(x,z)/100))
            distance+=length
        draw.line([(chart[0]+d/distance*(chart[2]-chart[0]),chart[3]-y/55*(chart[3]-chart[1])) for d,y in samples],fill=colors[i],width=3)
    draw.text((50,892),'Elevation profiles along each complete route (normalised travel distance)',font=font(18),fill='#c8cbbc')
    draw.text((30,chart[1]-10),'55 m',font=font(16),fill='#c8cbbc'); draw.text((35,chart[3]-12),'0 m',font=font(16),fill='#c8cbbc')
    draw.text((50,1080),'Off-road grading, source/native correspondence and human walk/drive/18v18 reviews remain separate checks.',font=font(18),fill='#c8cbbc')
    file=directory/(identity+'_battlefield_plan.png'); image.save(file); return str(file)


if __name__=='__main__':
    bundle=read(BASE/'battlefield-source-latest.json')
    for zone in ('sunmeadow_march','cinderfen_outskirts'): print(render(bundle,zone))
