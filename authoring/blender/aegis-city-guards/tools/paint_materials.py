"""Small deterministic tileable PBR color sources, no external image services."""
from pathlib import Path
import math
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
COLORS={'steel':(95,104,111),'brass':(137,107,60),'crimson':(30,49,72),
        'parchment':(194,185,157),'leather':(65,46,31),'chainmail':(74,80,82),
        'skin':(171,133,109),'skin_ear':(174,129,109)}

def main():
    out=ROOT/'textures'; out.mkdir(exist_ok=True)
    size=512
    for name,color in COLORS.items():
        image=Image.new('RGB',(size,size)); px=image.load()
        for y in range(size):
            for x in range(size):
                grain=(((x*73856093)^(y*19349663))%101)/100-.5
                variation=grain*.17+.028*math.sin(x*.037)*math.sin(y*.051)
                if name.startswith('skin'): variation=grain*.035
                if name in {'crimson','parchment'}: variation+=.025*((x%3==0)-(y%3==0))
                if name=='chainmail':
                    xx=(x+(y//12%2)*6)%12-6; yy=y%12-6
                    distance=math.sqrt(xx*xx+yy*yy)
                    variation+=.42 if 3.8<distance<5.1 else -.20
                px[x,y]=tuple(max(0,min(255,round(c*(1+variation)))) for c in color)
        draw=ImageDraw.Draw(image)
        if name in {'steel','brass','leather'}:
            for i in range(240):
                x=(i*137)%size; y=(i*223)%size
                shade=tuple(min(255,int(c*(1.35 if i%3 else .55))) for c in color)
                draw.line((x,y,x+2+i%9,y+3+i%5),fill=shade,width=1)
        if name in {'crimson','parchment'}:
            for i in range(140):
                x=(i*137)%size; y=size-1-(i*31%74)
                draw.line((x,y,x+1,y+3+i%12),fill=tuple(int(c*.50) for c in color),width=1)
        image.save(out/f'{name}.png')

if __name__=='__main__': main()
