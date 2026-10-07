"""Draw private catalog room plans; source markers are schematic, not asset previews."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
receipt=json.loads((DIRECTORY/'homes-latest.json').read_text())
review=json.loads((DIRECTORY/'home-review.json').read_text())
if receipt['signature']!=review['signature']:
    raise RuntimeError('Home drawings require matching native evidence')
catalog=json.loads((ROOT/'artifacts/unreal/capital-expansion/assets.json').read_text())['templates']
font=lambda size:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',size)
for zone in receipt['zones']:
    for home in zone['homes']:
        template=catalog[home['template']]
        if template['sha256']!=home['sourceSha256']:
            raise RuntimeError('Home template changed')
        result=next(r for r in review['homes'] if r['id']==home['id'])
        image=Image.new('RGB',(1120,920),'#172227');draw=ImageDraw.Draw(image)
        draw.text((32,22),zone['id'].replace('_',' ').title()+' — furnished home study',font=font(28),fill='#ece9d8')
        draw.text((32,64),home['id']+' / private modular catalog',font=font(17),fill='#bdc8bd')
        w,d=template['roomSize'];scale=.56
        point=lambda p:(500+p[0]*scale,420-p[1]*scale)
        left,top=point([-w/2,d/2]);right,bottom=point([w/2,-d/2])
        draw.rectangle((left,top,right,bottom),fill='#444943',outline='#eeddb8',width=8)
        entry=point(template['entrance'])
        wall=point([template['entrance'][0],-d/2])
        draw.line((wall[0]-40,wall[1],wall[0]+40,wall[1]),fill='#91e0c4',width=10)
        route=[template['entrance'],[template['entrance'][0],-d/2+85,10],[template['entrance'][0],0,10],[0,0,10]]
        draw.line([point(p) for p in route],fill='#91e0c4',width=6)
        for p in route:
            x,y=point(p);r=42*scale
            draw.ellipse((x-r,y-r,x+r,y+r),outline='#91e0c4',width=2)
        seen=set()
        for component in template['components']:
            if component['role']!='furniture' or 'support' in component:continue
            name=component['mesh'].rsplit('.',1)[-1].removeprefix('SM_').replace('_',' ')
            if name in ['Bed Matress','Bed Pillow','Bed Sheet','Bottle','Cup','Book']:continue
            key=(tuple(component['anchor']),name)
            if key in seen:continue
            seen.add(key)
            x,y=point(component['anchor'])
            draw.ellipse((x-9,y-9,x+9,y+9),fill='#ddb285')
            draw.text((x+13,y-12),name,font=font(17),fill='#f0ddc3')
        draw.text((800,140),'Room plan',font=font(23),fill='#ece9d8')
        lines=[f'{w/100:g} × {d/100:g} m ground floor','Furnished source assembly','Green: capsule route','Circles: 42 cm radius','Furniture: anchor markers','',f"{result['capsuleSweeps']:,} capsule sweeps",f"{result['floorSamples']:,} floor samples",f"{result['sweptStepTransitions']} step transitions",'Native step limit: 45 cm','', 'Capsule route: '+('clear' if result['capsuleClear'] else 'failed checks'),'Live walking: pending','Visual approval: pending']
        for i,line in enumerate(lines):draw.text((800,180+i*31),line,font=font(17),fill='#c7c9bb')
        draw.text((32,828),'Schematic derived from the private catalog receipt. Markers do not show furniture footprints.',font=font(17),fill='#c7c9bb')
        draw.text((32,864),'Original kit templates and capital scenes are preserved. Regional appearance and acceptance remain open.',font=font(17),fill='#c7c9bb')
        image.save(DIRECTORY/(home['id']+'_floor_plan.png'))
print('Created four furnished-home study drawings')
