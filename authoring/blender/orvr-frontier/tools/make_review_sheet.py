"""Assemble verified exported-model renders; never infer visual approval."""
import hashlib
import json
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source=json.loads((ROOT/'source/frontier_collection.json').read_text())
    renders=json.loads((ROOT/'review/reimport_renders.json').read_text())['renders']
    validation=json.loads((ROOT/'review/package_validation.json').read_text())
    assets=list(source['assets'])+['frontier_draft_horse','frontier_caravan_reins','frontier_supply_officer_kit']
    if len(renders)!=len(assets)*3 or not validation['passed']: raise ValueError('Every current asset needs three clean reimports and passing binary validation')
    canvas=Image.new('RGB',(1800,len(assets)*484),(28,32,37)); draw=ImageDraw.Draw(canvas); inventory=[]
    for row,asset in enumerate(assets):
        report=json.loads((ROOT/'review'/f'{asset}_build.json').read_text()); lods=[]
        for level in (0,1,2):
            record=next(entry for entry in renders if entry['asset']==asset and entry['lod']==level)
            measured=next(entry for entry in report['lods'] if entry['level']==level)
            checked=next(entry for entry in validation['records'] if entry['assetId']==asset and entry['level']==level)
            filepath=ROOT/measured['path'].replace('\\','/'); image_path=ROOT/record['image'].replace('\\','/')
            if len({sha(filepath),record['glb_sha256'],measured['sha256'],checked['sha256']})!=1: raise ValueError(f'Stale model review: {asset}/{level}')
            if sha(image_path)!=record['image_sha256']: raise ValueError(f'Stale review image: {asset}/{level}')
            x=level*600; y=row*484
            draw.text((x+14,y+10),f"{source['assets'].get(asset,{}).get('name',asset)} | LOD{level}",fill=(232,221,197))
            canvas.paste(Image.open(image_path).convert('RGB').resize((600,450),Image.Resampling.LANCZOS),(x,y+34))
            lods.append({'level':level,'model':str(filepath.relative_to(ROOT)).replace('\\','/'),'sha256':measured['sha256'],
                         'triangles':measured['triangles'],'materials':checked['materials'],'bytes':measured['bytes'],
                         'bounds_z_up':measured.get('bounds_z_up'),'image':str(image_path.relative_to(ROOT)).replace('\\','/'),
                         'image_sha256':record['image_sha256'],'validation_errors':checked['errors'],'validation_warnings':checked['warnings']})
        inventory.append({'asset_id':asset,'master':report.get('master',report['lods'][0].get('master','')).replace('\\','/'),'master_sha256':report.get('master_sha256',report['lods'][0].get('master_sha256')),
                          'build_report':f'review/{asset}_build.json','lods':lods,'limitations':report.get('limitations',[])})
    sheet=ROOT/'review/final_lod_contact_sheet.png'; canvas.save(sheet,optimize=True)
    result={'source_sha256':sha(ROOT/'source/frontier_collection.json'),'technical_validation_passed':True,'visual_approval':False,
            'lifecycle':'review_pending','contact_sheet':str(sheet.relative_to(ROOT)).replace('\\','/'),'contact_sheet_sha256':sha(sheet),'assets':inventory}
    (ROOT/'review/final_inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'Verified {len(renders)} model/image/validation hash sets and wrote final review inventory.')


if __name__=='__main__': main()
