"""Publish the reviewed local lower-city content without approving the full siege."""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/unreal/siege'
TARGET = '/Game/Capitals/Siege/AegisCapital_Siege'
PROFILES = {'riven_ruin_oracle_m', 'riven_void_magister_m'}

def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))

review = read('artifacts/unreal/siege/development-review.json')
if review.get('scope') != 'local-lower-city' or review.get('equippedFramesReviewed') != 185:
    raise RuntimeError('The exact equipped development review is required')
for row in review['evidence']:
    if hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest() != row['sha256']:
        raise RuntimeError('Review evidence changed: '+row['path'])
native = read(review['nativeReport'])
if native['failed'] or native['notRun'] or native['inProcess']:
    raise RuntimeError('Native tests did not complete successfully')
for name in ('WarpIdol', 'SiegeCasterGameplay', 'SiegeAuthorityAndNormalization'):
    if not any(t['fullTestPath'] == 'AegisWar.Foundation.'+name and t['state'] == 'Success' for t in native['tests']):
        raise RuntimeError('Required native behavior test missing: '+name)
traversal = read(review['traversalReport'])
if not traversal['passed'] or traversal['routesCompleted'] != 7 or len(traversal['walkers']) != 12:
    raise RuntimeError('Twelve-character traversal is required')
technical = read('artifacts/unreal/siege/animation/technical-verification.json')
if not technical['structuralChecksPassed'] or technical['failures']:
    raise RuntimeError('Caster structural checks failed')
registry_path = ROOT/'unreal/AegisWar/Content/Migration/visual-imports.json'
before = registry_path.read_bytes()
registry = json.loads(before)
staged = read('artifacts/unreal/siege/animation/staged-visual-imports.json')
entries = {r['profileKey']: r for r in registry['entries']}
selected = {r['profileKey']: r for r in staged['entries'] if r['profileKey'] in PROFILES}
if set(selected) != PROFILES: raise RuntimeError('Both exact caster bindings are required')
for profile, row in selected.items():
    if hashlib.sha256((ROOT/row['sourceModel']).read_bytes()).hexdigest() != row['sourceSha256']:
        raise RuntimeError('Caster source changed: '+profile)
    if profile in entries and entries[profile] != row:
        raise RuntimeError('Preserve an existing different caster binding: '+profile)
    entries[profile] = row
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(TARGET): raise RuntimeError('Missing isolated lower-city map')
fields = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
          if isinstance(a, unreal.WarSiegeBattlefield)]
if len(fields) != 1: raise RuntimeError('Exactly one battlefield is required')
field = fields[0]
if field.get_editor_property('traversal_reviewed') or field.get_editor_property('equipped_roster_reviewed'):
    raise RuntimeError('Preserve existing full-siege review')
roster = field.get_editor_property('roster')
if len(roster) != 6: raise RuntimeError('The six-class roster is required')
for entry in roster:
    visual = entry.get_editor_property('visual')
    if visual.validate_for_spawn(entry.get_editor_property('realm')): raise RuntimeError('Invalid equipped roster visual')
    binding = entries.get(str(visual.source_profile_key))
    if not binding or binding['sourceSha256'] != visual.source_sha256:
        raise RuntimeError('Roster source binding differs')
for role in ('crew_visual','guard_visual','commander_visual'):
    visual = field.get_editor_property(role)
    if not visual or visual.validate_for_spawn(visual.realm): raise RuntimeError('Invalid encounter: '+role)
registry['entries'] = list(entries.values())
backup = OUT/'visual-imports-before-lower-city.json'
if not backup.exists(): backup.write_bytes(before)
registry_path.write_text(json.dumps(registry,indent=2)+'\n',encoding='utf-8')
try:
    field.set_editor_property('lower_city_reviewed', True)
    if not levels.save_current_level(): raise RuntimeError('Could not save local admission')
except Exception:
    registry_path.write_bytes(before)
    raise
(OUT/'local-admission.json').write_text(json.dumps(dict(map=TARGET,lowerCityReviewed=True,
    addedProfiles=sorted(PROFILES),fullSiegeReviewed=False,releaseApproved=False,
    reviewSha256=hashlib.sha256((OUT/'development-review.json').read_bytes()).hexdigest()),indent=2)+'\n')
unreal.log('WAR_LOWER_CITY_ADMITTED; full siege and release remain unapproved')
