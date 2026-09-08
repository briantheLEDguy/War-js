"""Reimport only changed GLBs; never relabel an older render as current."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reviewer=ROOT/'tools/review_nature.py';tool_hash=sha(reviewer)
for path in sorted((ROOT/'review').glob('*_build.json')):
    built=json.loads(path.read_text());stale=[]
    for lod in built['lods']:
        evidence=ROOT/'review'/lod['model'].replace('.glb','_reimport.json')
        try:
            record=json.loads(evidence.read_text());valid=record['sha256']==sha(ROOT/'runtime'/lod['model']) and record['reviewer_sha256']==tool_hash
            valid=valid and all(sha(ROOT/'review'/v['image'])==v['sha256'] for v in record['views'].values())
        except (OSError,ValueError,KeyError):valid=False
        if not valid:stale.append(str(lod['level']))
    if stale:
        print('REIMPORT_CHANGED',built['asset_id'],stale,flush=True)
        subprocess.run(['C:/Program Files/Blender Foundation/Blender 5.0/blender.exe','--background','--python-exit-code','1','--threads','3','--python',str(reviewer),'--','--assets',built['asset_id'],'--lods',','.join(stale)],check=True)
    else:print('RETAINED_CURRENT_REIMPORT',built['asset_id'],flush=True)
