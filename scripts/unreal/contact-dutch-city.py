"""Private labelled review sheets from fresh native screenshots (Pillow required)."""
import argparse
import json
from PIL import Image, ImageDraw
from dutch_bastion import ROOT, OUT

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('group',type=int);parser.add_argument('--revision')
args=parser.parse_args()
current=json.loads((OUT/'city-current.json').read_text());run=OUT/(args.revision or current['revision'])
config_path=run/'proof-config.json';config=json.loads(config_path.read_text())
saved=ROOT/'unreal/AegisWar/Saved/DutchBastion'
sheet=Image.new('RGB',(1920,1320),'#161616');draw=ImageDraw.Draw(sheet)
for slot,index in enumerate(range(args.group*16,min((args.group+1)*16,len(config['views'])))):
    path=saved/f'view_{index:02d}.png'
    if not path.exists() or path.stat().st_mtime<config_path.stat().st_mtime:
        raise RuntimeError('Screenshot not fresh yet: '+str(path))
    picture=Image.open(path).convert('RGB');picture.thumbnail((480,300))
    x,y=(slot%4)*480,(slot//4)*330;sheet.paste(picture,(x,y))
    draw.text((x+5,y+304),str(index)+' '+config['views'][index]['id'],fill='white')
prefix='' if config.get('scope')=='whole_city' else config['scope']+'-'
target=run/f'{prefix}review-sheet-{args.group}.jpg';sheet.save(target,quality=90)
print(target)
