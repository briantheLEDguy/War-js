"""Apply only surveyed Aegis replacements and admit exact untouched legacy drafts."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import digest,require_unchanged
from capital_expansion_proof import placement_transform
from capital_expansion_materials import ExpansionMaterials
from world_actor_state import snapshot
OUT=ROOT/'artifacts/unreal/capital-expansion'
CONTENT=ROOT/'unreal/AegisWar/Content'


def sha(file): return hashlib.sha256(file.read_bytes()).hexdigest()
def package_file(p): return CONTENT/(p.removeprefix('/Game/')+'.umap')


def main():
    plan=json.loads((OUT/'replacement-plan.json').read_text())
    require_unchanged(plan['signature'],digest({k:v for k,v in plan.items() if k!='signature'}))
    assets=json.loads((OUT/'assets.json').read_text())
    require_unchanged(plan['assetsSha256'],sha(OUT/'assets.json'))
    receipt=json.loads((OUT/'applied.json').read_text())
    for p,expected in receipt['packageHashes'].items(): require_unchanged(expected,sha(package_file(p)))
    finished=OUT/'replacements.json'
    if finished.exists():
        require_unchanged(json.loads(finished.read_text())['planSignature'],plan['signature'])
        unreal.log('WAR_CAPITAL_REPLACEMENTS_ALREADY_APPLIED');return
    require_unchanged(plan['packageHashes'],receipt['packageHashes'])
    draft=ROOT/'unreal/AegisWar/Saved/WorldEdit/crownward-draft.json'
    require_unchanged(plan['ownerDraftSha256'],sha(draft) if draft.exists() else None)
    rows=plan['replacements']
    if len(rows)!=60 or len({r['id'] for r in rows})!=60 or len({r['recipe'] for r in rows})<12:
        raise RuntimeError('Review the surveyed replacement count and variety')
    baseline=json.loads((OUT/'baseline.json').read_text())['aegis_capital']
    for row in rows:
        require_unchanged(row['package'],baseline['levels']['authored'])
        template=assets['templates'][row['recipe']]
        require_unchanged(template['sha256'],sha(CONTENT/(template['mesh'].split('.')[0].removeprefix('/Game/')+'.uasset')))
    migration_file=CONTENT/'Migration/capital-expansion-replacements.json'
    if migration_file.exists(): raise RuntimeError('Preserve an existing replacement admission file')
    build=json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
    level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level.load_level(build['map']): raise RuntimeError('World missing')
    unreal.GameplayStatics.flush_level_streaming(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world())
    current={(a.get_outer().get_path_name().split('.')[0],a.get_name()):a
             for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
    for row in rows: require_unchanged(row['before'],snapshot(current[(row['package'],row['actor'])]))
    backup=OUT/('before-replacements-'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir()
    package=baseline['levels']['authored'];shutil.copy2(package_file(package),backup/package_file(package).name)
    manifest_file=ROOT/'artifacts/unreal/world-portals/zone-manifest.json'
    shutil.copy2(manifest_file,backup/'zone-manifest.json');shutil.copy2(OUT/'applied.json',backup/'applied.json')
    manifest=json.loads(manifest_file.read_text())
    palette=ExpansionMaterials('/Game/LicensedKits/CapitalExpansion/V1/Palettes')
    edited=[];admissions=[]
    for row in rows:
        actor=current[(row['package'],row['actor'])];template=assets['templates'][row['recipe']]
        hidden=bool(actor.get_editor_property('hidden'))
        actor.static_mesh_component.set_static_mesh(unreal.load_asset(template['mesh']))
        actor.static_mesh_component.set_editor_property('override_materials',[])
        actor.static_mesh_component.set_collision_profile_name('BlockAll')
        for box in actor.get_components_by_class(unreal.BoxComponent): box.set_collision_profile_name('NoCollision')
        for slot in range(actor.static_mesh_component.get_num_materials()):
            source=actor.static_mesh_component.get_material(slot)
            role=next((r for r in ('wall','roof','floor','trim') if 'mi_'+r+'_' in source.get_name().lower()),'original')
            actor.static_mesh_component.set_material(slot,palette.material(source,row['district'],role))
        location=placement_transform(row,template,baseline['origin'])
        actor.set_actor_scale3d(unreal.Vector(1,1,1))
        actor.set_actor_location_and_rotation(unreal.Vector(*location),unreal.Rotator(yaw=row['yaw']),False,True)
        fingerprint=digest({'mesh':template['sha256'],'district':row['district'],'paletteVersion':1})
        actor.tags=[str(t) for t in actor.tags if not str(t).startswith('WarModelSha256_')]+['WarModelSha256_'+fingerprint,'WarCapitalReplacementV1']
        edited.append({**row,'after':snapshot(actor)})
        admissions.append({'id':row['id'],'previousTransform':row['previousTransform'],'previousHidden':hidden,
                           'previousSourceIdentity':row['previousSourceIdentity'],
                           'currentSourceIdentity':template['mesh']+':'+fingerprint})
    result={'schemaVersion':1,'planSignature':plan['signature'],'backup':str(backup),'edits':edited,
            'ownerDraftSha256':plan['ownerDraftSha256'],'admissions':admissions}
    (OUT/'replacement-journal.json').write_text(json.dumps(result,indent=2)+'\n')
    if not level.set_current_level_by_name(package.rsplit('/',1)[1]) or not level.save_current_level():
        raise RuntimeError('Replacement save failed; inspect recovery journal')
    receipt['packageHashes'][package]=sha(package_file(package));manifest['packageHashes'][package]=receipt['packageHashes'][package]
    migration_file.write_text(json.dumps({'schemaVersion':1,'replacements':admissions},indent=2)+'\n')
    (OUT/'applied.json').write_text(json.dumps(receipt,indent=2)+'\n')
    manifest_file.write_text(json.dumps(manifest,indent=2)+'\n')
    finished.write_text(json.dumps(result,indent=2)+'\n')
    require_unchanged(plan['ownerDraftSha256'],sha(draft) if draft.exists() else None)
    unreal.log('WAR_CAPITAL_REPLACEMENTS_APPLIED='+str(len(edited)))


main()
