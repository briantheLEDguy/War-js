"""Paint new shade-foliage PBR fields with physical vein relief and saved heights."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];FOLDER=ROOT/'textures/source';FOLDER.mkdir(exist_ok=True)
SIZE=1024

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def field(x,y,phase):
    return (np.sin(x*19.3+y*7.7+phase)+.53*np.sin(x*43.7-y*21.1+phase*1.7)+.27*np.sin(x*97.1+y*66.7+phase*.61))/1.8

def paint(name):
    y,x=np.mgrid[0:SIZE,0:SIZE].astype(np.float32);u=x/SIZE;v=1-y/SIZE
    tile=np.floor(u*4);across=(u*4-tile-.5)*2
    noise=field(u,v,2.3);fine=field(u*14,v*13,6.7)
    if name=='fern_stem':
        base=np.array([72,88,36],np.float32);tone=1+.09*noise+.035*fine
        color=base[None,None,:]*tone[:,:,None];height=.00002*(1+noise)+.000035*np.sin(u*47)**2
        roughness=.78+.05*noise;width=.045;span=.55;maximum=.0003
    else:
        fern=name=='fern_leaf';base=np.array([67,91,37] if fern else [74,90,39],np.float32)
        curved=across+.025*np.sin(v*17+tile)
        midrib=np.exp(-(curved/.025)**2)
        if fern:
            trace=(v*12.5-np.abs(curved)*2.8+.13*np.sin(v*23+tile))%1
            vein=np.exp(-((np.minimum(trace,1-trace))/.044)**2)*(.35+.65*np.abs(across))
        else:
            trace=(curved*8+.04*np.sin(v*31))%1;vein=np.exp(-(np.minimum(trace,1-trace)/.071)**2)
        tip=np.clip((v-(.86+.02*tile))/.11,0,1)*(tile==3)
        edge=np.clip((np.abs(across)-.72)/.22,0,1)
        tone=1+.085*noise+.028*fine+(tile-1.5)*.032-.045*edge
        color=base[None,None,:]*tone[:,:,None]
        color+=np.stack([midrib*13+vein*5,midrib*14+vein*7,midrib*5+vein*2],axis=-1)
        color=color*(1-tip[:,:,None]*.68)+np.array([116,88,45])[None,None,:]*tip[:,:,None]*.68
        height=.00014*midrib+.000045*vein+.000009*(1+fine)+.000018*(1+noise)
        roughness=.77+.035*noise+.035*edge+.05*tip;width=.047 if fern else .041;span=.17 if fern else .54;maximum=.0003
    height=np.clip(height,0,maximum)
    dx=np.gradient(height,axis=1)*SIZE/(width*4);dy=np.gradient(height,axis=0)*SIZE/span
    normal=np.stack([-dx,dy,np.ones_like(dx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    orm=np.stack([np.ones_like(x)*.98,np.clip(roughness,.64,.94),np.zeros_like(x)],axis=-1)
    maps={'baseColor':np.clip(color,0,255).astype(np.uint8),'normal':np.clip((normal*.5+.5)*255,0,255).astype(np.uint8),'orm':np.clip(orm*255,0,255).astype(np.uint8)}
    channels={}
    for channel,pixels in maps.items():
        p=FOLDER/f'{name}_{channel}.png';Image.fromarray(pixels,'RGB').save(p);channels[channel]={'file':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p),'resolution':SIZE}
    p=FOLDER/f'{name}_height.png';Image.fromarray(np.round(height/maximum*65535).astype(np.uint16)).save(p)
    return {'material':name,'channels':channels,'height':{'file':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p),'maximumM':maximum,'uSpanM':width*4,'vSpanM':span},'normalConvention':'OpenGL tangent RGB from (-dH/dx,+dH/dImageRow,1); PNG rows increase downward.'}

if __name__=='__main__':
    rows=[paint(name) for name in ['fern_stem','fern_leaf','wood_sedge']]
    (ROOT/'textures/paint-records.json').write_text(json.dumps({'toolSha256':sha(Path(__file__)),'materials':rows},indent=2)+'\n')
    print('Painted three original shade-foliage materials with retained metric heights.')
