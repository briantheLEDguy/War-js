"""Install only the reviewed guard assets; preserve every existing registry entry."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--repo',type=Path,default=REPO)
    args=parser.parse_args(); repo=args.repo.resolve()
    build=json.loads((ROOT/'runtime/build-report.json').read_text())
    validation=json.loads((ROOT/'runtime/validation.json').read_text())
    review=json.loads((ROOT/'review/visual-review.json').read_text())
    grips=json.loads((ROOT/'review/exported-grip-audit.json').read_text())
    if grips['max_gap_m']>.015: raise ValueError('Exported weapon grip failed')
    for variant in ['standard','halberd','crossbow']:
        samples=[sample for sample in grips['samples'] if sample['variant']==variant]
        if len(samples)!=90 or {sample['hand'] for sample in samples}!={'L','R'}:
            raise ValueError(f'Incomplete exported grip audit: {variant}')
    for variant,model_hash in grips['models'].items():
        if sha(ROOT/'runtime'/f'chr_aegis_city_guard_{variant}.glb')!=model_hash: raise ValueError('Grip audit is stale')
    if validation['files']!=12 or validation['errors'] or review['status']!='reviewed': raise ValueError('Review/validation incomplete')
    for item in validation['results']:
        if sha(ROOT/'runtime'/item['file'])!=item['sha256']: raise ValueError('Export changed after validation')
    if review['validation_sha256']!=sha(ROOT/'runtime/validation.json'): raise ValueError('Review has stale validation')
    models=repo/'public/assets/models'
    preview=models/'reviews/aegis-city-guards'
    preview.mkdir(parents=True,exist_ok=True)
    for file in (ROOT/'review').glob('*.png'):
        if file.name.startswith('exported_') or '_grip_' in file.name or file.stem.endswith('_walk'): shutil.copy2(file,preview/file.name)
    for name in ['visual-review.json','exported-grip-audit.json']: shutil.copy2(ROOT/'review'/name,preview/name)
    manifests=repo/'scripts/blender-character-pipeline/data/approved-assets'
    index_path=models/'asset-index.json'; index=json.loads(index_path.read_text())
    for variant,lods in build['variants'].items():
        asset_id=f'chr.aegis.city_guard.{variant}'
        preview_path='reviews/aegis-city-guards/exported_idle_lineup.png'
        for lod,record in lods.items():
            file=ROOT/'runtime'/record['file']; shutil.copy2(file,models/file.name)
            checked=next(x for x in validation['results'] if x['file']==file.name)
            qc={'schemaVersion':1,'assetId':asset_id,'category':'character','model':file.name,
                'modelSha256':sha(file),'fileSizeBytes':file.stat().st_size,'lod':int(lod),
                'bodyFamily':'aegis_city_guard','bodyVariant':'m','skeletonId':'humanoid_game_v2','bindPoseId':'a_pose_v2',
                'totalTris':record['triangles'],'drawCalls':checked['primitives'],'meshCount':1,
                'animationClips':checked['animations'],'pbrChannels':['baseColor','metallic','roughness'],
                'maxTextureDimension':2048,'lifecycleStatus':'approved','reviewStatus':'approved',
                'khronosErrors':checked['issues']['numErrors'],'khronosWarnings':checked['issues']['numWarnings'],
                'qcPassed':checked['issues']['numErrors']==0,
                'gripAudit':'reviews/aegis-city-guards/exported-grip-audit.json',
                'previewImages':[preview_path], 'builtLods':[{'name':'LOD'+l,'model':r['file'],'sha256':r['sha256']} for l,r in lods.items()]}
            write(models/file.with_suffix('.qc.json').name,qc)
        record=lods['0']; model=record['file']; qc=model.replace('.glb','.qc.json'); profile='npc_aegis_city_guard_'+variant
        manifest={'schemaVersion':1,'assetId':asset_id,'displayName':'Aegis City Guard '+variant.title(),
            'category':'character','model':model,'qc':qc,'runtime':{'profileKey':profile},
            'compatibility':{'bodyFamily':'aegis_city_guard','bodyVariant':'m','skeletonId':'humanoid_game_v2','bindPoseId':'a_pose_v2'},
            'hashes':{'modelSha256':sha(models/model),'qcSha256':sha(models/qc),'previews':{'lineup':sha(preview/'exported_idle_lineup.png')}},
            'previews':{'lineup':preview_path},'approvalState':'approved',
            'review':{'reviewedBy':'Codex exported-model inspection (not user aesthetic approval)','reviewedAt':review['reviewedAt'],'reviewHash':sha(ROOT/'review/visual-review.json')},
            'provenance':{'sourcePackage':'authoring/blender/aegis-city-guards','referenceSha256':build['reference_sha256'],
                'sourceSha256':sha(ROOT/'source'/f'{variant}.json'),'validationSha256':sha(ROOT/'runtime/validation.json'),
                'geometry':'Adapted fitted armor cages, natural human head/neck and authored civic equipment; see derivation.json and anatomy/provenance.json',
                'limitations':'Simplified cloth, fur and feathers; patrol holds over canonical motion, no dedicated reload animation'}}
        write(manifests/model.replace('.glb','.approved.json'),manifest)
        index.setdefault('characterProfiles',{})[profile]={'assetId':asset_id,'model':model,'qc':qc,
            **manifest['compatibility'],'approvalState':'approved','lifecycleStatus':'approved','runtimeReady':True,
            'reviewStatus':'approved','modelSha256':manifest['hashes']['modelSha256'],'qcSha256':manifest['hashes']['qcSha256']}
        index['characterProfiles'][profile].update(previews=manifest['previews'],previewSha256=manifest['hashes']['previews'],review=manifest['review'])
    # Content version invalidates caches while retaining unrelated in-progress assets.
    payload={k:v for k,v in index.items() if k!='assetVersion'}
    index['assetVersion']='approved-'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]
    write(index_path,index)
    print('Installed 12 guard GLBs, QC, 4 manifests, and review evidence into',repo)


if __name__=='__main__': main()
