"""Freeze the final generation inputs and per-LOD construction receipts."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];KEY='frontier_field_command_table'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
paths=list((ROOT/'tools').glob('*.py'))+list((ROOT/'tools').glob('*.mjs'))+list((ROOT/'textures').glob('*'))
lods=[]
for level in(0,1,2):
    receipt=ROOT/'review'/f'{KEY}_lod{level}_build.json';record=json.loads(receipt.read_text());paths.append(receipt)
    for source in record['sourceFiles']:
        assert sha(ROOT/source['path'])==source['sha256'],f'Generation input changed since export: {source["path"]}'
    lods.append(record)
paths.extend([ROOT/'provenance.json',ROOT/'builder-contract.json',ROOT/'review/master-audit.json',ROOT/'review/construction-contacts.json'])
paths.extend(ROOT/'review'/f'{KEY}_lod{level}_finished-parts.json' for level in(0,1,2))
record={'key':KEY,'assetId':'prop.frontier.field_command_table','displayName':'Field Command Table','status':'technical_review_pending','sourceFiles':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(paths)) if p.is_file()],'lods':lods}
target=ROOT/'review'/f'{KEY}_build.json';target.write_text(json.dumps(record,indent=2)+'\n');print('COMMAND_TABLE_BUILD_CONSOLIDATED',[(r['level'],r['triangles']) for r in lods])
