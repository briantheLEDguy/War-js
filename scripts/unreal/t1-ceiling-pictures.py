"""Draw a labeled recipe schematic; actual appearance remains in native captures."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
directory=ROOT/'artifacts/unreal/t1-redesign'
receipt=json.loads((directory/'ceilings-latest.json').read_text())
review=json.loads((directory/'ceiling-review.json').read_text())
if review['signature']!=receipt['signature'] or not review['overheadClosed']:
    raise RuntimeError('Schematic requires the matching verified ceiling recipe')
canvas=Image.new('RGB',(1500,920),'#172227'); draw=ImageDraw.Draw(canvas)
font_file='C:/Windows/Fonts/arial.ttf'
font=lambda size:ImageFont.truetype(font_file,size)
draw.text((40,28),'T1 modular timber ceilings',font=font(38),fill='#efe4cf')
draw.text((40,83),'Authoring schematic — six/nine reviewed kit bays; native images show actual appearance',font=font(23),fill='#cbd1c8')
for index,room in enumerate(([600,900],[900,900])):
    recipe=next(r for r in receipt['inputs']['recipes'].values() if r['roomSize']==room)
    x=50+index*465; y=185; scale=.4; width,depth=room
    draw.text((x,y-42),f'{width/100:g} x {depth/100:g} m home: {len(recipe["panels"])} bays',font=font(25),fill='#eee2c9')
    for panel in recipe['panels']:
        bx,by=panel['bay']; bounds=(x+bx*300*scale,y+by*300*scale,x+(bx+1)*300*scale,y+(by+1)*300*scale)
        draw.rectangle(bounds,fill='#75533c',outline='#d3b181',width=3)
        for line in range(1,8):
            lx=bounds[0]+line*300*scale/8; draw.line((lx,bounds[1]+4,lx,bounds[3]-4),fill='#352a24',width=2)
        draw.text((bounds[0]+18,bounds[1]+45),'3 m bay',font=font(17),fill='#f0dec3')
    draw.text((x,y+depth*scale+18),f'{len(recipe["probes"])} upward native rays',font=font(22),fill='#cbd1c8')
    draw.text((x,y+depth*scale+50),'150 cm witness grid',font=font(20),fill='#cbd1c8')
recipe=next(iter(receipt['inputs']['recipes'].values()))
x,y=1080,185; scale=1.0
floor_y=y+recipe['topZ']*scale
ceiling_y=floor_y-recipe['bottomZ']*scale
draw.text((x,y-42),'Measured vertical envelope',font=font(25),fill='#eee2c9')
draw.rectangle((x,y,x+270,ceiling_y),fill='#75533c',outline='#d3b181',width=3)
draw.rectangle((x,floor_y-recipe['floorTopZ'],x+270,floor_y),fill='#737672')
draw.line((x-10,y,x+290,y),fill='#cbd1c8',width=2)
draw.text((x,y-25),f'{recipe["topZ"]:.1f} cm wall/eave top',font=font(19),fill='#efdfc9')
draw.text((x,ceiling_y+12),f'{recipe["topZ"]-recipe["bottomZ"]:.1f} cm timber depth',font=font(20),fill='#cbd1c8')
draw.text((x,ceiling_y+75),f'{recipe["minimumHeadroomCm"]:.1f} cm',font=font(28),fill='#efe4cf')
draw.text((x,ceiling_y+112),'minimum bounds clearance',font=font(19),fill='#cbd1c8')
draw.text((x,floor_y+18),'Existing floors and furniture retained',font=font(18),fill='#cbd1c8')
draw.text((50,725),'Plank top faces downward: no two-sided material override or new visible primitive.',font=font(25),fill='#efe4cf')
draw.text((50,775),'Each ceiling is merged separately; parent house meshes, doorways and roof refits remain exact.',font=font(23),fill='#cbd1c8')
draw.text((50,825),'Regional cultural architecture, distant LODs, camera/visual approval and release acceptance remain open.',font=font(23),fill='#cbd1c8')
target=ROOT/review['pictureDirectory']/'timber_ceiling_bays.png'
canvas.save(target)
print(str(target))
