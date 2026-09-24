"""Fail on retired character payloads; retain environmental GLB animation."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import ROOT,OUT,SOURCE,CLIPS
from strip_character_tracks import decode
from storage_inventory import regular_files, retired_storage_failures

failures=[]; checked=0; environment=[]
for folder in ('public/assets/models','authoring','artifacts','tmp','blends'):
    for path in regular_files(ROOT/folder):
        if path.suffix.lower()!='.glb': continue
        document,_=decode(path.read_bytes()); checked+=1
        if document.get('animations'):
            if document.get('skins'):
                failures.append('Embedded character tracks: '+path.relative_to(ROOT).as_posix())
            else: environment.append(path.relative_to(ROOT).as_posix())
expected={Path(name).as_posix() for name in CLIPS.values()}
actual={p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*.fbx')}
if expected!=actual: failures.append('Supplied FBX inventory differs: '+str(expected^actual))
provenance=json.loads((ROOT/'migration/animation-removal.json').read_text())
storage_manifest=ROOT/'migration/model-storage-removal.json'
if storage_manifest.exists():
    failures.extend(retired_storage_failures(ROOT,json.loads(storage_manifest.read_text())))
for row in provenance['files']:
    if row['operation']=='removed':
        if (ROOT/row['path']).exists(): failures.append('Retired payload remains: '+row['path'])
    elif row.get('currentSha256'):
        path=ROOT/row['currentPath']
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['currentSha256']:
            failures.append('Changed removal evidence: '+row['currentPath'])
native=json.loads((OUT/'native-animation-removal.json').read_text())
for row in native['removed']:
    path=ROOT/'unreal/AegisWar/Content'/(row['path'].removeprefix('/Game/')+'.uasset')
    if path.exists(): failures.append('Retired native package remains: '+row['path'])
blend_receipts=[row for name in ('blend-track-removal.json','morph-track-removal.json')
                for row in json.loads((OUT/name).read_text())]
cleared={}
for row in blend_receipts: cleared.setdefault(row['path'],set()).update(row.get('removedActions',[]))
retained_authoring=[]
for row in json.loads((OUT/'blend-track-plan.json').read_text()):
    if not (ROOT/row['path']).exists(): continue
    for action in row['actions']:
        if action['name'] in cleared.get(row['path'],set()): continue
        if any(channel.startswith(('pose.bones[','key_blocks[')) for channel in action['channels']):
            failures.append('Unaccounted authoring character action: '+row['path']+':'+action['name'])
        else: retained_authoring.append(dict(path=row['path'],action=action['name']))
report=dict(passed=not failures,checkedGlbs=checked,suppliedFbxCount=len(actual),
            retainedEnvironmentalAnimations=environment,removedNativePackages=len(native['removed']),failures=failures,
            strippedCharacterBlendFiles=len(blend_receipts),
            strippedCharacterBlendBackups=sum(Path(row['path']).suffix!='.blend' for row in blend_receipts),
            retainedAuthoringMechanisms=retained_authoring,
            nativeRegistryEvidence='artifacts/unreal/animation-replacement/native-animation-removal-verification.json')
if storage_manifest.exists():
    report['storageRemovalManifestSha256']=hashlib.sha256(storage_manifest.read_bytes()).hexdigest()
(OUT/'removal-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('retainedEnvironmentalAnimations','retainedAuthoringMechanisms')}))
if failures: raise SystemExit(1)
