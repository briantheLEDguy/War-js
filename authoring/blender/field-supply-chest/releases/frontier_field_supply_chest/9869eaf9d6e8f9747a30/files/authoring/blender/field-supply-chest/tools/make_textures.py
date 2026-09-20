"""Original oak, forged iron, brass and grip leather fields, retained as PBR PNGs."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
SIZE=1024
rng=np.random.default_rng(2092026)
y,x=np.mgrid[0:SIZE,0:SIZE]/SIZE

def noise(n):
    im=Image.fromarray(np.uint8(rng.random((n,n))*255))
    im=Image.fromarray(np.tile(np.asarray(im),(3,3))).resize((SIZE*3,SIZE*3),Image.Resampling.BICUBIC)
    return np.asarray(im.crop((SIZE,SIZE,SIZE*2,SIZE*2)),dtype=float)/255

def fields(name):
    broad,medium,fine=noise(14),noise(77),noise(420)
    if name=='oak':
        grain=np.sin(x*340+np.sin(y*19+broad*2)*2.8+broad*7)
        pores=np.maximum(0,grain-.5)**1.5
        color=np.array([.43,.28,.135])[None,None,:]*(.74+broad[:,:,None]*.54)
        color-=pores[:,:,None]*np.array([.10,.07,.035])
        color+=(np.maximum(0,medium-.67)*.12)[:,:,None]
        height=broad*.13-pores*.13+fine*.022;rough=.73+medium*.17;metal=0
    elif name=='iron':
        oxide=np.maximum(0,medium-.72)
        color=np.array([.15,.17,.18])[None,None,:]*(.75+broad[:,:,None]*.35)
        color+=oxide[:,:,None]*np.array([.20,.055,.008])
        height=medium*.045+fine*.035;rough=.45+broad*.22;metal=.85
    elif name=='brass':
        color=np.array([.55,.36,.13])[None,None,:]*(.74+broad[:,:,None]*.3)
        height=fine*.015+medium*.03;rough=.38+medium*.18;metal=.9
    else:
        color=np.array([.16,.075,.036])[None,None,:]*(.76+broad[:,:,None]*.45)
        height=medium*.07+fine*.09;rough=.72+medium*.15;metal=0
    dy,dx=np.gradient(height);normal=np.stack((-dx*10,-dy*10,np.ones_like(x)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    return {'basecolor':color,'normal':normal*.5+.5,
            'orm':np.stack((np.ones_like(x),rough,np.full_like(x,metal)),axis=-1)}

if __name__=='__main__':
    receipts={}
    for name in ('oak','iron','brass','leather'):
        for channel,pixels in fields(name).items():
            image=Image.fromarray(np.uint8(np.clip(pixels,0,1)*255))
            for lod,size in enumerate((1024,512,256)):
                target=ROOT/'textures'/f'{name}_lod{lod}_{channel}.png'
                image.resize((size,size),Image.Resampling.LANCZOS).save(target)
                receipts[str(target.relative_to(ROOT)).replace('\\','/')]={'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'size':size}
    (ROOT/'textures/sources.json').write_text(json.dumps({'generatorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'seed':2092026,'textures':receipts},indent=2)+'\n')
    print('TEXTURES_SAVED',len(receipts))
