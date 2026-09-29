"""Bind the proposed six-class roster in the isolated, unapproved siege draft."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
TARGET = '/Game/Capitals/Siege/AegisCapital_Siege'
PROPOSED = (
    ('civic_sunfire_templar_m', unreal.WarRealm.AEGIS, unreal.WarSiegeRole.TANK),
    ('civic_battle_prelate_m', unreal.WarRealm.AEGIS, unreal.WarSiegeRole.HEALER),
    ('civic_ember_arcanist_m', unreal.WarRealm.AEGIS, unreal.WarSiegeRole.DAMAGE),
    ('mire_warbrute_m', unreal.WarRealm.RIFTBOUND, unreal.WarSiegeRole.TANK),
    ('riven_ruin_oracle_m', unreal.WarRealm.RIFTBOUND, unreal.WarSiegeRole.HEALER),
    ('riven_void_magister_m', unreal.WarRealm.RIFTBOUND, unreal.WarSiegeRole.DAMAGE),
)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(TARGET): raise RuntimeError('The isolated siege draft is missing')
definitions = [actor for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
               if isinstance(actor, unreal.WarSiegeBattlefield)]
if len(definitions) != 1: raise RuntimeError('Expected exactly one siege definition')
battlefield = definitions[0]
if battlefield.get_editor_property('traversal_reviewed') or battlefield.get_editor_property('equipped_roster_reviewed') or battlefield.get_editor_property('lower_city_reviewed'):
    raise RuntimeError('Draft staging cannot rewrite a reviewed battlefield')
entries, receipt = [], []
for profile, realm, role in PROPOSED:
    folder = '/Game/Characters/SiegeStaging/' if profile.startswith('riven_') else '/Game/MigrationProof/'
    visual = unreal.load_asset(folder+'Visual_'+profile)
    if not isinstance(visual, unreal.WarCharacterVisualDefinition) or str(visual.profile_key) != profile:
        raise RuntimeError('Required exact class visual is missing: '+profile)
    error = visual.validate_for_spawn(realm)
    if error: raise RuntimeError(profile+': '+error)
    entry = unreal.WarSiegeRosterEntry()
    entry.set_editor_properties(dict(realm=realm, combat_role=role, visual=visual))
    entries.append(entry)
    receipt.append(dict(profile=profile, realm=str(realm), role=str(role), visual=visual.get_path_name()))
existing = list(battlefield.get_editor_property('roster'))
def identity(entry):
    return tuple(str(entry.get_editor_property(field)) for field in ('realm', 'combat_role', 'visual'))
if existing and [identity(e) for e in existing] != [identity(e) for e in entries]:
    raise RuntimeError('Existing siege roster differs; preserve it for review')
battlefield.set_editor_property('roster', entries)
if not levels.save_current_level(): raise RuntimeError('Could not save the isolated roster draft')
output = ROOT/'artifacts/unreal/siege/roster-staging.json'
output.write_text(json.dumps(dict(map=TARGET, roster=receipt, equippedRosterReviewed=False,
    traversalReviewed=False, gameplayVerified=False), indent=2)+'\n', encoding='utf-8')
unreal.log('WAR_SIEGE_ROSTER_STAGED=6; no review or admission gate changed')
