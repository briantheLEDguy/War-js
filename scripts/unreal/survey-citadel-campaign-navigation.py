"""Inspect exact private campaign/overlay navigation ownership without saving."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_blueprint import sha
from shared_city_sources import package_file, protected_source_file

revision = os.environ.get('WAR_CITADEL_INSPECT_REVISION', '')
if not re.fullmatch('[a-f0-9]{12}', revision):
    raise RuntimeError('An explicit private candidate revision is required')
directory = ROOT / 'artifacts/unreal/aegis-citadel' / revision
city = json.loads((directory / 'candidate.json').read_text())
prepared = json.loads((directory / 'publication-candidate.json').read_text())
prefix = '/Game/WorldRebuild/AegisCitadel_' + revision
if prepared.get('published') is not False or prepared.get('map') != prefix + '/CampaignCandidate':
    raise RuntimeError('Only the exact unpublished campaign candidate may be inspected')
hashes = {**city['sourceHashes'], **city['packageHashes'], **prepared['sourceHashes'], **prepared['packageHashes']}
def observed():
    return {name: sha(protected_source_file(ROOT, name, expected) if name.startswith('/Engine/')
        else package_file(ROOT, name)) for name, expected in hashes.items()}
if observed() != hashes:
    raise RuntimeError('Preserve changed source or candidate packages')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(prepared['map']):
    raise RuntimeError('Cannot load the exact private campaign candidate')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for name in [*city['sceneryLevels'], *city['retainedGameplayLevels'], prepared['overlay']]:
    stream = unreal.GameplayStatics.get_streaming_level(world, name)
    if not stream:
        raise RuntimeError('Missing exact candidate attachment: ' + name)
# Editor map loading loads attachment objects even when they start hidden in play.
# This survey reads ownership; it does not need to alter streaming visibility.
unreal.GameplayStatics.flush_level_streaming(world)
rows = []
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if isinstance(actor, (unreal.RecastNavMesh, unreal.NavMeshBoundsVolume, unreal.NavModifierVolume)):
        row = dict(actor=actor.get_path_name(), package=actor.get_outer().get_path_name().split('.')[0],
            klass=actor.get_class().get_name(), label=actor.get_actor_label(), tags=list(map(str, actor.tags)))
        if isinstance(actor, unreal.RecastNavMesh):
            row['properties'] = {key: str(actor.get_editor_property(key)) if key == 'runtime_generation'
                else actor.get_editor_property(key) for key in ('agent_radius', 'agent_height', 'runtime_generation')}
        rows.append(row)
if observed() != hashes:
    raise RuntimeError('Inspection changed protected package bytes')
output = directory / ('campaign-navigation-survey-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
output.write_text(json.dumps(dict(schemaVersion=1, revision=revision, map=prepared['map'], overlay=prepared['overlay'],
    nativeActors=rows, packagesUnchanged=True, protectedPackageHashes=hashes,
    nativeGameReadinessVerified=False, convoyTraversalVerified=False, productionAdmission=False), indent=2) + '\n')
unreal.log('WAR_CITADEL_CAMPAIGN_NAVIGATION_SURVEY=' + str(output))
