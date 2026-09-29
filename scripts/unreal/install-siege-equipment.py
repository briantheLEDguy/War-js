"""Install reviewed convoy assets and ownership standards in the isolated Scenario map."""
import hashlib,json,shutil,time
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/siege/equipment';BASE='/Game/Siege/Equipment'
native=json.loads((OUT/'native.json').read_text());acceptance=json.loads((OUT/'review/acceptance.json').read_text())
if acceptance.get('reviewed') is not True or acceptance.get('nativeSha256')!=hashlib.sha256((OUT/'native.json').read_bytes()).hexdigest():
    raise RuntimeError('Review the current native equipment and grips before installation')
for name,digest in acceptance['frames'].items():
    if hashlib.sha256((OUT/'review'/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Changed review frame: '+name)
library=unreal.EditorAssetLibrary;levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
target='/Game/Capitals/Siege/AegisCapital_Siege'
source=ROOT/'unreal/AegisWar/Content/Capitals/Siege/AegisCapital_Siege.umap'
backup=OUT/'backups'/str(time.time_ns());backup.mkdir(parents=True)
shutil.copy2(source,backup/source.name)
if not levels.load_level(target):raise RuntimeError('Missing isolated Scenario map')
fields=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarSiegeBattlefield)]
if len(fields)!=1:raise RuntimeError('Expected one battlefield')
field=fields[0];definitions=[]
for name in ('Ram','Catapult'):
    definition=unreal.load_asset(native['assets'][name])
    if library.get_metadata_tag(definition,'WarSiegeEquipmentV1')!='1':raise RuntimeError('Unowned equipment')
    definition.set_editor_property('reviewed',True)
    if not library.save_loaded_asset(definition,False):raise RuntimeError('Save failed: '+name)
    definitions.append(definition)
standards=native['assets']['RiftboundStandard']
if len(standards)!=1:raise RuntimeError('Expected combined authored war standard')
mesh=unreal.load_asset(standards[0]);placements=list(field.get_editor_property('objectives'))+list(field.get_editor_property('optional_objectives'))
existing={a.get_actor_label():a for a in actors.get_all_level_actors()};bound=[]
for i,position in enumerate(placements):
    label=f'Siege_AttackerStandard_{i:02d}'
    actor=existing.get(label)
    if actor and 'WarSiegeEquipmentV1' not in [str(t) for t in actor.tags]:raise RuntimeError('Preserve unowned map actor '+label)
    if not actor:actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,position)
    actor.set_actor_label(label);actor.tags=['WarSiegeEquipmentV1'];actor.static_mesh_component.set_static_mesh(mesh)
    actor.set_actor_location(position+unreal.Vector(0,430,-10 if i<2 or i==8 else 0),False,True)
    # Show the Riftbound emblem to the attackers approaching along +X.
    actor.set_actor_rotation(unreal.Rotator(yaw=180),True)
    actor.set_actor_scale3d(unreal.Vector(.55,.55,.55));actor.set_actor_enable_collision(False);actor.set_actor_hidden_in_game(True)
    bound.append(actor)
field.set_editor_properties(dict(equipment_definitions=definitions,attacker_standards=bound))
if not levels.save_current_level():raise RuntimeError('Map save failed')
(OUT/'installation.json').write_text(json.dumps(dict(map=target,standards=len(bound),definitions=native['assets'],backup=str(backup),
    fullSiegeApproved=False),indent=2)+'\n')
unreal.log('WAR_SIEGE_EQUIPMENT_INSTALLED=2; ownership standards=11')
