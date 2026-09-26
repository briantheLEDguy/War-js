"""Apply the tested landing-clearance revision to expansion-owned actors only."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import digest,require_unchanged,validate_plan,rotate
from capital_expansion_materials import ExpansionMaterials
from capital_expansion_proof import placement_transform,proof_config
from world_actor_state import snapshot
OUT=ROOT/'artifacts/unreal/capital-expansion'
CONTENT=ROOT/'unreal/AegisWar/Content'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def package_file(path): return CONTENT/(path.removeprefix('/Game/')+'.umap')


def main():
    receipt=json.loads((OUT/'applied.json').read_text())
    for package,expected in receipt['packageHashes'].items(): require_unchanged(expected,sha(package_file(package)))
    marker=OUT/'interior-revision.json'
    if marker.exists():
        require_unchanged(json.loads(marker.read_text())['assetsSha256'],sha(OUT/'assets.json'))
        unreal.log('WAR_EXPANSION_INTERIORS_ALREADY_REVISED');return
    plan=json.loads((OUT/'plan.json').read_text());validate_plan(plan)
    assets=json.loads((OUT/'assets.json').read_text())
    baseline=json.loads((OUT/'baseline.json').read_text())
    backup=OUT/'before-interior-revision'
    old_assets=json.loads((backup/'assets.json').read_text())
    require_unchanged(plan['assetsSha256'],sha(backup/'assets.json'))
    for row in plan['placements']:
        old,new=old_assets['templates'][row['recipe']],assets['templates'][row['recipe']]
        if not row['interior']: require_unchanged(old,new)
        if any(abs(a-b)>.01 for a,b in zip(old['origin']+old['extent'],new['origin']+new['extent'])):
            raise RuntimeError('Revision changed a surveyed footprint: '+row['recipe'])
        require_unchanged(new['sha256'],sha(CONTENT/(new['mesh'].split('.')[0].removeprefix('/Game/')+'.uasset')))
    build=json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
    level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level.load_level(build['map']): raise RuntimeError('World missing')
    unreal.GameplayStatics.flush_level_streaming(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world())
    current={(a.get_outer().get_path_name().split('.')[0],a.get_name()):a
             for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
    added={r['id']:r for r in receipt['added']}
    for r in receipt['added']: require_unchanged(r['state'],snapshot(current[(r['package'],r['actor'])]))
    manifest_path=ROOT/'artifacts/unreal/world-portals/zone-manifest.json'
    manifest=json.loads(manifest_path.read_text())
    for p in receipt['packageHashes']:
        target=backup/package_file(p).name
        if target.exists(): raise RuntimeError('Inspect an unfinished interior revision before retrying')
        shutil.copy2(package_file(p),target)
    shutil.copy2(manifest_path,backup/'zone-manifest.json')
    materials=ExpansionMaterials('/Game/LicensedKits/CapitalExpansion/V1/Palettes')
    for row in plan['placements']:
        if not row['interior']: continue
        record=added[row['id']];actor=current[(record['package'],record['actor'])]
        template=assets['templates'][row['recipe']]
        actor.static_mesh_component.set_static_mesh(unreal.load_asset(template['mesh']))
        actor.static_mesh_component.set_editor_property('override_materials',[])
        for slot in range(actor.static_mesh_component.get_num_materials()):
            source=actor.static_mesh_component.get_material(slot)
            role=next((r for r in ('wall','roof','floor','trim') if 'mi_'+r+'_' in source.get_name().lower()),'original')
            actor.static_mesh_component.set_material(slot,materials.material(source,row['district'],role))
        fingerprint=digest({'mesh':template['sha256'],'district':row['district'],'paletteVersion':1})
        actor.tags=[str(t) for t in actor.tags if not str(t).startswith('WarModelSha256_')]+['WarModelSha256_'+fingerprint,'WarCapitalInterior']
        location=placement_transform(row,template,baseline[row['zone']]['origin'])
        actor.set_actor_location(unreal.Vector(*location),False,True)
        record['state']=snapshot(actor)
        for floor in range(2 if row['upperFloor'] else 1):
            lamp_record=added[row['id']+'_light_'+str(floor)]
            lamp=current[(lamp_record['package'],lamp_record['actor'])]
            x,y=rotate(template['roomSize'][0]/2-55,template['roomSize'][1]/4,row['yaw'])
            lamp.set_actor_location(unreal.Vector(location[0]+x,location[1]+y,location[2]+245+floor*300),False,True)
            if not lamp.attach_to_actor(actor,'',unreal.AttachmentRule.KEEP_WORLD,unreal.AttachmentRule.KEEP_WORLD,
                                        unreal.AttachmentRule.KEEP_WORLD,False): raise RuntimeError('Interior light attachment failed')
            lamp_record['state']=snapshot(lamp);lamp_record['attachedTo']=row['id']
    plan['assetsSha256']=sha(OUT/'assets.json');plan.pop('signature');plan['signature']=digest(plan)
    receipt['planSignature']=plan['signature']
    (OUT/'interior-revision-journal.json').write_text(json.dumps({'receipt':receipt,'plan':plan},indent=2)+'\n')
    for package in receipt['packageHashes']:
        if not level.set_current_level_by_name(package.rsplit('/',1)[1]) or not level.save_current_level():
            raise RuntimeError('Revision save failed; inspect the recovery journal')
        receipt['packageHashes'][package]=sha(package_file(package))
        manifest['packageHashes'][package]=receipt['packageHashes'][package]
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (OUT/'applied.json').write_text(json.dumps(receipt,indent=2)+'\n')
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    (CONTENT/'Migration/capital-expansion-proof.json').write_text(json.dumps(proof_config(plan,assets,baseline),indent=2)+'\n')
    marker.write_text(json.dumps({'assetsSha256':plan['assetsSha256'],'planSignature':plan['signature'],'interiors':24,'attachedLights':38},indent=2)+'\n')
    unreal.log('WAR_EXPANSION_INTERIORS_REVISED=24')


main()
