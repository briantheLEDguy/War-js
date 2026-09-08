"""Label unchanged actual-export renders; composites retain their input hashes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def compose(kind):
    key='frontier_sunmeadow_'+kind;build_file=ROOT/'review'/f'{key}_build.json';build=json.loads(build_file.read_text());build_hash=sha(build_file)
    records=json.loads((ROOT/'review'/f'{key}_renders.json').read_text())['renders'];valid=[]
    for record in records:
        if record.get('build_sha256')!=build_hash or sha(ROOT/'runtime'/record['model'])!=record['model_sha256'] or sha(ROOT/record['image'])!=record['image_sha256']:continue
        if any(sha(ROOT/file)!=digest for file,digest in record['authored_files'].items()):continue
        valid.append(record)
    def find(lod,state,view='full'):
        return next((r for r in valid if r['level']==lod and r['state']==state and r['view']==view),None)
    groups={}
    lod_states=['rest','run@0.35','graze@0.5'] if kind.startswith('roe_deer') else ['rest']
    groups['lod_contact']=[find(lod,state) for state in lod_states for lod in range(3)]
    for clip in ['walk','run','graze','idle','sniff','hop','fly','attack','hit','death']:
        records=sorted([r for r in valid if r['level']==0 and r['view']=='profile' and r['state'].startswith(clip+'@')],key=lambda r:float(r['state'].partition('@')[2]))
        if records:groups[clip+'_contact']=records
    outputs=[]
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19);small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16)
    for group,records in groups.items():
        if not records or any(record is None for record in records):raise RuntimeError('Missing current exported renders for '+group)
        columns=3 if group=='lod_contact' else min(4,len(records));cell=350;caption=44;title=60;rows=math.ceil(len(records)/columns)
        sheet=Image.new('RGB',(columns*cell,rows*(cell+caption)+title),(24,29,35));draw=ImageDraw.Draw(sheet)
        draw.text((18,14),key.replace('frontier_sunmeadow_','').replace('_',' ')+' — '+group.replace('_',' '),font=font,fill=(241,235,220))
        for index,record in enumerate(records):
            image=Image.open(ROOT/record['image']).convert('RGB');image.thumbnail((cell,cell),Image.Resampling.LANCZOS)
            x=(index%columns)*cell;y=title+(index//columns)*(cell+caption)
            sheet.paste(image,(x+(cell-image.width)//2,y+(cell-image.height)//2))
            draw.text((x+10,y+cell+8),f"LOD{record['level']} · {record['state']} · {record['view']}",font=small,fill=(228,231,235))
        path=ROOT/'review'/f'{key}_{group}.png';sheet.save(path)
        outputs.append({'image':path.relative_to(ROOT).as_posix(),'image_sha256':sha(path),'kind':group,'inputs':[{'image':r['image'],'image_sha256':r['image_sha256'],'model':r['model'],'model_sha256':r['model_sha256'],'state':r['state'],'view':r['view'],'level':r['level']} for r in records]})
    if sha(build_file)!=build_hash:raise RuntimeError('Build changed while composing review')
    (ROOT/'review'/f'{key}_composites.json').write_text(json.dumps({'asset':key,'build_sha256':build_hash,'composer_sha256':sha(Path(__file__)),'composites':outputs},indent=2)+'\n')
    print('FAUNA_CONTACTS',key,len(outputs))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default='roe_deer_buck');args=parser.parse_args()
    for kind in args.assets.split(','):compose(kind)
