"""Apply surveyed room offsets and explicit low-output interior lighting."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import require_unchanged,digest,validate_plan,canonical_actor_state
from capital_expansion_proof import placement_transform,proof_config
from world_actor_state import snapshot
OUT=ROOT/'artifacts/unreal/capital-expansion'
CONTENT=ROOT/'unreal/AegisWar/Content'


def sha(file): return hashlib.sha256(file.read_bytes()).hexdigest()
def package_file(p): return CONTENT/(p.removeprefix('/Game/')+'.umap')


def main():
    survey=json.loads((OUT/'room-refit-plan.json').read_text())
    require_unchanged(survey['signature'],digest({k:v for k,v in survey.items() if k!='signature'}))
    receipt=json.loads((OUT/'applied.json').read_text())
    for p,expected in receipt['packageHashes'].items(): require_unchanged(expected,sha(package_file(p)))
    marker=OUT/'room-refits.json'
    if marker.exists():
        require_unchanged(json.loads(marker.read_text())['surveySignature'],survey['signature'])
        unreal.log('WAR_CAPITAL_ROOM_REFITS_ALREADY_APPLIED');return
    require_unchanged(survey['packageHashes'],receipt['packageHashes'])
    plan=json.loads((OUT/'plan.json').read_text());validate_plan(plan)
    require_unchanged(survey['planSignature'],plan['signature'])
    if survey['checked']!=24 or len(survey['refits'])!=len(survey['intrusions']): raise RuntimeError('Incomplete room clearance survey')
    changes={r['id']:r for r in survey['refits']}
    for i,row in enumerate(plan['placements']):
        if row['id'] in changes:
            new=changes[row['id']]
            for key in ('recipe','district','zone','interior','upperFloor'): require_unchanged(row[key],new[key])
            plan['placements'][i]=new
    plan.pop('signature');validate_plan(plan);plan['signature']=digest(plan)
    assets=json.loads((OUT/'assets.json').read_text());baseline=json.loads((OUT/'baseline.json').read_text())
    build=json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
    level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level.load_level(build['map']): raise RuntimeError('World missing')
    unreal.GameplayStatics.flush_level_streaming(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world())
    current={(a.get_outer().get_path_name().split('.')[0],a.get_name()):a
             for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
    added={r['id']:r for r in receipt['added']}
    for row in receipt['added']:
        require_unchanged(canonical_actor_state(row['state']),canonical_actor_state(snapshot(current[(row['package'],row['actor'])])))
    backup=OUT/('before-room-refits-'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir()
    for p in receipt['packageHashes']: shutil.copy2(package_file(p),backup/package_file(p).name)
    for name in ('applied.json','plan.json'): shutil.copy2(OUT/name,backup/name)
    manifest_path=ROOT/'artifacts/unreal/world-portals/zone-manifest.json'
    manifest=json.loads(manifest_path.read_text());shutil.copy2(manifest_path,backup/'zone-manifest.json')
    for identity,row in changes.items():
        record=added[identity];actor=current[(record['package'],record['actor'])]
        location=placement_transform(row,assets['templates'][row['recipe']],baseline[row['zone']]['origin'])
        actor.set_actor_location_and_rotation(unreal.Vector(*location),unreal.Rotator(yaw=row['yaw']),False,True)
        record['state']=snapshot(actor)
    for record in receipt['added']:
        if not record.get('attachedTo'): continue
        actor=current[(record['package'],record['actor'])]
        actor.light_component.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
        actor.light_component.set_editor_property('intensity',1800)
        actor.light_component.set_editor_property('source_radius',8)
        record['state']=snapshot(actor)
    receipt['planSignature']=plan['signature']
    (OUT/'room-refit-journal.json').write_text(json.dumps({'receipt':receipt,'plan':plan,'backup':str(backup)},indent=2)+'\n')
    for p in receipt['packageHashes']:
        if not level.set_current_level_by_name(p.rsplit('/',1)[1]) or not level.save_current_level(): raise RuntimeError('Room refit save failed')
        receipt['packageHashes'][p]=sha(package_file(p));manifest['packageHashes'][p]=receipt['packageHashes'][p]
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (OUT/'applied.json').write_text(json.dumps(receipt,indent=2)+'\n')
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    (CONTENT/'Migration/capital-expansion-proof.json').write_text(json.dumps(proof_config(plan,assets,baseline),indent=2)+'\n')
    marker.write_text(json.dumps({'surveySignature':survey['signature'],'planSignature':plan['signature'],
                                 'refits':list(changes),'lights':38,'lumensPerLight':1800},indent=2)+'\n')
    unreal.log('WAR_CAPITAL_ROOM_REFITS_APPLIED='+str(len(changes)))


main()
