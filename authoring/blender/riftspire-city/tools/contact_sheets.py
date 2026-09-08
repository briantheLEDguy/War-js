"""Assemble exported-model review frames without modifying their contents."""
from PIL import Image,ImageDraw
from pathlib import Path
import json
WORK=Path(__file__).resolve().parents[1]
kinds=[a['kind'] for a in json.loads((WORK/'build-report.json').read_text())]+['population_chaos','population_dark_elf','population_greenskin']
for page in range((len(kinds)+3)//4):
 sheet=Image.new('RGB',(1200,1400),(30,31,36));draw=ImageDraw.Draw(sheet)
 for row,kind in enumerate(kinds[page*4:page*4+4]):
  for lod in range(3):
   file=WORK/'review'/f'{kind}-lod{lod}.png'
   if not file.exists():continue
   im=Image.open(file);im.thumbnail((400,315));sheet.paste(im,(lod*400,row*350+25));draw.text((lod*400+12,row*350+8),f'{kind} / LOD{lod}',fill='white')
 sheet.save(WORK/'review'/f'contact-{page+1:02}.jpg',quality=95)
