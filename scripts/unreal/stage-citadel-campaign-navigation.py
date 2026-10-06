"""Stage or freshly verify exact private campaign nav ownership with rollback copies."""
import json
import os
import re
import shutil
import sys
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_blueprint import sha
from shared_city_sources import package_file, protected_source_file
from citadel_campaign_navigation import updated_preparation
from world_actor_state import snapshot

revision = os.environ.get('WAR_CITADEL_INSPECT_REVISION', '')
mode = os.environ.get('WAR_CITADEL_NAVIGATION_MODE', '')
if not re.fullmatch('[a-f0-9]{12}', revision) or mode not in ('stage', 'verify'):
    raise ValueError('An explicit private revision and stage/verify mode are required')
directory = ROOT / 'artifacts/unreal/aegis-citadel' / revision
receipt = directory / 'publication-candidate.json'
original_bytes = receipt.read_bytes()
staged = json.loads(original_bytes)
city = json.loads((directory / 'candidate.json').read_bytes())
prefix = '/Game/WorldRebuild/AegisCitadel_' + revision
if staged.get('published') is not False or staged.get('revision') != revision or staged.get('map') != prefix + '/CampaignCandidate' or staged.get('overlay') != prefix + '/CampaignSiegeOverlay':
    raise ValueError('Only the exact unpublished private pair may change')
mutable = {staged['map'], staged['overlay']}
authoring_files = [Path(__file__), Path(__file__).with_name('citadel_campaign_navigation.py'),
    ROOT / 'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarCampaignNavigationAuthoring.cpp',
    ROOT / 'unreal/AegisWar/Source/AegisWarEditorTools/Public/WarSiegeAuthoringLibrary.h',
    ROOT / 'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWarEditorTools.dll']
authoring_hashes = {str(p.relative_to(ROOT)): sha(p) for p in authoring_files}
protected = {**city['sourceHashes'], **city['packageHashes'], **staged['sourceHashes'], **staged['manifest']['packageHashes']}
protected = {p: h for p, h in protected.items() if p not in mutable}

def observe(hashes):
    return {p: sha(protected_source_file(ROOT, p, h) if p.startswith('/Engine/') else package_file(ROOT, p))
            for p, h in hashes.items()}

if observe(protected) != protected:
    raise ValueError('Preserve changed source, city, scenario, routing or service packages')
pending = directory / 'campaign-navigation-transfer.pending.json'
backup = directory / 'campaign-navigation-rollback'
if mode == 'stage':
    if pending.exists() or backup.exists() or staged.get('campaignNavigationOwnership'):
        raise ValueError('Preserve an existing or interrupted navigation transfer')
    if observe(staged['packageHashes']) != staged['packageHashes']:
        raise ValueError('Preserve changed preparation packages')
    backup.mkdir()
    (backup / 'publication-candidate.json').write_bytes(original_bytes)
    copied = {}
    for p in sorted(mutable):
        source = package_file(ROOT, p)
        for file in [source, *[source.with_suffix(s) for s in ('.uexp', '.ubulk') if source.with_suffix(s).exists()]]:
            target = backup / file.name
            shutil.copy2(file, target)
            if sha(target) != sha(file):
                raise ValueError('Cannot preserve exact rollback bytes')
            copied[str(file.relative_to(ROOT))] = dict(file=str(target.relative_to(ROOT)), sha256=sha(target))
    journal = dict(schemaVersion=1, revision=revision, helperSha256=sha(Path(__file__)),
        authoringHashes=authoring_hashes, stageProcessId=os.getpid(),
        originalPreparationSha256=sha(receipt), originalPackageHashes=staged['packageHashes'],
        rollback=copied, protectedPackageHashes=protected, completed=False, freshProcessVerified=False)
    pending.write_text(json.dumps(journal, indent=2) + '\n')
else:
    journal = json.loads(pending.read_bytes())
    if (journal.get('completed') is not True or journal.get('freshProcessVerified') is not False
            or journal.get('helperSha256') != sha(Path(__file__)) or journal.get('originalPreparationSha256') != sha(receipt)
            or journal.get('authoringHashes') != authoring_hashes or journal.get('stageProcessId') == os.getpid()
            or journal.get('protectedPackageHashes') != protected or observe(staged['packageHashes']) != journal.get('newPackageHashes')):
        raise ValueError('Preserve changed or unfinished navigation transfer')
    for original, binding in journal['rollback'].items():
        if sha(ROOT / binding['file']) != binding['sha256']:
            raise ValueError('Rollback package bytes changed')

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(staged['map']):
    raise ValueError('Cannot load the private campaign')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
library = unreal.WarSiegeAuthoringLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def retained():
    return {a.get_path_name(): snapshot(a) for a in actors.get_all_level_actors()
        if not isinstance(a, unreal.RecastNavMesh) and a.get_outer().get_path_name().split('.')[0] in mutable}

if mode == 'stage':
    before = retained()
    journal['retainedActorState'] = before
    journal['before'] = json.loads(library.describe_baked_navigation(world))
    pending.write_text(json.dumps(journal, indent=2) + '\n')
    raw_transfer = library.own_campaign_navigation(world, staged['overlay'])
    if not raw_transfer.startswith('{'):
        journal['failure'] = raw_transfer
        pending.write_text(json.dumps(journal, indent=2) + '\n')
        raise ValueError('Navigation transfer rejected before saving: ' + raw_transfer)
    journal['transfer'] = json.loads(raw_transfer)
    bounds = journal['transfer'].get('bounds', {})
    if (bounds.get('before') not in before or bounds.get('after') in before
            or not bounds['before'].startswith(staged['overlay'] + '.') or not bounds['after'].startswith(staged['map'] + '.')):
        raise ValueError('The exact siege bounds ownership witness is required')
    expected_after = {p: s for p, s in before.items() if p != bounds['before']}
    expected_after[bounds['after']] = before[bounds['before']]
    if journal['transfer'].get('passed') is not True or expected_after != retained():
        raise ValueError('Preserve rollback; navigation ownership changed unrelated actor state')
    journal['retainedActorState'] = expected_after
    pending.write_text(json.dumps(journal, indent=2) + '\n')
    for p in sorted(mutable):
        if not levels.set_current_level_by_name(p.rsplit('/', 1)[1]) or not levels.save_current_level():
            raise ValueError('Cannot save exact private transferred maps')
    journal['newPackageHashes'] = observe(staged['packageHashes'])
    if observe(protected) != protected or receipt.read_bytes() != original_bytes:
        raise ValueError('Protected bytes changed while saving private navigation')
    journal['completed'] = True
    pending.write_text(json.dumps(journal, indent=2) + '\n')
    unreal.log('WAR_CAMPAIGN_NAVIGATION_TRANSFER_SAVED=' + str(pending))
else:
    if retained() != journal['retainedActorState']:
        raise ValueError('Unrelated private actor state changed after save and reload')
    journal['reloadedActors'] = json.loads(library.describe_baked_navigation(world))['actors']
    journal['freshProcessVerified'] = True
    journal['verificationProcessId'] = os.getpid()
    updated = updated_preparation(staged, journal, observe(staged['packageHashes']))
    if observe(protected) != protected or receipt.read_bytes() != original_bytes:
        raise ValueError('Protected bytes changed during fresh verification')
    pending.write_text(json.dumps(journal, indent=2) + '\n')
    evidence = directory / 'campaign-navigation-ownership.json'
    if evidence.exists():
        raise ValueError('Preserve an existing ownership receipt')
    evidence.write_text(json.dumps(journal, indent=2) + '\n')
    updated['campaignNavigationOwnership']['evidence'] = dict(file=str(evidence.relative_to(ROOT)), sha256=sha(evidence))
    temp = directory / 'publication-candidate.navigation.tmp'
    temp.write_text(json.dumps(updated, indent=2) + '\n')
    temp.replace(receipt)
    unreal.log('WAR_CAMPAIGN_NAVIGATION_OWNERSHIP_VERIFIED=' + str(evidence))
