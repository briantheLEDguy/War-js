"""Labeled schematic of measured roof attachment datums; no licensed pixels."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'
native=json.loads((DIRECTORY/'shells-latest.json').read_text())
review=json.loads((DIRECTORY/'shell-seam-review.json').read_text())
if native['signature']!=review['signature'] or not review['seamRaysClosed']:
    raise RuntimeError('Roof drawing requires matching native seam witnesses')
folder=DIRECTORY/'shell-views'/native['signature'][:12]
image=Image.new('RGB',(1200,850),'#172227'); draw=ImageDraw.Draw(image)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
draw.text((30,20),'Modular home roofs — attachment datum',font=font(30),fill='#e9e5d7')
draw.text((30,64),'SCHEMATIC / offsets exaggerated / native pictures and LOD0 rays provide separate evidence',font=font(18),fill='#c7c9bb')
for x,corrected in [(30,False),(630,True)]:
    draw.rounded_rectangle((x,115,x+540,690),radius=12,fill='#202f35')
    draw.text((x+24,133),'REFIT' if corrected else 'PARENT',font=font(26),fill='#91e0c4' if corrected else '#efbf8c')
    wall_y=480; eave_y=wall_y if corrected else wall_y-60
    draw.rectangle((x+80,wall_y,x+235,610),fill='#747b72',outline='#e9ddc3',width=3)
    draw.polygon([(x+65,eave_y),(x+350,eave_y-235),(x+382,eave_y-208),(x+95,eave_y+20)],fill='#647584',outline='#cbd9e8')
    draw.line((x+40,wall_y,x+480,wall_y),fill='#91e0c4',width=2)
    draw.text((x+250,wall_y+10),'Wall top / eave datum',font=font(18),fill='#91e0c4')
    draw.text((x+24,187),'Roof pivot seated on wall' if corrected else 'Bounds skirt used as pivot',font=font(20),fill='#e9e5d7')
    if not corrected:
        draw.line((x+250,eave_y,x+250,wall_y),fill='#efbf8c',width=4)
        draw.text((x+265,eave_y+10),'15 cm lift',font=font(21),fill='#efbf8c')
    draw.text((x+24,630),'Sampled open eave rays: '+str(review['openRefitRays'] if corrected else review['openParentRays']),font=font(22),fill='#e9e5d7')
draw.text((30,719),'Main roof: -15 cm    Porch: -10 cm    Chimney follows roof    Walls, doors and floors unchanged',font=font(21),fill='#e9e5d7')
draw.text((30,766),'Four furnished homes / first terrain pair / regional appearance and distant roof LODs unapproved',font=font(18),fill='#c7c9bb')
output=folder/'roof_attachment_schematic.png';image.save(output)
print(output)
