"""Retained original surface strokes and physically scaled material channels."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1]; SIZE=1024
FISSURES=[[(0,151),(131,143),(217,170),(306,160),(417,179),(510,172),(646,192),(731,179),(861,208),(1024,192)],
          [(0,603),(149,590),(201,606),(309,592),(388,616),(460,608),(596,634),(681,622),(773,641),(889,629),(1024,650)],
          [(76,0),(90,104),(82,179),(104,269),(96,350)],[(863,1024),(845,929),(850,868),(824,782)]]
GRAIN=[[(31,0),(42,179),(25,361),(43,563),(30,745),(37,1024)],[(106,0),(96,134),(123,328),(110,544),(133,812),(113,1024)],
       [(208,0),(191,210),(218,434),(198,701),(225,1024)],[(305,0),(319,187),(291,468),(316,705),(301,1024)],
       [(413,0),(401,218),(429,399),(405,650),(437,1024)],[(521,0),(530,258),(512,489),(535,724),(514,1024)],
       [(624,0),(604,214),(633,458),(615,684),(646,1024)],[(739,0),(752,194),(733,395),(764,731),(740,1024)],
       [(857,0),(839,235),(866,436),(849,699),(874,1024)],[(962,0),(978,229),(947,484),(971,799),(952,1024)]]
PITS=[(62,87),(184,57),(295,139),(428,95),(617,142),(757,68),(896,156),(987,91),(115,313),(259,271),(368,345),(505,274),(675,341),(810,294),(945,386),
      (49,502),(203,467),(334,553),(494,490),(573,588),(738,476),(886,551),(983,466),(120,700),(277,759),(414,679),(597,741),(753,657),(929,740),
      (55,914),(208,863),(359,959),(495,888),(644,969),(785,889),(956,947)]


def paint(name,definition):
    base=definition['color']; kind=definition['kind']; rough=round(255*definition['roughness']); metal=round(255*definition.get('metallic',0))
    color=Image.new('RGB',(SIZE,SIZE),tuple(base)); height=Image.new('L',(SIZE,SIZE),128); roughness=Image.new('L',(SIZE,SIZE),rough)
    c=ImageDraw.Draw(color); h=ImageDraw.Draw(height); r=ImageDraw.Draw(roughness)
    tint=lambda delta:tuple(max(0,min(255,value+delta)) for value in base)
    if kind in ('stone','slate','lime'):
        for index,path in enumerate(FISSURES):
            for offset,width,delta in ((-23,35,-3),(0,13,-8),(14,7,5)):
                points=[(x,y+offset) for x,y in path]
                c.line(points,fill=tint(delta),width=width,joint='curve'); h.line(points,fill=128+delta,width=max(2,width//2),joint='curve')
            h.line(path,fill=99 if kind=='stone' else 112,width=2,joint='curve')
            r.line(path,fill=min(255,rough+13),width=9)
        for index,(x,y) in enumerate(PITS):
            size=2+index%4
            patch=[(x-size,y),(x-1,y-size),(x+size+2,y-1),(x+size,y+size),(x-2,y+size+1)]
            c.polygon(patch,fill=tint(-8-index%4));h.polygon(patch,fill=101+index%13);r.polygon(patch,fill=min(255,rough+8))
        if kind=='slate':
            for index in range(22):
                y=index*47
                line=[(0,y+8),(204,y),(377,y+9),(511,y+3),(703,y+12),(891,y+7),(1024,y+15)]
                c.line(line,fill=tint(-7 if index%3 else 9),width=3);h.line(line,fill=119 if index%3 else 138,width=2)
    elif kind=='wood':
        for path in GRAIN:
            for offset,width,delta in ((-29,2,-13),(-17,4,7),(-6,6,-10),(0,3,-22),(11,2,12),(25,4,-8),(39,1,8)):
                shifted=[(x+offset,y) for x,y in path]
                c.line(shifted,fill=tint(delta),width=width,joint='curve');h.line(shifted,fill=128+delta,width=max(1,width//2));r.line(shifted,fill=min(255,rough+abs(delta)//2),width=width)
        for x,y in ((271,388),(707,743)):
            outline=[(x,y-75),(x-24,y-38),(x-30,y+10),(x-16,y+47),(x,y+62),(x+20,y+35),(x+29,y-15),(x+16,y-58),(x,y-75)]
            c.line(outline,fill=tint(-19),width=4,joint='curve');h.line(outline,fill=111,width=3)
        for points in [[(76,0),(78,83),(65,117)],[(591,1024),(604,937),(598,869)],[(886,0),(879,61),(891,104)]]:
            c.line(points,fill=tint(-28),width=3);h.line(points,fill=81,width=2)
    elif kind=='metal':
        for index,(x,y) in enumerate(PITS):
            patch=[(x-10,y-4),(x-5,y-12),(x+9,y-8),(x+16,y+2),(x+4,y+11),(x-11,y+7)]
            h.polygon(patch,fill=122);r.polygon(patch,fill=min(255,rough+index%15))
            c.line([(x-8,y+7),(x+4,y+10),(x+13,y+2)],fill=tint(5),width=2)
        for points in [[(29,0),(31,106),(19,210)],[(988,824),(1001,913),(996,1024)]]:
            c.line(points,fill=tint(-14),width=23);r.line(points,fill=min(255,rough+45),width=28)
    elif kind=='cloth':
        for x in range(0,SIZE,6):c.line([(x,0),(x,SIZE)],fill=tint(4),width=1);h.line([(x,0),(x,SIZE)],fill=136,width=1)
        for y in range(0,SIZE,6):c.line([(0,y),(SIZE,y)],fill=tint(-5),width=1);h.line([(0,y),(SIZE,y)],fill=121,width=1)
        for x in (18,25,998,1005):c.line([(x,0),(x,SIZE)],fill=tint(13),width=2);h.line([(x,0),(x,SIZE)],fill=142,width=2)
    if definition.get('weather')=='ground_splash':
        patch=[(0,1024),(0,882),(79,894),(141,872),(195,900),(264,865),(331,893),(401,881),(467,913),(543,892),(607,866),(686,896),(755,883),(834,899),(899,874),(962,895),(1024,883),(1024,1024)]
        c.polygon(patch,fill=tint(-13));r.polygon(patch,fill=249)
        for index,(x,y) in enumerate(PITS[:18]):
            if index%2==0:c.line([(x,946),(x-5,899),(x+3,868)],fill=tint(-18),width=5)
    if definition.get('weather')=='soot':
        for offset in (27,289,591,804):
            c.line([(offset,0),(offset+17,178),(offset-7,371),(offset+22,558)],fill=tint(-28),width=45,joint='curve')
    # Tile joins share exactly matching color, roughness and relief instead of
    # introducing a false horizontal board seam whenever a long stave repeats.
    for layer in (color,height,roughness):
        pixels=np.asarray(layer,dtype=np.float32).copy()
        for axis in (0,1):
            for distance in range(16):
                a=[slice(None)]*pixels.ndim;b=list(a);a[axis]=distance;b[axis]=SIZE-1-distance
                weight=(1-distance/16)*.5;first=pixels[tuple(a)].copy();last=pixels[tuple(b)].copy()
                pixels[tuple(a)]=first*(1-weight)+last*weight;pixels[tuple(b)]=last*(1-weight)+first*weight
        layer.paste(Image.fromarray(np.round(pixels).astype('uint8')))
    # Micrometre-scaled height is a real separate surface channel, not color-derived lighting.
    field=np.asarray(height.filter(ImageFilter.GaussianBlur(.55)),dtype=np.float32)/255
    dx=(np.roll(field,-1,axis=1)-np.roll(field,1,axis=1))*.5;dy=(np.roll(field,-1,axis=0)-np.roll(field,1,axis=0))*.5
    strength={'stone':.005,'slate':.002,'wood':.002,'lime':.001,'metal':.0009,'cloth':.0007}[kind]*SIZE
    normal=np.dstack((-dx*strength,-dy*strength,np.ones_like(field)));normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    normal_image=Image.fromarray(np.round((normal*.5+.5)*255).clip(0,255).astype('uint8'),'RGB')
    cavity=np.clip(1-np.maximum(0,.5-field)*.38,0,1)
    orm=Image.fromarray(np.dstack((cavity*255,np.asarray(roughness),np.full_like(field,metal))).astype('uint8'),'RGB')
    output=ROOT/'textures/source';output.mkdir(exist_ok=True)
    images={'baseColor':color,'normal':normal_image,'orm':orm,'height':height,'roughness':roughness}
    for channel,image in images.items():image.save(output/f'{name}_{channel}.png',optimize=True)
    return {'material':name,'definition':definition,'height_scale_m':strength/SIZE,'channels':{channel:{'path':f'textures/source/{name}_{channel}.png','sha256':hashlib.sha256((output/f'{name}_{channel}.png').read_bytes()).hexdigest()} for channel in images},'occlusion_scope':'authored material cavity; no baked scene lighting'}


if __name__=='__main__':
    source=json.loads((ROOT/'source/architecture.json').read_text())
    records=[paint(name,definition) for name,definition in source['materials'].items()]
    (ROOT/'textures/paint_records.json').write_text(json.dumps({'strokes':{'fissures':FISSURES,'grain':GRAIN,'pits':PITS},'materials':records},indent=2)+'\n')
    print(f'Painted {len(records)} original 1024px PBR surface sets.')
