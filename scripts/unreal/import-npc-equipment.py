"""Bind existing authored weapons to placed combat NPCs without saving their levels."""
import hashlib
import datetime
import json
import shutil
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from world_build_assets import WorldAssets
from world_actor_state import transform

OUT = ROOT/'artifacts/unreal/npc-equipment'
CATALOG = '/Game/WorldRebuild/NpcEquipment/CombatLoadouts'
OWNER = 'WarNpcEquipmentSources'


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def package_file(asset):
    return ROOT/'unreal/AegisWar/Content'/(asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')


def main():
    exported = json.loads((OUT/'export.json').read_text())
    if digest(ROOT/'migration/npc-equipment-sources.json') != exported['sourcesSha256']:
        raise RuntimeError('Equipment source manifest changed')
    world_receipt = json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
    manifest = json.loads((ROOT/'artifacts/unreal/world-portals/zone-manifest.json').read_text())
    world_hashes = {world_receipt['map']:manifest['mainSha256'],**manifest['packageHashes']}
    for path, fingerprint in world_hashes.items():
        file=ROOT/'unreal/AegisWar/Content'/(path.removeprefix('/Game/')+'.umap')
        if digest(file)!=fingerprint: raise RuntimeError('Saved world changed; reconcile owner edits before equipment regeneration: '+path)
    world_fingerprint = hashlib.sha256(json.dumps(world_hashes,sort_keys=True).encode()).hexdigest()
    prior = json.loads((OUT/'import.json').read_text()) if (OUT/'import.json').exists() else None
    existing = unreal.load_asset(CATALOG) if unreal.EditorAssetLibrary.does_asset_exist(CATALOG) else None
    if existing:
        if not prior or digest(package_file(existing)) != prior['catalogSha256']:
            raise RuntimeError('Owner changed the equipment catalog; refusing regeneration')
        if (digest(OUT/'export.json') == prior['exportSha256'] and digest(Path(__file__))==prior.get('importToolSha256')
                and world_fingerprint==prior.get('worldFingerprint')):
            unreal.log('WAR_NPC_EQUIPMENT_UNCHANGED='+str(prior['combatActors']))
            return
        shutil.copy2(package_file(existing), OUT/('catalog-backup-'+prior['catalogSha256']+'.uasset'))
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(world_receipt['map']):
        raise RuntimeError('Main map unavailable')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    imports = json.loads((ROOT/'unreal/AegisWar/Content/Migration/visual-imports.json').read_text())['entries']
    asset_builder = WorldAssets(ROOT,'NpcEquipment_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    meshes = {}
    for key, row in exported['weapons'].items():
        if (digest(ROOT/row['source']) != row['sha256'] or digest(ROOT/row['geometry']) != row['geometrySha256']
                or digest(ROOT/row['glb']) != row['glbSha256']):
            raise RuntimeError('Equipment source changed: '+key)
        meshes[key] = asset_builder.composite(key,json.loads((ROOT/row['geometry']).read_text()),False)
    if not existing:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class',unreal.WarNpcEquipmentCatalog)
        existing = unreal.AssetToolsHelpers.get_asset_tools().create_asset('CombatLoadouts',CATALOG.rsplit('/',1)[0],
            unreal.WarNpcEquipmentCatalog,factory)
    bindings, records = [], []
    for actor in actors:
        if isinstance(actor,unreal.WarEnemy):
            profile = str(actor.get_editor_property('visual').get_editor_property('source_profile_key'))
            identity, role = str(actor.get_editor_property('enemy_id')), 'enemy'
        elif isinstance(actor,unreal.WarCityNpc):
            profile = str(actor.get_editor_property('character_profile'))
            identity, role = str(actor.get_editor_property('npc_id')), str(actor.get_editor_property('city_role'))
            if role not in ('guard','marshal'): continue
        else: continue
        mesh = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        native = mesh.get_skeletal_mesh_asset()
        candidates = [row for row in imports if row['skeletalMeshPath']==native.get_path_name()]
        if len(candidates)!=1: raise RuntimeError('Body lacks unique import provenance: '+identity)
        source = candidates[0]
        if digest(ROOT/source['sourceModel']) != source['sourceSha256']: raise RuntimeError('Body source changed')
        unreal.WarImportLibrary.prepare_preview_frame(mesh)
        binding = unreal.WarNpcLoadout()
        for name,value in dict(profile=profile,role=role,identities=[identity],body=native,
                               body_source_sha256=source['sourceSha256']).items(): binding.set_editor_property(name,value)
        if profile == 'npc_frontier_sunmeadow_high_elf_scout':
            # The source mesh already carries its recurve bow and quiver, weighted to the chest.
            binding.set_editor_property('embedded_weapon_material_slots',['scout_tool_bow_ash','scout_tool_quiver_leather'])
            keys=[]
        elif profile == 'npc_frontier_cinderfen_dark_elf_supply_officer' or role == 'marshal':
            keys=['officer_sidearm']
        elif profile == 'npc_aegis_ari_vell_brightfen_field_officer' and role == 'guard':
            keys=['patrol_spear','aegis_heater_shield']
        elif profile == 'enemy_aegis_campaign_raider_raider' and role == 'enemy': keys=['patrol_spear']
        else: raise RuntimeError('Combat identity requires an explicit loadout: '+identity)
        attachments=[]
        for key in keys:
            bone = 'hips' if key=='officer_sidearm' else 'hand_l' if key=='aegis_heater_shield' else 'hand_r'
            if not mesh.does_socket_exist(bone): raise RuntimeError('Required bone missing: '+bone)
            bone_world = mesh.get_socket_transform(bone,unreal.RelativeTransformSpace.RTS_WORLD)
            rotation = unreal.MathLibrary.compose_rotators(unreal.Rotator(yaw=90),mesh.get_world_rotation())
            if bone == 'hips':
                offset = unreal.MathLibrary.transform_location(mesh.get_world_transform(),unreal.Vector(27,-12,0))-mesh.get_world_location()
                position = bone_world.translation+offset+unreal.Vector(0,0,12)
            else:
                side=bone[-1]
                knuckles=(mesh.get_socket_location('index_01_'+side)+mesh.get_socket_location('pinky_01_'+side))*.5
                position=bone_world.translation*.25+knuckles*.75
            relative=unreal.MathLibrary.make_relative_transform(unreal.Transform(location=position,rotation=rotation),bone_world)
            attachment=unreal.WarNpcWeaponAttachment()
            for name,value in dict(id=key,bone=bone,mesh=meshes[key],relative_transform=relative,
                                   source_sha256=exported['weapons'][key]['sha256']).items():
                attachment.set_editor_property(name,value)
            attachments.append(attachment)
        binding.set_editor_property('attachments',attachments)
        bindings.append(binding)
        records.append({'id':identity,'profile':profile,'role':role,'body':native.get_path_name(),
                        'weapons':keys or ['embedded_recurve_bow_and_quiver'],
                        'attachments':[{'bone':str(a.get_editor_property('bone')),
                            'relativeTransform':transform(a.get_editor_property('relative_transform'))} for a in attachments]})
    if not records: raise RuntimeError('No combat NPCs found')
    existing.set_editor_property('loadouts',bindings)
    unreal.EditorAssetLibrary.set_metadata_tag(existing,OWNER,exported['sourcesSha256'])
    unreal.EditorAssetLibrary.set_metadata_tag(existing,'NativeArtApproved','false')
    if not unreal.EditorAssetLibrary.save_loaded_asset(existing,False): raise RuntimeError('Catalog save failed')
    (OUT/'import.json').write_text(json.dumps({'schemaVersion':1,'exportSha256':digest(OUT/'export.json'),'importToolSha256':digest(Path(__file__)),
        'catalog':existing.get_path_name(),'catalogSha256':digest(package_file(existing)),'worldFingerprint':world_fingerprint,
        'combatActors':len(records),'records':records,'nativeArtApproved':False},indent=2)+'\n')
    unreal.log('WAR_NPC_EQUIPMENT_IMPORTED='+str(len(records)))


if __name__ == '__main__': main()
