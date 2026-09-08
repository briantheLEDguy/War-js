"""Original botanical pigment/relief fields, saved as inspectable PNG channels.

Pixels use Pillow's top-down rows. The exported tangent normal therefore uses
(-dH/dx,+dH/dy,+1), where increasing Blender V points toward decreasing rows.
"""
import hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1];SIDE=1024
SOURCE=json.loads((ROOT/'source/nature.json').read_text())
FISSURES=[[(39,0),(30,98),(48,180),(36,284),(47,360)],[(157,160),(143,296),(158,413),(133,539),(148,644)],[(259,0),(273,131),(255,264),(269,384),(253,462)],[(384,441),(369,548),(385,684),(361,781),(376,921),(365,1024)],[(501,0),(485,129),(505,237),(487,359),(504,492),(483,574)],[(612,239),(594,385),(610,539),(589,662),(607,738)],[(745,0),(730,109),(749,224),(737,356),(756,466)],[(829,487),(813,640),(836,757),(819,896),(830,1024)],[(957,97),(939,229),(959,337),(938,478),(951,601),(936,744)]]
ROCK_CLEFTS=[[(0,331),(154,318),(279,383),(411,365),(553,401),(692,382),(832,440),(1024,417)],[(76,0),(95,137),(74,258),(102,380),(83,513)],[(622,1024),(603,875),(629,722),(612,564),(639,396)],[(0,783),(181,799),(308,745),(477,777),(622,743),(793,792),(1024,761)]]

def wash(seed,scales):
    rng=np.random.default_rng(seed);result=np.zeros((SIDE,SIDE),np.float32)
    for w,h,weight in scales:
        grid=np.round(rng.uniform(0,255,(h,w))).astype('uint8')
        result+=(np.asarray(Image.fromarray(grid).resize((SIDE,SIDE),Image.Resampling.BICUBIC),dtype=np.float32)/127.5-1)*weight
    return result

def paint(name,definition):
    kind=definition['kind'];base=np.array(definition['color']);rough=round(definition['roughness']*255)
    yy,xx=np.mgrid[0:SIDE,0:SIDE].astype(np.float32)
    field=wash(2819+list(SOURCE['materials']).index(name)*83,[(13,17,.6),(69,83,.24),(239,251,.1)])
    pigment=base[None,None,:]+field[...,None]*22;relief=128+field*11;roughness=rough+field*12
    if kind=='bark':
        longitudinal=wash(6847,[(25,6,.7),(113,29,.3),(369,97,.14)])
        pigment+=longitudinal[...,None]*25;relief+=longitudinal*25
        darkwash=np.maximum(0,field-.04)*18;pigment-=darkwash[...,None]
    elif kind in ('stem','reed_leaf','sedge_leaf','horsetail'):
        fibres=wash(7619,[(153,4,.55),(377,23,.25)])
        pigment+=fibres[...,None]*26;relief+=fibres*14
        if kind in ('reed_leaf','sedge_leaf'):
            # Tips lose chlorophyll first; lower blades retain muted olive.
            tip=np.maximum(0,.44-yy/SIDE)/.44
            pigment+=tip[...,None]*np.array([28,-3,-14])
    elif kind in ('rock','mineral'):
        grit=wash(8713,[(89,111,.5),(353,397,.35),(877,823,.12)])
        pigment+=grit[...,None]*11;relief+=grit*28;roughness+=grit*18
        iron=np.maximum(0,wash(9263,[(7,9,.7),(37,51,.2)])-.1)
        pigment+=iron[...,None]*np.array([37,13,-4])
    albedo=Image.fromarray(np.round(pigment).clip(0,255).astype('uint8'))
    height=Image.fromarray(np.round(relief).clip(0,255).astype('uint8'))
    rough_image=Image.fromarray(np.round(roughness).clip(0,255).astype('uint8'))
    c,h,r=ImageDraw.Draw(albedo),ImageDraw.Draw(height),ImageDraw.Draw(rough_image)
    tint=lambda delta:tuple(np.clip(base+delta,0,255).astype(int))
    if kind=='bark':
        for i,line in enumerate(FISSURES):
            for shift in (-21,0,19):
                points=[(x+shift,y) for x,y in line]
                c.line(points,fill=tint(-21 if shift==0 else 6),width=3 if shift==0 else 2,joint='curve');h.line(points,fill=83 if shift==0 else 151,width=3,joint='curve')
            for j in range(1,len(line)-1):
                x,y=line[j];hook=[(x,y),(x-17,y+21),(x-23,y+54)]
                c.line(hook,fill=tint(-14),width=2);h.line(hook,fill=102,width=2)
        for i in range(61):
            x=(i*163+29)%SIDE;y=(i*271+73)%SIDE;s=5+i%8
            points=[(x-s,y),(x-s//2,y-s),(x+s//2,y-s+3),(x+s,y+2),(x+2,y+s),(x-s+2,y+s//2)]
            c.polygon(points,fill=(94+i%11,99+i%9,78+i%7));h.polygon(points,fill=135+i%7);r.polygon(points,fill=231)
    elif kind=='alder_leaf':
        # Four painted autumn leaves share one field; midribs and curved
        # secondary veins map to the actual rounded, notched blade silhouette.
        for tile,color in enumerate([(103,109,49),(121,101,47),(83,104,50),(136,91,44)]):
            x0=tile*256;local=field[:,x0:x0+256]
            tile_pixels=np.array(color)[None,None,:]+local[...,None]*21
            edge=np.abs(np.arange(256)-127.5)/127.5
            tile_pixels-=edge[None,:,None]**4*np.array([12,10,7])
            albedo.paste(Image.fromarray(np.round(tile_pixels).clip(0,255).astype('uint8')),(x0,0))
        c=ImageDraw.Draw(albedo)
        for tile in range(4):
            centre=tile*256+128
            c.line([(centre,1023),(centre-1,689),(centre+2,338),(centre,0)],fill=(156,147,72),width=4);h.line([(centre,1023),(centre,0)],fill=153,width=4)
            for row in range(8):
                y=922-row*110
                for sign in (-1,1):
                    line=[(centre,y),(centre+sign*25,y-23),(centre+sign*56,y-67),(centre+sign*100,y-99)]
                    c.line(line,fill=(138,130,65),width=2,joint='curve');h.line(line,fill=144,width=2,joint='curve')
                    for branch in range(1,3):
                        x=centre+sign*(23+branch*24);z=y-branch*24
                        h.line([(x,z),(x+sign*19,z-34)],fill=137,width=1)
            for speck in range(24):
                x=tile*256+(speck*83+31)%250;y=(speck*137+tile*109)%1000;s=1+speck%3
                c.ellipse((x-s,y-s,x+s,y+s),fill=(79+tile*8,66,35));h.ellipse((x-s,y-s,x+s,y+s),fill=118)
    elif kind in ('stem','reed_leaf','sedge_leaf','horsetail'):
        for i in range(81):
            x=i*13+3;line=[(x,0),(x+2,239),(x-1,502),(x+2,759),(x,1024)]
            c.line(line,fill=tint(5 if i%3 else -8),width=1);h.line(line,fill=139 if i%3 else 120,width=1)
        if kind in ('reed_leaf','sedge_leaf'):
            c.line([(510,1024),(514,631),(510,292),(512,0)],fill=tint(21),width=8 if kind=='reed_leaf' else 5);h.line([(512,1024),(512,0)],fill=151,width=6)
            for i in range(17):
                x=(i*127+83)%1024;y=(i*193+37)%1024
                c.line([(x,y),(x+3,y+17),(x-2,y+36)],fill=tint(-21),width=2);h.line([(x,y),(x+3,y+33)],fill=111,width=2)
        else:
            for y in (173,511,849):
                c.line([(0,y),(221,y-3),(514,y+2),(773,y-2),(1024,y)],fill=tint(-23),width=9);h.line([(0,y),(1024,y)],fill=158,width=6)
    elif kind=='seed':
        for row in range(19):
            for col in range(17):
                x=col*65+(row%2)*31;y=row*59;points=[(x,y+26),(x-19,y+1),(x-11,y-21),(x+4,y-27),(x+21,y-3)]
                c.polygon(points,fill=tint((row+col)%5*3-8));h.polygon(points,fill=136+(row+col)%4*3)
                c.line(points+[points[0]],fill=tint(-15),width=2);h.line(points+[points[0]],fill=109,width=2)
    elif kind in ('rock','mineral'):
        for line in ROCK_CLEFTS:
            c.line(line,fill=tint(-12),width=3,joint='curve');h.line(line,fill=89,width=3,joint='curve');r.line(line,fill=239,width=5)
            c.line([(x+3,y-2) for x,y in line],fill=tint(8),width=2,joint='curve')
        for i in range(310):
            x=(i*239+47)%SIDE;y=(i*419+89)%SIDE;s=1+i%3
            outline=[(x-s,y-1),(x,y-s-1),(x+s,y),(x+1,y+s),(x-s,y+1)]
            c.polygon(outline,fill=tint(-10-i%8));h.polygon(outline,fill=92+i%17)
    height_array=np.asarray(height,dtype=np.float32)/255
    dy,dx=np.gradient(height_array);strength=2.5 if kind in ('bark','rock','mineral') else 1.1
    normals=np.stack((-dx*strength,dy*strength,np.ones_like(dx)),axis=-1);normals/=np.linalg.norm(normals,axis=-1)[...,None]
    normal=Image.fromarray(np.round((normals*.5+.5)*255).clip(0,255).astype('uint8'))
    ao=np.clip(244+np.minimum(0,height_array-.5)*44,218,255).astype('uint8')
    orm=Image.fromarray(np.stack((ao,np.asarray(rough_image),np.zeros_like(ao)),axis=-1))
    result={}
    for channel,image in [('baseColor',albedo),('normal',normal),('orm',orm),('height',height)]:
        path=ROOT/'textures/source'/f'{name}_{channel}.png';image.save(path);result[channel]={'file':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    return {'material':name,'channels':result,'normalConvention':'Pillow top-down: tangent RGB encodes normalized (-dH/dx,+dH/dy,+1)','signedGradientMaxError':float(np.max(np.abs(np.asarray(normal,dtype=np.float32)/255-(normals*.5+.5))))}

if __name__=='__main__':
    records=[paint(name,value) for name,value in SOURCE['materials'].items()]
    (ROOT/'textures/paint-records.json').write_text(json.dumps({'resolution':SIDE,'painterSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'records':records},indent=2)+'\n')
    print('PAINTED',len(records),'original material fields',flush=True)
