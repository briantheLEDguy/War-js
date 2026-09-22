"""Inspect the saved main world and list source coverage without granting acceptance."""
import hashlib
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_level_access import WorldLevelAccess
from world_zones import owner_zone

directory = ROOT/'artifacts/unreal/world-portals'
receipt = json.loads((directory/'build.json').read_text())
plan = json.loads((directory/'plan.json').read_text())
access = WorldLevelAccess(ROOT,receipt)
for package, expected in access.manifest['packageHashes'].items():
    file = ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Saved content changed; reconcile before updating coverage: '+package)
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(receipt['map']):
    raise RuntimeError('Main world unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
npcs, resources, enemies, tags, identities = {}, {}, {}, set(), set()
combat_equipment = []
for actor in actors:
    actor_tags = [str(tag) for tag in actor.tags]
    for tag in actor_tags:
        if tag.startswith('WarZoneObject_'):
            if tag in identities: raise RuntimeError('Duplicate stable campaign actor: '+tag)
            identities.add(tag)
    tags.update(actor_tags)
    equipment_role = 'enemy' if isinstance(actor,unreal.WarEnemy) else (
        str(actor.get_editor_property('city_role')) if isinstance(actor,unreal.WarCityNpc) else '')
    training_mesh = actor.get_editor_property('training_mesh') if isinstance(actor,unreal.WarEnemy) else None
    if training_mesh and training_mesh.static_mesh:
        equipment_role = ''
    if equipment_role in ('enemy','guard','marshal'):
        profile = str(actor.get_editor_property('visual').get_editor_property('source_profile_key')) if equipment_role=='enemy' else str(actor.get_editor_property('character_profile'))
        entity = str(actor.get_editor_property('enemy_id' if equipment_role=='enemy' else 'npc_id'))
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        error = unreal.WarNpcEquipmentLibrary.apply(component,profile,entity,equipment_role)
        if error != '': raise RuntimeError('Unarmed placed combat NPC: '+entity)
        combat_equipment.append({'id':entity,'profile':profile,'role':equipment_role,'nativeEquipped':True,'visualAcceptance':'pending'})
    if isinstance(actor,unreal.WarEnemy):
        key = (str(actor.get_editor_property('zone_id')),str(actor.get_editor_property('enemy_id')))
        if key in enemies: raise RuntimeError('Duplicate enemy identity')
        visual = actor.get_editor_property('visual')
        mesh = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        if training_mesh and training_mesh.static_mesh:
            enemies[key] = training_mesh.static_mesh.get_path_name()
        else:
            if not visual or not mesh or not mesh.get_skeletal_mesh_asset(): raise RuntimeError('Missing enemy visual')
            enemies[key] = str(visual.get_editor_property('profile_key'))
    if isinstance(actor,(unreal.WarCityNpc,unreal.WarQuestNpc,unreal.WarResourceNode)):
        point = actor.get_actor_location()
        zone = owner_zone(plan['zones'],[point.x,point.y,point.z])
        if isinstance(actor,unreal.WarResourceNode):
            key = (zone,str(actor.get_editor_property('node_id')))
            if key in resources: raise RuntimeError('Duplicate resource identity')
            resources[key] = actor.static_mesh_component.static_mesh is not None
        else:
            key = (zone,str(actor.get_editor_property('npc_id')))
            if key in npcs: raise RuntimeError('Duplicate NPC identity')
            component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
            if not component or not component.get_skeletal_mesh_asset(): raise RuntimeError('Missing placed NPC visual')
            npcs[key] = actor.get_class().get_name()

zones = []
for zone in access.manifest['zones']:
    identity = zone['id']
    source_file = ROOT/'public/assets/maps'/(identity+'.json')
    if hashlib.sha256(source_file.read_bytes()).hexdigest()!=zone['sourceSha256']:
        raise RuntimeError('Source zone changed: '+identity)
    source = json.loads(source_file.read_text())
    access.refresh_bindings(identity)
    for category in ('pendingScenery','pendingGameplay','pendingResources'):
        zone['outstanding'][category] = [row for row in receipt.get(category,[]) if row['zone']==identity]
    npc_rows = [{'id':row['id'],'profile':row.get('characterProfileKey'),'role':row['role'],
        'nativeActor':npcs.get((identity,row['id'])),
        'equipmentRequired':row['role']=='guard',
        'nativeEquipped':any(e['id']==row['id'] for e in combat_equipment),
        'behaviorAcceptance':'pending'} for row in source.get('npcs',[])]
    resource_rows = [{'id':row['id'],'visualPropId':row['visualPropId'],
        'nativePlaced':resources.get((identity,row['id']),False)} for row in source.get('resourceNodes',[])]
    # Placed raiders have a development melee lifecycle; source specials and navigation
    # remain explicit gates. Placement alone never grants behavioral acceptance.
    enemy_rows = [{'id':row['id'],'name':row['name'],
        'profile':row.get('characterProfileKey',row.get('assetKey')),
        'nativePlaced':(identity,row['id']) in enemies,
        'nativeEquipped':any(e['id']==row['id'] for e in combat_equipment),
        'behaviorAcceptance':'pending',
        'missing':(['visual-acceptance','network-combat-acceptance']
                   if (identity,row['id']) in enemies and row.get('assetKey') in ('dummy','riftspire_training_dummy') else
                   ['navigation','source-special-attack','visual-acceptance','network-combat-acceptance']
                   if (identity,row['id']) in enemies else
                   ['native-model-binding','AI-and-encounter','navigation','kill-attribution','death-and-respawn'])}
        for row in source.get('enemies',[])]
    mechanisms = [{'id':row['id'],'missing':'native-mechanism'} for row in source.get('props',[])
        if row.get('interaction') or row.get('interactionId') or row.get('kind')=='riftspire_lift']
    objectives = [{'id':row['id'],'missing':'native-authoritative-campaign-behavior'} for row in source.get('rvrObjectives',[])]
    zone['outstanding']['enemies'] = enemy_rows
    zone['outstanding']['mechanisms'] = mechanisms
    zone['outstanding']['objectives'] = objectives
    zones.append({'id':identity,'batch':zone['batch'],'npcs':npc_rows,'resources':resource_rows,
        'enemies':enemy_rows,'mechanisms':mechanisms,'objectives':objectives,
        'pendingScenery':zone['outstanding']['pendingScenery'],
        'acceptance':zone['acceptance'],'complete':False})

report = {'schemaVersion':1,'map':receipt['map'],'zones':zones,'stableCampaignActors':len(identities),
    'nativeNpcActors':len(npcs),'nativeResourceActors':len(resources),'nativeEnemyActors':len(enemies),'productionAccepted':False,
    'packageHashes':access.manifest['packageHashes'],'combatEquipment':combat_equipment}
(directory/'coverage.json').write_text(json.dumps(report,indent=2)+'\n')
(directory/receipt['partitionManifest']).write_text(json.dumps(access.manifest,indent=2)+'\n')
unreal.log('WAR_WORLD_COVERAGE='+json.dumps({key:report[key] for key in ('stableCampaignActors','nativeNpcActors','nativeResourceActors','nativeEnemyActors')}))
