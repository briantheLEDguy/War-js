"""Measured four-region terrain atlas. Authoring diagrams, never native screenshots or acceptance."""
import json
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'artifacts/unreal/t1-redesign'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)


def render(bundle,identity,output):
    directory=ROOT/bundle['directory'];source=read(directory/(identity+'.json'));mesh=read(directory/(identity+'_terrain.json'))
    b=source['spatial']['bounds'];g=source['spatial']['terrainGrid'];nx,nz=g['segmentsX'],g['segmentsZ']
    vertices=np.asarray(mesh['positions']);ix=np.rint((vertices[:,1]/100-b['minX'])/(b['maxX']-b['minX'])*nx).astype(int)
    iz=np.rint((vertices[:,0]/100-b['minZ'])/(b['maxZ']-b['minZ'])*nz).astype(int)
    if len(vertices)!=(nx+1)*(nz+1) or np.any(ix<0) or np.any(iz<0) or np.any(ix>nx) or np.any(iz>nz):raise ValueError('Incomplete source grid')
    heights=np.zeros((nz+1,nx+1));heights[iz,ix]=vertices[:,2]/100
    dxz=(b['maxX']-b['minX'],b['maxZ']-b['minZ']);scale=min(1340/dxz[0],720/dxz[1]);w,h=round(dxz[0]*scale),round(dxz[1]*scale)
    left,top=(1500-w)//2,140+(720-h)//2
    panel=Image.new('RGB',(1500,1080),'#17252b');d=ImageDraw.Draw(panel)
    dz,dx=np.gradient(heights,dxz[1]/nz,dxz[0]/nx);light=np.clip((1-dx*.8-dz*.55)/np.sqrt(1+dx*dx+dz*dz)*.8+.2,.3,1.15)
    low=np.array(dict(sunmeadow_march=[110,137,85],cinderfen_outskirts=[100,104,77],brightfen_approach=[122,150,132],ashen_steppe=[155,143,119])[identity]);high=np.array([182,177,158])
    mix=np.clip(heights/130,0,1)[:,:,None];color=(low*(1-mix)+high*mix)*light[:,:,None]
    bands=np.floor(heights/10);edges=np.zeros_like(heights,dtype=bool);edges[1:,:]|=bands[1:,:]!=bands[:-1,:];edges[:,1:]|=bands[:,1:]!=bands[:,:-1];color[edges]*=.55
    if identity=='brightfen_approach':color[heights<0]=[54,100,114]
    terrain=Image.fromarray(np.flipud(np.clip(color,0,255).astype('uint8'))).resize((w,h),Image.Resampling.BILINEAR);panel.paste(terrain,(left,top))
    def p(row):return left+(row['x']-b['minX'])*scale,top+(b['maxZ']-row['z'])*scale
    d.line([p(r) for r in source['spatial']['playableOutline']]+[p(source['spatial']['playableOutline'][0])],fill='#eee5cf',width=3)
    colors=['#ffe1a1','#76d3e4','#76d3e4','#ed9ec8','#ed9ec8']
    for i,path in enumerate(source['paths']):d.line([p(v) for v in path['points']],fill='#dfb170' if '_western_spur_counter_' in path['id'] else colors[i] if i<5 else '#b5b3a7',width=5 if i<3 else 3)
    tactical=[path for path in source['paths'] if '_western_spur_counter_' in path['id']]
    climbs=[c for c in source['orvrLayout']['terrain']['clearCorridors'] if c['id'].endswith('_climb') and '_scarp_' in c['id']]
    for climb in climbs:d.line([p(v) for v in climb['points']],fill='#b8db89',width=4)
    def mark(row,label,color,r=8,offset=(12,-25)):
        x,y=p(row);d.ellipse((x-r,y-r,x+r,y+r),fill=color,outline='#f5ebd5',width=2)
        d.text((x+offset[0],y+offset[1]),label,font=font(18),fill='#fff3d5',stroke_width=2,stroke_fill='#17252b')
    if climbs:mark(climbs[0]['points'][-1],'Overlook / 2 back climbs','#92b267',6,(-40,-74))
    if tactical:mark(tactical[0]['points'][-1],'Spur / 2 contour counters','#dfb170',6,(-110,31))
    for i,bo in enumerate(source['orvrLayout']['battlefieldObjectives']):mark(bo,'BO '+str(i+1),'#cfb069',offset=(-25,17 if i!=1 else -45))
    for keep in source['orvrLayout']['keeps']:mark(keep,keep['realm'].capitalize()+' keep','#365f85' if keep['realm']=='aegis' else '#943f4a',12,(-65,-35))
    for camp in source['orvrLayout']['stagingCamps']:mark(camp,'Staging','#313f43',6,(-35,-27))
    for i,path in enumerate(source['paths'][3:5]):mark(path['points'][1],'R'+str(i+1),'#cb82b0',5,(8,-23))
    mark(source['spawnPoint'],'Village + court','#84c7a1',11,(-60,17))
    for t in source['zoneTriggers']:
        if t['targetZoneId'] in ('wardens_hollow','cindermaw_pit','mireglass_den','ashfang_pit'):mark(t,'Optional lair','#a596bf',7,(-85,-30))
    pockets=read(directory/(identity+'_pockets.json')) if (directory/(identity+'_pockets.json')).exists() else []
    for q in pockets:mark(q,q['label']+(' (water)' if q['cosmeticWater'] else ' (dry)'), '#579ab2' if q['cosmeticWater'] else '#867965',5,(-25,15))
    d.text((45,22),source['name']+' - measured landscape study',font=font(34),fill='#f1e6d0')
    d.text((45,75),'AUTHORING DIAGRAM | 10m contours | source '+bundle['signature'][:12]+' | appearance and combat unapproved',font=font(20),fill='#c8cec4')
    d.text((45,891),'Gold: advance   Cyan: vehicle flanks   Pink: rotations R1/R2   Pale outline: playable ground',font=font(21),fill='#f1e6d0')
    d.text((45,932),'Two keeps, three objectives, two staging camps, six supply itineraries. Lime: scarp climbs. Amber: contour counters.',font=font(21),fill='#c8cec4')
    d.text((45,973),'First-pair views are separate native renders. Brightfen/Ashen are source studies; native environments are pending.',font=font(19),fill='#c8cec4')
    d.text((45,1017),'No underground environment, vehicle/18v18, human visual, lair, platform, Steam or release acceptance is implied.',font=font(18),fill='#c8cec4')
    target=output/(identity+'_landscape.png');panel.save(target);return target


if __name__=='__main__':
    bundles=[read(BASE/'battlefield-source-latest.json'),read(BASE/'second-pair-source-latest.json')]
    signature=hashlib.sha256(''.join(b['signature'] for b in bundles).encode()+Path(__file__).read_bytes()).hexdigest()[:12];output=BASE/'landscape-atlas'/signature;output.mkdir(parents=True,exist_ok=True)
    for bundle,identities in zip(bundles,[['sunmeadow_march','cinderfen_outskirts'],['brightfen_approach','ashen_steppe']]):
        for identity in identities:print(render(bundle,identity,output))
