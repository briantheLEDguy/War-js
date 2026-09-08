"""Arrange unmodified GLB review renders with measured LOD labels."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'build-report.json').read_text())
width=1800;cell_width=600;cell_height=486
canvas=Image.new('RGB',(width,cell_height*len(report)),(29,32,31));draw=ImageDraw.Draw(canvas)
try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
except OSError:font=ImageFont.load_default()
for row,asset in enumerate(report):
    for lod in asset['lods']:
        image=Image.open(ROOT/'review'/f"{asset['asset_id']}_lod{lod['level']}_reimport.png").convert('RGB')
        image.thumbnail((600,434));x=lod['level']*cell_width;y=row*cell_height
        canvas.paste(image,(x+(cell_width-image.width)//2,y))
        label=asset['asset_id'].replace('frontier_sunmeadow_','').replace('_',' ')
        draw.text((x+15,y+437),f"{label} · LOD{lod['level']} · {lod['triangles']:,} tris",font=font,fill=(237,231,207))
canvas.save(ROOT/'review/all-exports.png')
print('Created review/all-exports.png from 18 actual GLB import views.')
