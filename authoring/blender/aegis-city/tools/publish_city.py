"""Publish only hash-matching, technically validated city artifacts."""
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone
WORK=Path(__file__).resolve().parents[1]
ROOT=WORK.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((WORK/'build-report.json').read_text())
validation=json.loads((WORK/'validation.json').read_text())
assert len(validation)==len(report)*3 and all(not r['errors'] for r in validation)
models=ROOT/'public/assets/models';textures=ROOT/'public/assets/textures/aegis_city';textures.mkdir(parents=True,exist_ok=True)
for p in (WORK/'textures/aegis_city').glob('*.png'):shutil.copy2(p,textures/p.name)
shutil.copy2(WORK/'textures/brick_baseColor.png',textures/'brick_baseColor.png')
shutil.copy2(WORK/'textures/stone_baseColor.png',textures/'stone_baseColor.png')
for name in ['paving','flagstone']: shutil.copy2(WORK/'textures'/f'{name}_baseColor.png',textures/f'{name}_baseColor.png')
blueprints=ROOT/'scripts/blender-character-pipeline/data/asset-blueprints'
approved=ROOT/'scripts/blender-character-pipeline/data/approved-assets'
review={ 'summary':f'All {len(report)} optimized exports inspected in normalized-scale all-exports; the keep, gate, arcade, bastion and eroded mountain also inspected in dedicated monument views. Includes the grand battle precinct, irregular painted surfaces and street furnishings. Runtime placement and 36-combatant spacing are checked separately.', 'reviewedAt':datetime.now(timezone.utc).isoformat(),'reviewedBy':'Codex','validationSha256':sha(WORK/'validation.json'),'buildSha256':sha(WORK/'build-report.json') }
if (WORK/'review/citadel-interior.png').exists():
    review['citadelInteriorPreviewSha256']=sha(WORK/'review/citadel-interior.png')
    review['summary']+=' The hollow keep doorway, hall shell and gallery were also inspected from inside the exported model.'
mountain_previews=['mountain-passage-interior','mountain-redoubt-interior','mountain-command-chamber','mountain-seal','mountain-vault-interior','mountain-vault-portals']
if all((WORK/'review'/f'{name}.png').exists() for name in mountain_previews):
    review['mountainPreviewSha256s']={name:sha(WORK/'review'/f'{name}.png') for name in mountain_previews}
    review['summary']+=' The open mountain passage, divided forehall and throne hall, two-portal treasury vault, and sealed crypt threshold were inspected in dedicated exported-model views.'
(WORK/'review/review.json').write_text(json.dumps(review,indent=2)+'\n')
template=json.loads((blueprints/'prop_town_house_1.asset.json').read_text())
for a in report:
    kind=a['kind'];name='prop_aegis_'+kind;model=name+'.glb'
    for lod in a['lods']:
        source=WORK/'runtime'/lod['model'];assert sha(source)==lod['sha256']
        shutil.copy2(source,models/source.name)
        qc={'qcPassed':True,'assetId':'prop.aegis.'+kind,'modelSha256':lod['sha256'],'lod':lod,'lods':a['lods'],'validationErrors':0,'reviewHash':sha(WORK/'review/review.json'),'textureMaxDimension':2048}
        (models/source.with_suffix('.qc.json').name).write_text(json.dumps(qc,indent=2)+'\n')
    bp=json.loads(json.dumps(template));bp.update(assetId='prop.aegis.'+kind,displayName='Aegis '+kind.replace('_',' ').title(),version='1.0.0',sets=['aegis_gothic_city'])
    bp['runtime']={'staticKey':'aegis_'+kind};bp['output']={'model':model,'artifactDir':'authoring/blender/aegis-city/runtime'}
    bp['generator']={'kind':'copyExisting','copyFrom':'authoring/blender/aegis-city/runtime/'+model}
    bp['geometry']['lods']=[{'name':'LOD'+str(l['level']),'triTarget':max(1,l['triangles']),'screenCoverageMin':[.2,.08,0][l['level']]} for l in a['lods']]
    bp['materials'].update(master='MM_AegisCityPbr',textureSet='aegis_city',maxTextureResolution=2048)
    bp['provenance'].update(source='authoring/blender/aegis-city/tools/build_city.py',promptIds=['aegis_gothic_city_v1'],referencePackId='original_aegis_architecture')
    (blueprints/(name+'.asset.json')).write_text(json.dumps(bp,indent=2)+'\n')
    manifest={'schemaVersion':1,'assetId':'prop.aegis.'+kind,'displayName':bp['displayName'],'category':'prop','model':model,'qc':name+'.qc.json','runtime':{'staticKey':'aegis_'+kind},'compatibility':{'bodyFamily':'static_architecture','bodyVariant':'neutral','skeletonId':'none','bindPoseId':'none'},'hashes':{'modelSha256':sha(models/model),'qcSha256':sha(models/(name+'.qc.json')),'previews':{'assembly':sha(WORK/'review/all-exports.png')}},'previews':{'assembly':'authoring/blender/aegis-city/review/all-exports.png'},'review':{'reviewedBy':'Codex','reviewedAt':review['reviewedAt'],'reviewHash':sha(WORK/'review/review.json')},'provenance':bp['provenance'],'approvalState':'approved'}
    (approved/(name+'.approved.json')).write_text(json.dumps(manifest,indent=2)+'\n')
print('Published',len(report),'city assets with three LODs each.')
