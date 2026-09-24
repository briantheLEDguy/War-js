"""Publish hash-bound track removal provenance without retaining old payloads."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/animation-replacement'

def relative(value):
    path=Path(value)
    return (path.relative_to(ROOT) if path.is_absolute() else path).as_posix()

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    renames={relative(row['from']):relative(row['to']) for row in json.loads((OUT/'rest-rig-renames.json').read_text())}
    records={}
    sources=('source-track-removal.json','blend-track-removal.json','morph-track-removal.json','fbx-track-removal.json',
             'generator-separation.json','obsolete-file-removal-plan.json','obsolete-animation-binaries.json',
             'obsolete-generator-plan.json','obsolete-generator-copies.json','obsolete-review-map-files.json')
    for name in sources:
        for row in json.loads((OUT/name).read_text()):
            key=relative(row['path']); target=renames.get(key,key); path=ROOT/target
            entry=records.setdefault(key,dict(path=key,previousSha256=[],operation='removed'))
            for field in ('beforeSha256','sha256'):
                if row.get(field) and row[field] not in entry['previousSha256']: entry['previousSha256'].append(row[field])
            if path.exists():
                if row.get('preservationSha256') and digest(path)!=row['afterSha256']:
                    raise RuntimeError('Model changed since verified track removal: '+key)
                entry.update(operation='tracks_removed' if 'preservationSha256' in row else 'body_tool_separated',currentPath=target,currentSha256=digest(path))
                if row.get('preservationSha256'): entry['preservationSha256']=row['preservationSha256']
            elif row.get('afterSha256'): entry['previousSha256'].append(row['afterSha256'])
            for field in ('removedClips','removedActions'):
                if field in row: entry[field]=row[field]
    # Bind modified source-ledger helpers to their immutable Git version. This
    # permits removing old generation code without silently rewriting history.
    ledgers=set()
    for path in (ROOT/'scripts/blender-character-pipeline/data/approved-assets').glob('*.json'):
        provenance=json.loads(path.read_text()).get('provenance',{})
        if provenance.get('sourceLedger'): ledgers.add(provenance['sourceLedger'])
    for ledger in ledgers:
        directory=(ROOT/ledger).parent
        for name,evidence in json.loads((ROOT/ledger).read_text())['files'].items():
            path=(directory/name).resolve(); key=path.relative_to(ROOT).as_posix(); target=renames.get(key,key)
            if (ROOT/target).exists() and digest(ROOT/target)==evidence['sha256']: continue
            entry=records.get(key)
            if entry and evidence['sha256'] in entry['previousSha256']: continue
            original=subprocess.run(['git','show','HEAD:'+key],cwd=ROOT,capture_output=True,check=True).stdout
            if hashlib.sha256(original).hexdigest()!=evidence['sha256']:
                raise RuntimeError('Unaccounted historical source change: '+key)
            if not entry:
                if path.suffix not in ('.py','.dat'): raise RuntimeError('Missing model preservation receipt: '+key)
                entry=records.setdefault(key,dict(path=key,previousSha256=[],operation='body_tool_separated',currentPath=target,currentSha256=digest(ROOT/target)))
            entry['previousSha256'].append(evidence['sha256'])
    result=dict(schemaVersion=1,scope='Character animation replacement; model data and environmental animation retained',
                files=sorted(records.values(),key=lambda row:row['path']),nativeRemovalEvidence='artifacts/unreal/animation-replacement/native-animation-removal.json')
    (ROOT/'migration/animation-removal.json').write_text(json.dumps(result,indent=2)+'\n')
    print('WAR_ANIMATION_REMOVAL_PROVENANCE='+str(len(records)))

if __name__=='__main__': main()
