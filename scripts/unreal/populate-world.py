"""Add exact, already-imported source NPCs to the generated campaign layer."""
import hashlib
import datetime
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from world_build_assets import ground
from world_level_access import WorldLevelAccess
directory=ROOT/'artifacts/unreal/world-portals'
receipt=json.loads((directory/'build.json').read_text())
plan=json.loads((directory/'plan.json').read_text())
if hashlib.sha256((directory/'plan.json').read_bytes()).hexdigest()!=receipt['planSha256']: raise RuntimeError('Stale world plan')
profiles={row['profileKey'] for row in json.loads((ROOT/'unreal/AegisWar/Content/Migration/visual-imports.json').read_text())['entries']}
registry=json.loads((ROOT/'public/assets/models/asset-index.json').read_text())['characterProfiles']
identities={'npc_frontier_sunmeadow_empire_farmer':('empire',unreal.WarRealm.AEGIS),
    'npc_frontier_sunmeadow_empire_herbalist':('empire',unreal.WarRealm.AEGIS),
    'npc_frontier_sunmeadow_high_elf_scout':('high_elf',unreal.WarRealm.AEGIS),
    'npc_frontier_sunmeadow_dwarf_artisan':('dwarf',unreal.WarRealm.AEGIS),
    'npc_frontier_cinderfen_greenskin_peat_worker':('greenskin',unreal.WarRealm.RIFTBOUND),
    'npc_frontier_cinderfen_dark_elf_supply_officer':('dark_elf',unreal.WarRealm.RIFTBOUND)}
spec=importlib.util.spec_from_file_location('world_visuals',Path(__file__).with_name('prepare-proof.py'))
visuals=importlib.util.module_from_spec(spec);spec.loader.exec_module(visuals)
visuals.DESTINATION=receipt['layer'].rsplit('/',1)[0]+'/Characters'
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level(receipt['map']): raise RuntimeError('Main world unavailable')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
access=WorldLevelAccess(ROOT,receipt)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
unreal.WarImportLibrary.prepare_preview_frame(None)
existing={}
for actor in actors.get_all_level_actors():
    tags=[str(t) for t in actor.tags]
    if 'WarCampaignNpc' in tags:
        existing[str(actor.get_editor_property('npc_id'))]=actor
placed=[]
for zone in plan['zones']:
    if zone['id'] in ('aegis_capital','riftspire_capital'):continue
    source_file=ROOT/'public/assets/maps'/(zone['id']+'.json')
    if hashlib.sha256(source_file.read_bytes()).hexdigest()!=plan['sourceHashes'][zone['id']]:raise RuntimeError('Source map changed')
    source=json.loads(source_file.read_text())
    for row in source.get('npcs',[]):
        profile=row.get('characterProfileKey')
        if profile not in profiles or profile not in identities:continue
        prior=existing.get(row['id'])
        actor_class=unreal.WarQuestNpc if row['role']=='questgiver' else unreal.WarCityNpc
        if prior and isinstance(prior,actor_class) and 'WarCampaignNpcV2' in [str(t) for t in prior.tags]:continue
        access.select(zone['id'])
        if prior:actors.destroy_actor(prior)
        # Exact source identity; no substitution with another available character.
        race,realm=identities[profile]
        visual=visuals.visual(profile,race,'npc',realm,registry[profile]['bodyVariant'])
        if not unreal.EditorAssetLibrary.save_loaded_asset(visual,False):raise RuntimeError('Visual save failed')
        origin=zone['origin'];point=unreal.Vector(origin[0]+row['z']*100,origin[1]+row['x']*100,origin[2]+row.get('y',0)*100)
        floor=ground(world,point,5000)
        actor=actors.spawn_actor_from_class(actor_class,floor,unreal.Rotator(yaw=row.get('rotY',0)*180/math.pi))
        actor.set_actor_label(row['name']);actor.tags=['WarCampaignWorld','WarCampaignNpc','WarCampaignNpcV2',
            'WarZoneObject_'+zone['id']+'_Npc_'+row['id']]
        actor.set_editor_property('npc_id',row['id'])
        if row['role']=='questgiver':
            actor.set_editor_property('zone_id',zone['id']);actor.set_editor_property('visual',visual)
            mesh=actor.get_editor_property('mesh')
        else:
            actor.set_editor_property('display_name',row['name']);actor.set_editor_property('city_role',row['role'])
            actor.set_editor_property('character_profile',profile)
            mesh=actor.skeletal_mesh_component
        mesh.set_skeletal_mesh_asset(visual.skeletal_mesh)
        mesh.set_collision_profile_name('NoCollision')
        mesh.set_relative_transform(visual.mesh_transform,False,True)
        if isinstance(actor,unreal.WarCityNpc):
            # Population actors use the mesh as their root, unlike a quest NPC's child mesh.
            actor.set_actor_location(floor,False,True)
            actor.set_actor_rotation(unreal.Rotator(yaw=row.get('rotY',0)*180/math.pi-90),False)
        mesh.override_animation_data(visual.idle_animation,True,True,0,1)
        unreal.WarImportLibrary.prepare_preview_frame(mesh)
        center,extent,_=unreal.SystemLibrary.get_component_bounds(mesh)
        if not 100<extent.z*2<240:raise RuntimeError('Unexpected NPC height: '+profile)
        actor.set_actor_location(floor+unreal.Vector(0,0,floor.z-(center.z-extent.z)),False,True)
        placed.append({'zone':zone['id'],'id':row['id'],'kind':'npc','profile':profile,'role':row['role'],
            'interactionImplemented':row['role']=='questgiver'})
if placed:
    access.save({row['zone'] for row in placed})
    ids={(r['zone'],r['id']) for r in placed}
    receipt['gameplay']=[r for r in receipt['gameplay'] if (r['zone'],r['id']) not in ids]+placed
    receipt['pendingGameplay']=[r for r in receipt['pendingGameplay'] if (r['zone'],r['id']) not in ids]
    receipt['runtimeTraversalVerified']=False
    (directory/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
unreal.log('WAR_WORLD_NPCS_ADDED='+str(len(placed)))
