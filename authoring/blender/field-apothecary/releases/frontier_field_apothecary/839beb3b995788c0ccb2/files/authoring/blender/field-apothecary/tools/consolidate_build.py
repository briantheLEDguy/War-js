"""Freeze the final generation inputs and per-LOD construction receipts."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KEY='frontier_field_apothecary'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
paths=list((ROOT/'tools').glob('*.py'))+list((ROOT/'tools').glob('*.mjs'))+list((ROOT/'textures').glob('*'))
lods=[]
for level in(0,1,2):
    receipt=ROOT/'review'/f'{KEY}_lod{level}_build.json';record=json.loads(receipt.read_text());paths.append(receipt)
    for source in record['sourceFiles']:
        assert sha(ROOT/source['path'])==source['sha256'],f'Generation input changed since export: {source["path"]}'
    lods.append(record)
paths.extend([ROOT/'builder-contract.json',ROOT/'review/master-audit.json'])
record={'key':KEY,'assetId':'prop.frontier.field_apothecary','displayName':'Field Apothecary Worktable','status':'technical_review_pending','sourceFiles':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(paths)) if p.is_file()],'lods':lods}
target=ROOT/'review'/f'{KEY}_build.json';target.write_text(json.dumps(record,indent=2)+'\n');print('APOTHECARY_BUILD_CONSOLIDATED',[(r['level'],r['triangles']) for r in lods])
