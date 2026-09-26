"""Apply only a surveyed expansion, preserving and fingerprinting existing city actors."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from capital_expansion import ZONES, validate_plan, require_unchanged, rotate, digest, walking_route
from capital_expansion_materials import ExpansionMaterials
from world_actor_state import snapshot
OUT=ROOT/'artifacts/unreal/capital-expansion'
CONTENT=ROOT/'unreal/AegisWar/Content'


def sha(file): return hashlib.sha256(file.read_bytes()).hexdigest()
def package_file(p): return CONTENT/(p.removeprefix('/Game/')+'.umap')


from capital_expansion_proof import placement_transform, proof_config


def main():
    plan=json.loads((OUT/'plan.json').read_text());validate_plan(plan)
    baseline=json.loads((OUT/'baseline.json').read_text())
    assets=json.loads((OUT/'assets.json').read_text())
    require_unchanged(plan['baselineSha256'],sha(OUT/'baseline.json'))
    require_unchanged(plan['assetsSha256'],sha(OUT/'assets.json'))
    receipt_path=OUT/'applied.json'
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text())
        require_unchanged(receipt['planSignature'],plan['signature'])
        require_unchanged(receipt['packageHashes'],{p:sha(package_file(p)) for p in receipt['packageHashes']})
        unreal.log('WAR_EXPANSION_ALREADY_APPLIED');return
    # Check every original city package, not just the two receiving additions.
    for zone in ZONES:
        require_unchanged(baseline[zone]['hashes'],{p:sha(package_file(p)) for p in baseline[zone]['hashes']})
    for row in assets['templates'].values():
        path=CONTENT/(row['mesh'].split('.')[0].removeprefix('/Game/')+'.uasset')
        require_unchanged(row['sha256'],sha(path))
    directory=ROOT/'artifacts/unreal/world-portals'
    manifest_path=directory/'zone-manifest.json';manifest=json.loads(manifest_path.read_text())
    build=json.loads((directory/'build.json').read_text())
    zones={z['id']:z for z in manifest['zones']}
    level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not level.load_level(build['map']): raise RuntimeError('Official world missing')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    originals={}
    for zone in ZONES:
        packages=set(baseline[zone]['levels'].values())
        current={(a.get_outer().get_path_name().split('.')[0],a.get_name()):a for a in actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0] in packages}
        for row in baseline[zone]['actors']:
            if (row['package'],row['name']) not in current or snapshot(current[(row['package'],row['name'])])!=row['state']:
                raise RuntimeError('Existing actor changed: '+row['name'])
        originals[zone]=current
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=OUT/('before-apply-'+stamp);backup.mkdir()
    for zone in ZONES:
        for p in baseline[zone]['hashes']: shutil.copy2(package_file(p),backup/package_file(p).name)
    shutil.copy2(manifest_path,backup/'zone-manifest.json')
    materials=ExpansionMaterials('/Game/LicensedKits/CapitalExpansion/V1/Palettes')
    added=[];palette_edits=[]
    # New geometry belongs to the existing authored zone level and inherits its
    # existing streaming ownership. No startup-map or routing changes are needed.
    for row in plan['placements']:
        zone=row['zone'];template=assets['templates'][row['recipe']]
        package=baseline[zone]['levels']['authored']
        if not level.set_current_level_by_name(package.rsplit('/',1)[1]): raise RuntimeError('Authored level unavailable')
        location=placement_transform(row,template,baseline[zone]['origin'])
        actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*location),unreal.Rotator(yaw=row['yaw']))
        actor.set_actor_label(row['district'].replace('_',' ').title()+' '+row['recipe'].replace('_',' '))
        actor.set_folder_path('Capital expansion/'+row['district'])
        mesh=unreal.load_asset(template['mesh']);actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_collision_profile_name('BlockAll')
        for slot in range(actor.static_mesh_component.get_num_materials()):
            source=actor.static_mesh_component.get_material(slot)
            name=source.get_name().lower()
            role=next((r for r in ('wall','roof','floor','trim') if 'mi_'+r+'_' in name),
                      ('wall' if slot%3==0 else 'roof' if slot%3==1 else 'trim') if not row['interior'] else 'original')
            actor.static_mesh_component.set_material(slot,materials.material(source,row['district'],role))
        fingerprint=digest({'mesh':template['sha256'],'district':row['district'],'paletteVersion':1})
        actor.tags=['WarCapitalBuilding','WarCapitalExpansionV1','WarWorldObject_'+row['id'],'WarModelSha256_'+fingerprint]
        added.append({'id':row['id'],'zone':zone,'actor':actor.get_name(),'package':package,'state':snapshot(actor)})
        if row['interior']:
            for floor in range(2 if row['upperFloor'] else 1):
                x,y=rotate(0,template['roomSize'][1]/2-100,row['yaw'])
                lamp=actors.spawn_actor_from_class(unreal.PointLight,
                    unreal.Vector(location[0]+x,location[1]+y,location[2]+245+floor*300))
                lamp.set_actor_label(row['id']+' warm interior light '+str(floor))
                lamp.tags=['WarCapitalExpansionV1']
                lamp.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
                lamp.light_component.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
                lamp.light_component.set_editor_property('intensity',1800)
                lamp.light_component.set_editor_property('attenuation_radius',900)
                lamp.light_component.set_editor_property('use_temperature',True)
                lamp.light_component.set_editor_property('temperature',3200)
                lamp.light_component.set_editor_property('cast_shadows',False)
                added.append({'id':row['id']+'_light_'+str(floor),'zone':zone,'actor':lamp.get_name(),'package':package,'state':snapshot(lamp)})
    # Existing buildings retain their mesh, transform, identity, collision and GM
    # draft provenance. Only their component materials change by district.
    source=json.loads((ROOT/'public/assets/maps/aegis_capital.json').read_text())
    for actor in originals['aegis_capital'].values():
        if not isinstance(actor,unreal.StaticMeshActor): continue
        component=actor.static_mesh_component;mesh=component.static_mesh
        if not mesh or '/Crownward/SM_MH_02_House_' not in mesh.get_path_name(): continue
        point=actor.get_actor_location()
        district=min(source['cityDistricts'],key=lambda d:(d['x']*100-point.y)**2+(d['z']*100-point.x)**2)['id']
        before=snapshot(actor)
        for slot in range(component.get_num_materials()):
            # Reuse the mesh's shared source, not per-house appearance overrides.
            material=mesh.get_material(slot)
            while isinstance(material,unreal.MaterialInstanceConstant) and '/LicensedKits/' in material.get_path_name():
                material=material.get_editor_property('parent')
            component.set_material(slot,materials.material(material,district,('wall','roof','trim')[slot%3]))
        palette_edits.append({'actor':actor.get_name(),'package':actor.get_outer().get_path_name().split('.')[0],'before':before,'after':snapshot(actor)})
    edited={(r['package'],r['actor']) for r in palette_edits}
    for zone in ZONES:
        for row in baseline[zone]['actors']:
            if zone=='aegis_capital' and (row['package'],row['name']) in edited: continue
            require_unchanged(row['state'],snapshot(originals[zone][(row['package'],row['name'])]))
    journal={'schemaVersion':1,'planSignature':plan['signature'],'backup':str(backup),'added':added,
             'paletteEdits':palette_edits,'packageHashes':{},'visualApproved':False,'traversalVerified':False}
    # Persist the recovery journal before saving any city package.
    (OUT/'apply-journal.json').write_text(json.dumps(journal,indent=2)+'\n')
    for zone in ZONES:
        p=baseline[zone]['levels']['authored']
        if not level.set_current_level_by_name(p.rsplit('/',1)[1]) or not level.save_current_level():
            raise RuntimeError('City save failed; inspect recovery journal')
        journal['packageHashes'][p]=sha(package_file(p))
        manifest['packageHashes'][p]=journal['packageHashes'][p]
        zones[zone]['actorCount']+=sum(r['zone']==zone for r in added)
        zones[zone]['acceptance']['visual']='pending';zones[zone]['acceptance']['traversal']='pending'
        (OUT/'apply-journal.json').write_text(json.dumps(journal,indent=2)+'\n')
    manifest.pop('traversalEvidence',None)
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    receipt_path.write_text(json.dumps(journal,indent=2)+'\n')
    (CONTENT/'Migration/capital-expansion-proof.json').write_text(json.dumps(proof_config(plan,assets,baseline),indent=2)+'\n')
    unreal.log('WAR_EXPANSION_APPLIED='+str(len(added)))


main()
