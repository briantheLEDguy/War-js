"""Original material fields and schematic campaign-map drawing, no external art."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
SIZE=2048
rng=np.random.default_rng(2092071)
y,x=np.mgrid[0:SIZE,0:SIZE]/SIZE

def noise(n):
    # The timber and leather charts intentionally repeat; interpolate through a
    # tiled neighbour field so a UV wrap cannot draw a rectangular colour patch.
    samples=np.uint8(rng.random((n,n))*255)
    im=Image.fromarray(np.tile(samples,(3,3))).resize((SIZE*3,SIZE*3),Image.Resampling.BICUBIC)
    return np.asarray(im.crop((SIZE,SIZE,SIZE*2,SIZE*2)),dtype=float)/255

def map_art(image):
    image=image.resize((2048,1146),Image.Resampling.LANCZOS)
    raw=ImageDraw.Draw(image)
    class ChartDraw:
        """Place chart geometry on its actual paper aspect; keep lettering square."""
        def __getattr__(self,name):
            def call(coords,*args,**kwargs):
                if isinstance(coords[0],(tuple,list)):
                    coords=[(p[0],p[1]*1146/2048) for p in coords]
                else:coords=tuple(v*(1146/2048 if i%2 else 1) for i,v in enumerate(coords))
                return getattr(raw,name)(coords,*args,**kwargs)
            return call
    d=ChartDraw();ink=(58,54,37);faded=(98,84,52);water=(69,107,109)
    fontPath=Path('C:/Windows/Fonts/georgia.ttf')
    title=ImageFont.truetype(str(fontPath),42);label=ImageFont.truetype(str(fontPath),22)
    small=ImageFont.truetype(str(fontPath),17)
    d.rounded_rectangle((60,68,1988,1980),radius=12,outline=ink,width=4)
    d.rectangle((76,84,1972,1964),outline=faded,width=2)
    d.text((1024,133),'THE DIVIDED FRONTIER',font=title,fill=ink,anchor='mm')
    d.text((1024,192),'Aegis Accord  /  Riftbound Host',font=label,fill=faded,anchor='mm')
    # Coast and river are original field-cartographer marks, not a gameplay minimap.
    coast=[]
    for i in range(121):
        yy=310+i*12;xx=1005+135*math.sin(i*.082)+42*math.sin(i*.35)
        coast.append((xx,yy))
    d.line(coast,fill=water,width=7)
    d.line([(a+14,b) for a,b in coast],fill=(141,158,142),width=2)
    for sign in(-1,1):
        for index in range(3):
            base=430+index*365
            points=[(coast[min(120,round((base-310)/12))][0],base)]
            points += [(1005+sign*j*20+32*math.sin(j*.48+index),base-j*5+25*math.sin(j*.7)) for j in range(1,27)]
            d.line(points,fill=water,width=3)
    # Contour hatching, woods and stepped original mountain silhouettes.
    for cx,cy,rx,ry in[(350,390,215,130),(1520,410,270,150),(1590,1530,240,190),(390,1580,250,140)]:
        for ring in range(4):
            pts=[]
            for j in range(101):
                a=j*math.tau/100;r=1-ring*.16
                pts.append((cx+math.cos(a)*(rx*r+9*math.sin(a*5)),cy+math.sin(a)*(ry*r+8*math.cos(a*4))))
            d.line(pts,fill=(159,145,106),width=2)
    for j in range(25):
        cx=1290+(j%8)*61;cy=340+(j//8)*56+14*math.sin(j*1.7)
        d.line([(cx-25,cy+24),(cx,cy-25),(cx+27,cy+24)],fill=faded,width=3)
        d.line([(cx,cy-25),(cx+2,cy+13),(cx+16,cy+24)],fill=faded,width=2)
    for j in range(45):
        cx=220+(j%9)*45;cy=1330+(j//9)*38
        d.line([(cx,cy+14),(cx,cy-16)],fill=(94,112,67),width=2)
        d.line([(cx-10,cy+5),(cx,cy-12),(cx+10,cy+5)],fill=(94,112,67),width=3)
    # Original campaign labels, connected schematically in original central order.
    sites=[('BASTION OF AEGIS',250,970,'a'),('STARFALL GATE',455,935,'a'),
      ('AEGIS CROWNWORKS',660,900,'a'),('DAWNLINE EXPANSE',865,930,'a'),
      ('SHATTERLINE EXPANSE',1130,990,'r'),('RIFT CROWNWORKS',1360,955,'r'),
      ('VOIDGATE FORTRESS',1585,920,'r'),('RIFTSPIRE CITADEL',1800,970,'r')]
    d.line([(sx,sy) for _,sx,sy,_ in sites],fill=(114,74,55),width=5)
    routes=[([('SUNMEADOW MARCH',220,630),('GREYBROOK CROSSING',420,685),('IRONWOOD REDOUBT',620,730)],sites[2]),
      ([('BRIGHTFEN APPROACH',250,1180),('GLASSRIVER FORD',455,1150),('HIGHVALE RAMPART',655,1110)],sites[2]),
      ([('CINDERFEN OUTSKIRTS',1830,635),('BLEAKROOT CAUSEWAY',1630,687),('VILEMERE HEIGHTS',1420,737)],sites[5]),
      ([('ASHEN STEPPE',1830,1190),('GOREPINE PASS',1620,1150),('OBSIDIAN SCAR',1410,1110)],sites[5])]
    for rows,end in routes:
        d.line([(sx,sy) for _,sx,sy in rows]+[(end[1],end[2])],fill=(133,106,72),width=3)
        for text,sx,sy in rows:
            d.ellipse((sx-6,sy-6,sx+6,sy+6),fill=ink)
            d.text((sx,sy-31),text,font=small,fill=ink,anchor='mm')
    for i,(text,sx,sy,realm) in enumerate(sites):
        color=(61,91,122) if realm=='a' else(133,55,54)
        d.rectangle((sx-14,sy-11,sx+14,sy+11),fill=color,outline=ink,width=2)
        for dx in(-13,-2,9):d.rectangle((sx+dx,sy-16,sx+dx+5,sy-10),fill=color)
        words=text.split(' ');mid=max(1,len(words)//2)
        d.text((sx,sy+38),' '.join(words[:mid]),font=small,fill=ink,anchor='mm')
        d.text((sx,sy+68),' '.join(words[mid:]),font=small,fill=ink,anchor='mm')
    # Compass rose and distance-bar are printed; separate geometric brass dividers sit above.
    cx,cy=1750,1650
    for j in range(16):
        a=j*math.tau/16;length=112 if j%4==0 else 78 if j%2==0 else 45
        pts=[(cx+math.cos(a-.19)*15,cy+math.sin(a-.19)*15),(cx+math.cos(a)*length,cy+math.sin(a)*length),(cx+math.cos(a+.19)*15,cy+math.sin(a+.19)*15)]
        d.polygon(pts,fill=ink if j%2==0 else faded)
    d.text((cx,cy-141),'N',font=label,fill=ink,anchor='mm')
    d.line((170,1745,645,1745),fill=ink,width=4)
    for j in range(6):d.line((170+j*95,1732,170+j*95,1758),fill=ink,width=3)
    d.text((170,1780),'FIELD SURVEY  •  ROUTES SCHEMATIC',font=small,fill=ink)
    d.text((170,1825),'Reckon passes, provisions and river crossings.',font=small,fill=faded)
    d.text((170,1870),'Keep this chart dry. Return to the quartermaster.',font=small,fill=faded)
    return image

def fields(name):
    broad,medium,fine=noise(19),noise(91),noise(520)
    if name=='oak':
        grain=np.sin(x*math.tau*60+np.sin(y*math.tau*3+broad*2)*2.6+broad*8)
        pores=np.maximum(0,grain-.45)**1.5
        color=np.array([.43,.285,.15])[None,None,:]*(.79+broad[:,:,None]*.36)
        color-=pores[:,:,None]*np.array([.08,.06,.032]);color+=np.maximum(0,medium-.7)[:,:,None]*.07
        height=broad*.1-pores*.08+fine*.02;rough=.71+medium*.17;metal=0
    elif name=='iron':
        color=np.array([.22,.235,.24])[None,None,:]*(.75+broad[:,:,None]*.38)
        color+=np.maximum(0,medium-.75)[:,:,None]*np.array([.16,.07,.02])
        height=medium*.04+fine*.024;rough=.37+medium*.18;metal=.91
    elif name=='brass':
        color=np.array([.61,.42,.19])[None,None,:]*(.8+broad[:,:,None]*.23)
        height=medium*.015+fine*.009;rough=.34+medium*.16;metal=.91
    elif name=='leather':
        color=np.array([.22,.086,.039])[None,None,:]*(.76+broad[:,:,None]*.48)
        height=medium*.065+fine*.055;rough=.72+medium*.13;metal=0
    elif name=='ceramic':
        color=np.array([.18,.255,.235])[None,None,:]*(.83+broad[:,:,None]*.29)
        height=medium*.009+fine*.005;rough=.29+medium*.14;metal=0
    else:
        age=(np.maximum(abs(x-.5),abs(y-.5))/.5)**7
        color=np.array([.87,.80,.62])[None,None,:]*(.91+broad[:,:,None]*.08)
        color-=age[:,:,None]*np.array([.11,.115,.11]);color-=np.maximum(0,medium-.83)[:,:,None]*.13
        height=medium*.022+fine*.014;rough=.83+medium*.1;metal=0
    dy,dx=np.gradient(height);normal=np.stack((-dx*8,-dy*8,np.ones_like(x)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    return {'basecolor':color,'normal':normal*.5+.5,'orm':np.stack((np.ones_like(x),rough,np.full_like(x,metal)),axis=-1)}

if __name__=='__main__':
    receipts={}
    for name in('oak','iron','brass','leather','ceramic','parchment'):
        for channel,pixels in fields(name).items():
            image=Image.fromarray(np.uint8(np.clip(pixels,0,1)*255))
            if name=='parchment' and channel=='basecolor':image=map_art(image)
            sizes=(2048,1024,512) if name=='parchment' and channel=='basecolor' else (1024,512,256) if channel=='basecolor' or name=='oak' else (512,256,128)
            for lod,size in enumerate(sizes):
                dimensions=(size,round(size*1146/2048)) if name=='parchment' and channel=='basecolor' else(size,size)
                target=ROOT/'textures'/f'{name}_lod{lod}_{channel}.png';image.resize(dimensions,Image.Resampling.LANCZOS).save(target)
                receipts[str(target.relative_to(ROOT)).replace('\\','/')]={'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'dimensions':dimensions}
    (ROOT/'textures/sources.json').write_text(json.dumps({'generatorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'seed':2092071,'art':'Original schematic Aegis/Riftbound chart drawn from campaign names; not a navigable minimap.','textures':receipts},separators=(',',':'))+'\n')
    print('COMMAND_TABLE_TEXTURES_SAVED',len(receipts),flush=True)
