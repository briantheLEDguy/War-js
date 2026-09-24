"""Refresh current model admission hashes after verified track-only removal.

Historical review/source hashes stay in provenance. This preserves model-only
approval and explicitly withdraws the old embedded-motion evidence.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MODELS=ROOT/'public/assets/models'
rows=json.loads((ROOT/'artifacts/unreal/animation-replacement/source-track-removal.json').read_text())
changed={Path(row['path']).name:row for row in rows if row['path'].startswith('public/assets/models/') and (ROOT/row['path']).exists()}


def hash_file(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value): path.write_bytes((json.dumps(value,indent=2)+'\n').encode())


def update_model_record(record):
    if not isinstance(record,dict): return
    model=record.get('model'); row=changed.get(model)
    if row:
        if hash_file(MODELS/model)!=row['afterSha256']: raise RuntimeError('Source changed after removal: '+model)
        for field in ('modelSha256','sha256'):
            if record.get(field)==row['beforeSha256']: record[field]=row['afterSha256']
        if 'animationClips' in record: record['animationClips']=[]
    for key,value in list(record.items()):
        if key in ('provenance','sourceAnimationRemoval','sourceRecords'): continue
        if isinstance(value,dict): update_model_record(value)
        elif isinstance(value,list):
            for child in value: update_model_record(child)


for qc in MODELS.glob('*.qc.json'):
    record=json.loads(qc.read_text()); row=changed.get(record.get('model'))
    if not row: continue
    update_model_record(record)
    retired=record.setdefault('provenance',{}).setdefault('retiredEmbeddedAnimationValidation',{})
    for field in ('animationAudit','requiredAnimationClips','nineAnimations'):
        if field in record: retired[field]=record.pop(field)
    checks=record.get('checks',{})
    for field in list(checks):
        if 'animation' in field.lower(): retired['checks.'+field]=checks.pop(field)
    record['fileSizeBytes']=(MODELS/record['model']).stat().st_size
    record['sourceAnimationRemoval']=dict(beforeSha256=row['beforeSha256'],afterSha256=row['afterSha256'],
        preservationSha256=row['preservationSha256'],removedClips=row['removedClips'],
        modelContentUnchanged=True,animationValidation='Native supplied-set evidence is separate')
    write(qc,record)

for manifest in (ROOT/'scripts/blender-character-pipeline/data/approved-assets').glob('*.json'):
    record=json.loads(manifest.read_text()); row=changed.get(record.get('model'))
    runtime=record.get('runtime',{}); removed={}
    for field in ('animationPack','operatorAnimationPacks'):
        if field in runtime: removed[field]=runtime.pop(field)
    if removed: record.setdefault('provenance',{})['retiredAnimationBindings']=removed
    if row:
        hashes=record.setdefault('hashes',{}); hashes['modelSha256']=row['afterSha256']
        hashes['qcSha256']=hash_file(MODELS/record['qc'])
        record.setdefault('provenance',{})['sourceAnimationRemoval']={k:row[k] for k in ('beforeSha256','afterSha256','preservationSha256','removedClips')}
    update_model_record(record)
    if row or removed: write(manifest,record)

index_path=MODELS/'asset-index.json'; index=json.loads(index_path.read_text())
def update_index(value):
    if isinstance(value,dict):
        value.pop('animationPack',None);value.pop('operatorAnimationPacks',None)
        row=changed.get(value.get('model'))
        if row:
            value['modelSha256']=row['afterSha256']
            if value.get('qc') and (MODELS/value['qc']).exists(): value['qcSha256']=hash_file(MODELS/value['qc'])
            if 'animationClips' in value:value['animationClips']=[]
        for child in value.values():update_index(child)
    elif isinstance(value,list):
        for child in value:update_index(child)
update_index(index);write(index_path,index)
print('WAR_UPDATED_MODEL_TRACK_PROVENANCE='+str(len(changed)))
