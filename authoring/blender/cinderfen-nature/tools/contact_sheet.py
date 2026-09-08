"""Assemble unretouched actual-export review images with readable LOD labels."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
builds=[json.loads(p.read_text()) for p in sorted((ROOT/'review').glob('*_build.json'))]
for mode in ('neutral','gameplay'):
    canvas=Image.new('RGB',(1800,len(builds)*500),(32,34,33));draw=ImageDraw.Draw(canvas)
    for row,asset in enumerate(builds):
        for lod in asset['lods']:
            image=Image.open(ROOT/'review'/f"{asset['asset_id']}_lod{lod['level']}_{mode}.png").convert('RGB');image.thumbnail((594,440))
            x=lod['level']*600+(600-image.width)//2;y=row*500+40+(440-image.height)//2;canvas.paste(image,(x,y))
            label=asset['asset_id'].replace('frontier_cinderfen_','').replace('_',' ')+f" · LOD{lod['level']} · {lod['triangles']:,} tris"
            draw.text((lod['level']*600+12,row*500+10),label,font=font,fill=(235,233,219))
    canvas.save(ROOT/'review'/('all-exports.png' if mode=='neutral' else 'gameplay-exports.png'))
print('Actual-export contact sheets written.')
