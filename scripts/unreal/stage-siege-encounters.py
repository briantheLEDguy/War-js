"""Stage explicit siege NPC adaptations; keep the saved battlefield review gates closed."""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/unreal/siege'
FOLDER = '/Game/Characters/SiegeStaging/'
TARGET = '/Game/Capitals/Siege/AegisCapital_Siege'
SOURCES = (
    ('crew_visual', 'npc_siege_riftbound_breach_engineer',
     '/Game/WorldRebuild/Zones_20260922_112247_385690/Characters/Visual_npc_frontier_cinderfen_greenskin_peat_worker'),
    ('guard_visual', 'npc_siege_bastion_garrison', '/Game/MigrationProof/Visual_civic_sunfire_templar_m'),
    ('commander_visual', 'npc_siege_bastion_commander', '/Game/MigrationProof/Visual_civic_battle_prelate_m'),
)
library = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(TARGET): raise RuntimeError('Missing isolated siege draft')
battlefields = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
               if isinstance(a, unreal.WarSiegeBattlefield)]
if len(battlefields) != 1: raise RuntimeError('Expected exactly one battlefield')
battlefield = battlefields[0]
if battlefield.get_editor_property('traversal_reviewed') or battlefield.get_editor_property('equipped_roster_reviewed') or battlefield.get_editor_property('lower_city_reviewed'):
    raise RuntimeError('Do not rewrite reviewed encounter content')
bindings = {r['profileKey']: r for r in json.loads((ROOT/'unreal/AegisWar/Content/Migration/visual-imports.json').read_text())['entries']}
rows = []
for field, profile, source_path in SOURCES:
    source = unreal.load_asset(source_path)
    if not isinstance(source, unreal.WarCharacterVisualDefinition): raise RuntimeError('Missing exact authored source: '+source_path)
    source_key = str(source.source_profile_key)
    if source_key in ('None', ''): source_key = str(source.profile_key)
    binding = bindings.get(source_key)
    if (not binding or source.source_sha256 != binding['sourceSha256']
        or hashlib.sha256((ROOT/binding['sourceModel']).read_bytes()).hexdigest() != binding['sourceSha256']):
        raise RuntimeError('Stale source binding: '+profile)
    path = FOLDER+'Visual_'+profile
    current = battlefield.get_editor_property(field)
    if current and current.get_path_name().split('.')[0] != path: raise RuntimeError('Preserve existing encounter assignment: '+field)
    if library.does_asset_exist(path):
        visual = unreal.load_asset(path)
        if library.get_metadata_tag(visual, 'WarSiegeEncounterSource') != source_path:
            raise RuntimeError('Preserve unowned encounter visual: '+path)
    else: visual = library.duplicate_asset(source_path, path)
    if not visual: raise RuntimeError('Cannot create '+profile)
    visual.set_editor_properties(dict(profile_key=profile, source_profile_key=source_key))
    if field == 'crew_visual':
        # The original is mounted directly on a city actor. A character's root
        # sits at its capsule centre, so place the same authored feet 96 cm below.
        transform = visual.mesh_transform
        transform.translation = unreal.Vector(0, 0, -96)
        visual.set_editor_property('mesh_transform', transform)
    error = visual.validate_for_spawn(unreal.WarRealm.RIFTBOUND if field == 'crew_visual' else unreal.WarRealm.AEGIS)
    if error: raise RuntimeError(profile+': '+error)
    library.set_metadata_tag(visual, 'WarSiegeEncounterSource', source_path)
    if not library.save_loaded_asset(visual, False): raise RuntimeError('Cannot save '+profile)
    battlefield.set_editor_property(field, visual)
    rows.append(dict(role=field, profile=profile, visual=visual.get_path_name(), sourceVisual=source_path,
        sourceProfile=source_key, sourceModel=binding['sourceModel'], sourceSha256=binding['sourceSha256']))
if not levels.save_current_level(): raise RuntimeError('Cannot save encounter draft')
(OUT/'encounter-staging.json').write_text(json.dumps(dict(map=TARGET, encounters=rows,
    equippedRosterReviewed=False, traversalReviewed=False, gameplayVerified=False), indent=2)+'\n')
unreal.log('WAR_SIEGE_ENCOUNTERS_STAGED=3; equipment and traversal review remain required')
