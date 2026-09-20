"""Retain the exact additional inputs read by the final read-only gate.

Run after current model reviews and geometry reports, before publication. The
original build source hashes stay untouched; validation evidence is separate.
"""
import hashlib,json
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];ROOT=WORK.parents[2]
KEY='frontier_sunmeadow_empire_field_captain'
build_path=WORK/'review'/f'{KEY}_build.json'
build=json.loads(build_path.read_text())
paths={WORK/'review/male-foundation.json',WORK/'review/master-continuity.json',
       WORK/'review/semantic-parts.json',WORK/'review/equipment-attachment-source.json',WORK/'review/shoulder-routing.json'}
provenance=json.loads((WORK/'foundation-provenance.json').read_text())
for row in provenance['inputs']:
    path=ROOT/row['retained']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Retained foundation changed')
    paths.add(path)
for lod in build['lods']:
    paths.add(WORK/lod['master'])
    review_path=WORK/'review'/f'{KEY}_lod{lod["level"]}_review_final.json'
    review=json.loads(review_path.read_text())
    if review['modelSha256']!=lod['sha256']:raise RuntimeError('Saved views do not match current build')
    paths.add(review_path)
    for image in review['images']:
        path=WORK/image['image']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=image['sha256']:raise RuntimeError('Saved image changed')
        paths.add(path)
paths.update((WORK/'tools').glob('*.py'))
records=[]
for path in sorted(paths):
    if not path.resolve().is_relative_to(WORK.resolve()):raise RuntimeError('Validation input escaped package')
    raw=path.read_bytes();records.append({'path':path.relative_to(ROOT).as_posix(),
        'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
build['validationSourceFiles']=records
build_path.write_text(json.dumps(build,indent=2)+'\n')
print(json.dumps({'status':'retained','validationInputs':len(records)}))
