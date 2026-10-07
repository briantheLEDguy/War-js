"""Render source topology progress PNGs; these are diagrams, not native gameplay captures."""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
def font(size):
    return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',size)

def render(identity):
    zone=json.loads((DIRECTORY/(identity+'.json')).read_text())
    image=Image.new('RGB',(1400,1050),'#172227');draw=ImageDraw.Draw(image)
    b=zone['spatial']['bounds']
    def p(row):return (50+(row['x']-b['minX'])/(b['maxX']-b['minX'])*1300,115+(b['maxZ']-row['z'])/(b['maxZ']-b['minZ'])*800)
    def label(row,text,color='#eee8d3'):
        x,y=p(row);draw.text((x+12,y-22),text,font=font(17),fill=color,stroke_width=2,stroke_fill='#172227')
    draw.text((45,25),zone['name']+' — topology progress',font=font(36),fill='#eee8d3')
    draw.text((45,76),'Gold: advance   Cyan: vehicle flanks   Pink: rotation links   Dashed circles: staging',font=font(19),fill='#cecbb9')
    outline=[p(row) for row in zone['spatial']['playableOutline']]
    draw.polygon(outline,fill=zone['orvrLayout']['biome']['palette'][0],outline='#d4c99d',width=3)
    for feature in zone['orvrLayout']['terrain']['landforms']:
        if feature['height']<0:continue
        x,y=p(feature);rx=feature['radiusX']/(b['maxX']-b['minX'])*1300;rz=feature['radiusZ']/(b['maxZ']-b['minZ'])*800
        for scale in [.35,.65,.9]:draw.ellipse((x-rx*scale,y-rz*scale,x+rx*scale,y+rz*scale),outline='#b7b497',width=1)
    for i,path in enumerate(zone['paths']):draw.line([p(row) for row in path['points']],fill='#ffe5a1' if i==0 else '#83d4e1' if i<3 else '#eea4e2' if i<5 else '#c9c8ae',width=7 if i<3 else 4,joint='curve')
    for keep in zone['orvrLayout']['keeps']:
        x,y=p(keep);draw.rectangle((x-17,y-14,x+17,y+14),fill='#244e7b' if keep['realm']=='aegis' else '#842c38',outline='#ffffff',width=2);label(keep,keep['realm'].capitalize()+' keep')
    for i,bo in enumerate(zone['orvrLayout']['battlefieldObjectives']):
        x,y=p(bo);draw.ellipse((x-13,y-13,x+13,y+13),fill='#ffe5a1',outline='#172227',width=2);label(bo,'Objective '+str(i+1))
    for camp in zone['orvrLayout']['stagingCamps']:
        x,y=p(camp);draw.ellipse((x-19,y-19,x+19,y+19),outline='#ffffff',width=3);label(camp,'Staging')
    v=zone['spawnPoint']
    modules=json.loads((DIRECTORY/(identity+'_modules.json')).read_text())['modules']
    def corner(module,x,z):
        c,s=math.cos(module['rotY']),math.sin(module['rotY'])
        return {'x':module['x']+x*c+z*s,'z':module['z']+z*c-x*s}
    for module in modules:
        w,d=module['reservation']['width']/2,module['reservation']['depth']/2
        draw.polygon([p(corner(module,x*w,z*d)) for x,z in [(-1,-1),(-1,1),(1,1),(1,-1)]],fill='#91e0c4' if module['interiorRequired'] else '#eed6b1')
    label({'x':v['x'],'z':v['z']+95},'Village: 20 building target')
    for trigger in zone['zoneTriggers']:
        label(trigger,'Arrival courtyard' if trigger['targetZoneId'].endswith('_capital') else 'Optional lair' if trigger['targetZoneId'].endswith(('_hollow','_pit','_den')) else 'Campaign route')
    draw.text((45,951),'Six supply itineraries: '+', '.join(str(row['lengthMetres'])+' m' for row in zone['orvrLayout']['caravanRoutes']),font=font(18),fill='#eee8d3')
    draw.text((45,990),'Authoring diagram. Native art, furnished villages and live 18v18 acceptance remain pending.',font=font(18),fill='#cecbb9')
    image.save(DIRECTORY/(identity+'_topology.png'))

    image=Image.new('RGB',(1400,1050),'#172227');draw=ImageDraw.Draw(image)
    plan=json.loads((DIRECTORY/(identity+'_modules.json')).read_text())
    def local(row):return (475+(row['x']-v['x'])*2.8,530-(row['z']-v['z'])*2.8)
    draw.text((40,25),zone['name']+' — modular village plan',font=font(33),fill='#eee8d3')
    draw.text((40,77),plan['layout'],font=font(20),fill='#cecbb9')
    for path in zone['paths']:
        draw.line([local(row) for row in path['points']],fill='#565c58',width=round(path['width']*2.8),joint='curve')
    court=plan['arrivalCourt'];cx,cy=local(court['point']);radius=court['radius']*2.8
    draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill='#29405b',outline='#8cb8e1',width=2)
    draw.text((cx-radius+4,cy-15),'Arrival court',font=font(18),fill='#c7dff4')
    for module in modules:draw.line([local(row) for row in module['approach']],fill='#858763',width=3,joint='curve')
    for index,module in enumerate(modules):
        w,d=module['reservation']['width']/2,module['reservation']['depth']/2
        draw.polygon([local(corner(module,x*w,z*d)) for x,z in [(-1,-1),(-1,1),(1,1),(1,-1)]],fill='#91e0c4' if module['interiorRequired'] else '#eed6b1',outline='#263032',width=2)
        x,y=local(module);draw.text((x-8,y-12),str(index+1),font=font(17),fill='#172227')
        if module.get('practical'):
            x,y=local(module['practical']);draw.ellipse((x-3,y-3,x+3,y+3),fill='#ffd178')
    for item in plan['serviceReservations']:
        x,y=local(item['point']);draw.ellipse((x-5,y-5,x+5,y+5),fill='#79bfea' if item['kind']=='crafting' else '#dba8da')
    draw.rectangle((0,0,1399,110),fill='#172227')
    draw.rectangle((0,910,1399,1049),fill='#172227')
    draw.text((40,25),zone['name']+' — modular village plan',font=font(33),fill='#eee8d3')
    draw.text((40,77),plan['layout'],font=font(20),fill='#cecbb9')
    # A fixed legend keeps role names readable even when the assemblies are close together.
    draw.rectangle((970,110,1399,910),fill='#172227')
    for index,module in enumerate(modules):
        draw.text((990,125+index*35),f"{index+1:02}  "+module['role'].replace('_',' ').title(),font=font(20),fill='#91e0c4' if module['interiorRequired'] else '#eed6b1')
    draw.text((40,946),'Gold dots: admitted fixture candidates   Blue: crafting   Purple: retained NPCs',font=font(19),fill='#cecbb9')
    draw.text((40,985),'Reserved footprints and walking links. Door/interior proof and visual approval remain pending.',font=font(19),fill='#cecbb9')
    image.save(DIRECTORY/(identity+'_village_plan.png'))

if __name__=='__main__':
    for identity in ['sunmeadow_march','brightfen_approach','cinderfen_outskirts','ashen_steppe']:render(identity)
