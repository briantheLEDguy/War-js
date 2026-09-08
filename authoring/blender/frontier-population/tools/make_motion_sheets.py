"""Arrange hash-verified export renders without changing their image content."""
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

WORK=Path(__file__).resolve().parents[1]
key=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--asset=')),'frontier_sunmeadow_dwarf_artisan')
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report=json.loads((WORK/'review'/f'{key}_lod{lod}_motion_sheet.json').read_text())
if report['modelSha256']!=sha(WORK/'runtime'/f'{key}_lod{lod}.glb'):raise RuntimeError('Renders describe an older export')
results=[]
for name,clips in [('locomotion',['idle','walk','run']),('actions',['combat_idle','attack_melee','attack_ranged']),('response',['cast','death','jump'])]:
    canvas=Image.new('RGB',(1260,1590),(28,32,38));draw=ImageDraw.Draw(canvas)
    for row,clip in enumerate(clips):
        records=[record for record in report['images'] if record['clip']==clip]
        if len(records)!=3:raise RuntimeError('Expected three literal poses for '+clip)
        for col,record in enumerate(records):
            source=WORK/record['image'].replace('\\','/')
            if sha(source)!=record['sha256']:raise RuntimeError('Render hash changed: '+source.name)
            with Image.open(source) as image:canvas.paste(image.convert('RGB'),(col*420,row*530+30))
            draw.text((col*420+10,row*530+8),f'{clip} — {record["seconds"]:.3f} s',fill=(245,245,245))
    output=WORK/'review'/f'{key}_lod{lod}_{name}_sheet.png';canvas.save(output)
    results.append({'category':name,'image':output.name,'sha256':sha(output)})
(WORK/'review'/f'{key}_lod{lod}_sheets.json').write_text(json.dumps({'modelSha256':report['modelSha256'],'sheets':results,'visualApproval':False},indent=2))
