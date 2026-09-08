"""Original retained Cinderfen surface painting; no Sunmeadow pixel reuse."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1];SIDE=1024
GRAIN=[[(24,0),(34,114),(19,293),(42,447),(28,640),(45,806),(33,1024)],
 [(118,0),(99,198),(120,362),(104,549),(132,725),(113,897),(128,1024)],
 [(221,0),(240,139),(213,326),(231,511),(214,681),(242,843),(229,1024)],
 [(343,0),(324,181),(349,383),(327,594),(354,784),(338,1024)],
 [(464,0),(482,148),(459,316),(487,519),(468,719),(489,910),(480,1024)],
 [(595,0),(580,172),(606,379),(587,593),(613,803),(600,1024)],
 [(725,0),(742,183),(718,378),(745,586),(726,775),(750,1024)],
 [(859,0),(837,176),(866,392),(844,592),(868,825),(851,1024)],
 [(981,0),(960,193),(986,390),(969,566),(992,816),(980,1024)]]
CLEFTS=[[(0,223),(123,205),(242,248),(357,218),(472,246),(582,231),(707,269),(812,245),(930,267),(1024,241)],
 [(0,731),(150,759),(276,725),(398,750),(526,736),(659,769),(768,746),(911,784),(1024,754)],
 [(324,0),(308,125),(327,271),(295,389),(315,502)],[(791,1024),(765,875),(791,739),(758,621)]]
CHIPS=[(37,72),(167,163),(266,84),(398,139),(540,57),(677,151),(824,93),(957,180),
 (81,369),(223,303),(346,391),(498,328),(638,402),(785,313),(924,421),
 (25,603),(177,551),(306,645),(463,566),(610,632),(743,541),(866,617),(996,559),
 (107,820),(242,921),(377,837),(523,971),(672,858),(811,933),(966,849)]
KNOT_OUTLINE=[(0,-71),(-21,-51),(-33,-14),(-29,29),(-11,56),(7,62),(29,27),(32,-12),(19,-49),(0,-71)]
MINERAL_MARGIN=[(0,837),(65,849),(126,817),(194,842),(271,803),(347,833),(411,816),(486,851),(551,827),(617,847),(692,819),(759,840),(824,812),(903,841),(965,825),(1024,847)]
DAMP_TRAILS=[[(73,12),(88,151),(61,282),(95,426),(72,610),(103,781),(82,1014)],[(502,5),(481,186),(513,339),(489,527),(521,702),(494,859),(510,1018)],[(888,8),(871,151),(902,313),(879,482),(909,699),(883,843),(905,1017)]]

def pigment_field(seed,scales):
    """Retained seed and brush scales describe an original multiscale wash."""
    random=np.random.default_rng(seed);field=np.zeros((SIDE,SIDE),dtype=np.float32)
    for width,height,weight in scales:
        knots=np.round(random.uniform(0,255,(height,width))).astype('uint8')
        field+=(np.asarray(Image.fromarray(knots).resize((SIDE,SIDE),Image.Resampling.BICUBIC),dtype=np.float32)/127.5-1)*weight
    return field


def painted(name,definition):
    base=definition['color'];kind=definition['kind'];rough=round(255*definition['roughness']);metal=round(255*definition.get('metallic',0))
    albedo=Image.new('RGB',(SIDE,SIDE),tuple(base));height=Image.new('L',(SIDE,SIDE),128);roughness=Image.new('L',(SIDE,SIDE),rough)
    yy,xx=np.mgrid[0:SIDE,0:SIDE].astype(np.float32)
    if kind=='wood':
        # Directional fibres vary along their length without a crosswise lattice.
        wash=pigment_field(1703,[(17,3,.75),(67,9,.28),(251,31,.10)])
        drift=7*np.sin(yy*.008)+3*np.sin(yy*.026+xx*.009)
        grain=np.sin((xx+drift)*.39)+.45*np.sin((xx+drift*.6)*1.14)
        color=np.array(base)[None,None,:]+wash[...,None]*24+grain[...,None]*3.5
        relief=128+wash*14+grain*5;rough_field=rough+wash*16-grain*3
    elif kind=='stone':
        wash=pigment_field(2917,[(9,11,.75),(39,43,.25),(181,197,.10)])
        mineral=pigment_field(4031,[(21,18,.5),(113,129,.17)])
        grit=pigment_field(6073,[(149,163,.50),(367,349,.22)])
        amplitude=4 if definition.get('weather')=='ash_mortar' else 13
        color=np.array(base)[None,None,:]+wash[...,None]*amplitude+mineral[...,None]*4+grit[...,None]*3
        relief=128+wash*11+mineral*7+grit*19;rough_field=rough+wash*11+mineral*7+grit*8
    elif kind=='reed':
        wash=pigment_field(3169,[(173,5,.65),(337,21,.20)])
        color=np.array(base)[None,None,:]+wash[...,None]*28
        relief=128+wash*18;rough_field=rough+wash*12
    else:color=relief=rough_field=None
    if color is not None:
        albedo=Image.fromarray(np.round(color).clip(0,255).astype('uint8'))
        height=Image.fromarray(np.round(relief).clip(0,255).astype('uint8'))
        roughness=Image.fromarray(np.round(rough_field).clip(0,255).astype('uint8'))
    c,h,r=ImageDraw.Draw(albedo),ImageDraw.Draw(height),ImageDraw.Draw(roughness)
    tint=lambda delta:tuple(max(0,min(255,value+delta)) for value in base)
    if kind=='wood':
        for index,line in enumerate(GRAIN):
            for shift,width,delta in [(-36,2,-12),(-23,3,7),(-8,5,-8),(0,2,-21),(12,3,9),(27,2,-7),(43,1,10)]:
                points=[(x+shift,y) for x,y in line]
                c.line(points,fill=tint(delta),width=width,joint='curve');h.line(points,fill=128+delta,width=max(1,width//2));r.line(points,fill=min(255,rough+abs(delta)//2),width=width)
        for cx,cy in [(282,267),(679,779)]:
            for ring in range(4):
                scale=1+ring*.18;points=[(cx+x*scale,cy+y*scale) for x,y in KNOT_OUTLINE]
                c.line(points,fill=tint(-18+ring*3),width=2,joint='curve');h.line(points,fill=107+ring*4,width=2)
        for crack in [[(43,0),(47,69),(36,125),(41,158)],[(570,1024),(553,944),(565,874)],[(914,0),(924,55),(910,111)]]:
            c.line(crack,fill=tint(-27),width=3);h.line(crack,fill=82,width=2)
    elif kind in ('stone','ceramic'):
        for line in ([] if definition.get('weather')=='ash_mortar' else CLEFTS):
            c.line(line,fill=tint(-11 if kind=='stone' else -5),width=4,joint='curve');h.line(line,fill=102 if kind=='stone' else 119,width=3,joint='curve')
            r.line(line,fill=min(255,rough+15),width=8)
        for index,(x,y) in enumerate(CHIPS):
            extent=2+index%4;outline=[(x-extent,y-1),(x-2,y-extent),(x+extent,y-2),(x+extent+1,y+extent),(x-1,y+extent+1)]
            c.polygon(outline,fill=tint(-9-index%5));h.polygon(outline,fill=98+index%11);r.polygon(outline,fill=min(255,rough+12))
        if kind=='ceramic':
            for row in range(31):
                y=row*34;c.line([(0,y+4),(256,y),(511,y+7),(768,y+2),(1024,y+5)],fill=tint(3 if row%3 else -4),width=2)
    elif kind=='reed':
        for stem,x in enumerate(range(-10,SIDE+10,11)):
            bend=[(x,0),(x+2,156),(x-2,338),(x+3,550),(x,753),(x+2,1024)]
            c.line(bend,fill=tint((stem%5)*3-6),width=7,joint='curve');h.line(bend,fill=142,width=6,joint='curve')
            c.line([(a-2,b) for a,b in bend],fill=tint(-12),width=1);h.line([(a-4,b) for a,b in bend],fill=112,width=1)
        # Roof sheaves are held by the modeled iron bindings. Only woven wall
        # mats carry crosswise ties; repeating roof ties read as stitched cloth.
        binders=range(29,SIDE,87) if definition.get('weather')!='exposed_tips' else ()
        for y in binders:
            c.line([(0,y),(220,y+2),(491,y-1),(756,y+3),(1024,y)],fill=tint(-19),width=7);h.line([(0,y),(SIDE,y)],fill=151,width=6)
            c.line([(0,y-2),(SIDE,y-2)],fill=tint(5),width=1)
        for index,(x,y) in enumerate(CHIPS):r.line([(x,y-18),(x+1,y+19)],fill=min(255,rough+8),width=4)
    elif kind=='metal':
        for index,(x,y) in enumerate(CHIPS):
            outline=[(x-7,y-3),(x-2,y-9),(x+8,y-5),(x+12,y+3),(x+3,y+9),(x-8,y+4)]
            h.polygon(outline,fill=121+index%6);r.polygon(outline,fill=min(255,rough+8+index%13))
            c.line([(x-5,y+4),(x+4,y+6),(x+9,y+1)],fill=tint(4),width=1)
        for index in range(12):
            y=52+index*83;c.line([(28,y),(191,y-7),(370,y+4)],fill=tint(5),width=1);r.line([(28,y),(370,y+4)],fill=max(0,rough-16),width=2)
    elif kind=='cloth':
        for x in range(0,SIDE,5):c.line([(x,0),(x,SIDE)],fill=tint(4),width=1);h.line([(x,0),(x,SIDE)],fill=135,width=1);r.line([(x,0),(x,SIDE)],fill=max(0,rough-6),width=1)
        for y in range(0,SIDE,5):c.line([(0,y),(SIDE,y)],fill=tint(-4),width=1);h.line([(0,y),(SIDE,y)],fill=122,width=1);r.line([(0,y),(SIDE,y)],fill=min(255,rough+4),width=1)
        for x in (21,28,996,1003):c.line([(x,0),(x,SIDE)],fill=tint(12),width=2);h.line([(x,0),(x,SIDE)],fill=142,width=2);r.line([(x,0),(x,SIDE)],fill=max(0,rough-10),width=2)
    weather=definition.get('weather')
    if weather=='cut_pith':
        # A separate physical cut-end material prevents the edge of a dense
        # sheaf from looking like a smooth wooden plate or a stitched fabric.
        random=np.random.default_rng(4519);c.rectangle((0,0,SIDE,SIDE),fill=tint(-24));h.rectangle((0,0,SIDE,SIDE),fill=119)
        for row in range(-1,66):
            for column in range(-1,66):
                x=column*16+(row%2)*8+random.uniform(-2,2);y=row*16+random.uniform(-2,2)
                rx=random.uniform(6.3,8.2);ry=random.uniform(6.0,8.0);delta=int(random.integers(-9,15))
                rim=(x-rx,y-ry,x+rx,y+ry);c.ellipse(rim,fill=tint(delta));h.ellipse(rim,fill=143+delta//3);r.ellipse(rim,fill=239+abs(delta)//3)
                inner=(x-rx*.53+.4,y-ry*.48,x+rx*.53+.4,y+ry*.48)
                c.ellipse(inner,fill=tint(-42 if (row+column)%4 else -28));h.ellipse(inner,fill=86 if (row+column)%4 else 108);r.ellipse(inner,fill=251)
    elif weather=='mineral_splash':
        outline=MINERAL_MARGIN+[(1024,1024),(0,1024)]
        c.polygon(outline,fill=(103,110,75));r.polygon(outline,fill=248)
        for x,y in CHIPS:
            if y>700:
                c.line([(x,1001),(x-3,937),(x+4,873)],fill=(137,129,90),width=5);h.line([(x,1001),(x+4,873)],fill=140,width=3)
    elif weather=='tar':
        for index,line in enumerate(GRAIN[::2]):c.line([(x+14,y) for x,y in line],fill=tint(-9),width=14,joint='curve');r.line(line,fill=max(80,rough-27),width=16,joint='curve')
    elif weather=='footwear':
        for x,y in [(267,183),(701,441),(330,803)]:
            outline=[(x-53,y-81),(x+29,y-71),(x+41,y+32),(x+17,y+79),(x-37,y+64),(x-61,y-12)]
            c.polygon(outline,fill=tint(8));r.polygon(outline,fill=max(0,rough-24))
    elif weather=='exposed_tips':
        for x,y in MINERAL_MARGIN:
            c.line([(x,1024),(x+2,y+45)],fill=tint(-17),width=9);r.line([(x,1024),(x+2,y+45)],fill=253,width=8)
    if weather in ('exposed_tips','damp_weave','tar'):
        stain=Image.new('L',(SIDE,SIDE),0);brush=ImageDraw.Draw(stain)
        for index,line in enumerate(DAMP_TRAILS):brush.line(line,fill=65+index*13,width=39+index*17,joint='curve')
        stain=stain.filter(ImageFilter.GaussianBlur(13));field=np.asarray(stain,dtype=np.float32)/255
        color=np.asarray(albedo,dtype=np.float32).copy()
        pigment=np.array((31,36,25) if weather!='tar' else (25,27,23),dtype=np.float32)
        amount=field[...,None]*.72
        color=color*(1-amount)+pigment*amount
        albedo=Image.fromarray(np.round(color).clip(0,255).astype('uint8'))
        rough_pixels=np.asarray(roughness,dtype=np.float32)-field*24
        roughness=Image.fromarray(np.round(rough_pixels).clip(0,255).astype('uint8'))
    # Continuous periodic material fields avoid introducing rectangular tile seams.
    for layer in (albedo,height,roughness):
        pixels=np.asarray(layer,dtype=np.float32).copy()
        for axis in (0,1):
            for distance in range(12):
                first=[slice(None)]*pixels.ndim;last=list(first);first[axis]=distance;last[axis]=SIDE-1-distance
                weight=(1-distance/12)*.5;a=pixels[tuple(first)].copy();b=pixels[tuple(last)].copy();pixels[tuple(first)]=a*(1-weight)+b*weight;pixels[tuple(last)]=b*(1-weight)+a*weight
        layer.paste(Image.fromarray(np.round(pixels).astype('uint8')))
    relief=np.asarray(height.filter(ImageFilter.GaussianBlur(.38)),dtype=np.float32)/255
    scale={'wood':.0032,'stone':.006,'ceramic':.0012,'reed':.0055,'metal':.0007,'cloth':.0005}[kind]
    dx=(np.roll(relief,-1,axis=1)-np.roll(relief,1,axis=1))*.5;dy=(np.roll(relief,-1,axis=0)-np.roll(relief,1,axis=0))*.5
    # PNG rows run downward; Blender UV V and tangent-space +Y run upward.
    normal=np.dstack((-dx*scale*SIDE,dy*scale*SIDE,np.ones_like(relief)));normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    normal_image=Image.fromarray(np.round((normal*.5+.5)*255).clip(0,255).astype('uint8'))
    cavity=np.clip(1-np.maximum(0,.5-relief)*.40,0,1)
    orm=Image.fromarray(np.dstack((cavity*255,np.asarray(roughness),np.full_like(relief,metal))).astype('uint8'))
    maps={'baseColor':albedo,'normal':normal_image,'orm':orm,'height':height,'roughness':roughness}
    output=ROOT/'textures/source';output.mkdir(parents=True,exist_ok=True)
    for channel,image in maps.items():image.save(output/f'{name}_{channel}.png',optimize=True)
    return {'material':name,'definition':definition,'height_scale_m':scale,'normal_convention':'OpenGL tangent +Y, with top-left raster Y converted to upward UV V','channels':{channel:{'path':f'textures/source/{name}_{channel}.png','sha256':hashlib.sha256((output/f'{name}_{channel}.png').read_bytes()).hexdigest()} for channel in maps},'occlusion_scope':'painted material cavity, not scene illumination'}


if __name__=='__main__':
    source=json.loads((ROOT/'source/architecture.json').read_text());records=[painted(name,definition) for name,definition in source['materials'].items()]
    manifest={'source':'Original Cinderfen surface painting; independent height and roughness fields. No Sunmeadow image pixels reused.','paint_tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'strokes':{'grain':GRAIN,'clefts':CLEFTS,'chips':CHIPS,'knot_outline':KNOT_OUTLINE,'mineral_margin':MINERAL_MARGIN,'damp_trails':DAMP_TRAILS,'pigment_washes':{'wood':1703,'stone':2917,'stone_mineral':4031,'reed':3169}},'materials':records}
    (ROOT/'textures/paint_records.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Painted {len(records)} original Cinderfen PBR material sets.')
