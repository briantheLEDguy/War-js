"""Draw measured retained-population approaches; never present drawings as native views."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
receipt=json.loads((DIRECTORY/'population-latest.json').read_text(encoding='utf-8'))
review=json.loads((DIRECTORY/'population-review.json').read_text(encoding='utf-8'))
if receipt['signature']!=review['signature'] or not review['exactBindingsVerified'] or not review['capsuleClear']:
    raise RuntimeError('Population drawings require matching native binding/access review')
output=ROOT/review['pictureDirectory']
font=lambda size:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
for zone in receipt['zones']:
    source=json.loads((DIRECTORY/(zone['id']+'.json')).read_text(encoding='utf-8'))
    image=Image.new('RGB',(1720,1130),'#162329'); draw=ImageDraw.Draw(image)
    draw.text((35,25),zone['id'].replace('_',' ').title()+' — retained population and access',font=font(31),fill='#f3e7cb')
    draw.text((35,72),'Measured topology drawing • isolated prototype • gameplay, Node integration and appearance unapproved',font=font(21),fill='#c7d0c8')
    b=source['spatial']['bounds']; scale=min(1000/(b['maxX']-b['minX']),850/(b['maxZ']-b['minZ']))
    project=lambda x,z:(int(50+(x-b['minX'])*scale),int(125+(z-b['minZ'])*scale))
    native=lambda p:project(p[1]/100,p[0]/100)
    outline=[project(p['x'],p['z']) for p in source['spatial']['playableOutline']]
    draw.polygon(outline,fill='#283d3c',outline='#8c9c89')
    for path in source['paths']:
        p=[project(q['x'],q['z']) for q in path['points']]
        color='#aba989' if 'advance' in path['id'] else '#637b74'
        draw.line(p,fill=color,width=5)
    for n,home in enumerate(zone['homes']):
        p=native(zone['actorInventory'][home['id']]['location'])
        draw.rectangle((p[0]-6,p[1]-6,p[0]+6,p[1]+6),fill='#d8bb86')
        draw.text((p[0]+9,p[1]-14),'H'+str(n+1),font=font(16),fill='#f3e7cb')
    for number,row in enumerate(zone['population'],1):
        points=[native(p) for p in row['approach']]; color='#8bd3e8' if row['kind']=='npc' else '#a2da90'
        draw.line(points,fill=color,width=3); p=native(row['ground'])
        draw.ellipse((p[0]-7,p[1]-7,p[0]+7,p[1]+7),fill=color,outline='#162329',width=2)
        draw.text((p[0]+10,p[1]-11),str(number),font=font(18),fill='#f3e7cb')
        y=140+(number-1)*80
        name=row['definition'].get('name',row['definition'].get('label',row['id']))
        draw.text((1110,y),str(number)+'. '+name,font=font(22),fill=color)
        label=row['id'].removeprefix(zone['id']+'_').replace('_',' ')
        draw.text((1110,y+28),label+' / '+row['kind'],font=font(17),fill='#d0d9cb')
        length=sum(((a[0]-c[0])**2+(a[1]-c[1])**2)**.5 for a,c in zip(row['approach'],row['approach'][1:]))/100
        draw.text((1110,y+52),f'{length:.1f} m supported approach • {row["adjustmentCm"]/100:.1f} m horizontal adjustment',font=font(16),fill='#aebcaf')
    pending=[r for r in zone['pendingPopulation'] if r['reason']=='native-terrain-capsule-access-pending']
    y=140+len(zone['population'])*80+30
    draw.text((1110,y),'Held native access sites',font=font(23),fill='#edb076')
    for n,row in enumerate(pending):
        p=native(row['ideal']); draw.line((p[0]-7,p[1]-7,p[0]+7,p[1]+7),fill='#edb076',width=3)
        draw.line((p[0]-7,p[1]+7,p[0]+7,p[1]-7),fill='#edb076',width=3)
        draw.text((1110,y+35+n*30),row['id'].removeprefix(zone['id']+'_')+' — terrain/capsule access pending',font=font(17),fill='#edb076')
    if not pending: draw.text((1110,y+35),'None among the admitted native sources',font=font(17),fill='#d0d9cb')
    counts={kind:sum(r['kind']==kind for r in zone['pendingPopulation']) for kind in ('npc','resource','crafting')}
    draw.text((35,1010),'Blue: exact retained NPC • Green: exact herb visual • Coloured links: native capsule-checked approach',font=font(20),fill='#d0d9cb')
    draw.text((35,1045),'Pending: '+', '.join(str(v)+' '+k for k,v in counts.items())+' • H1/H2: furnished homes • muted lines: authored route network',font=font(20),fill='#edb076')
    draw.text((35,1080),'These points retain canonical rules and meshes. Native position overrides are recorded separately; Node geometry remains unsynchronized.',font=font(18),fill='#aebcaf')
    file=output/(zone['id']+'_population_topology.png'); image.save(file)
    print(file)
