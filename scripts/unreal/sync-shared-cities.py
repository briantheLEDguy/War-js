"""Split campaign gameplay from scenery and bind every city consumer to shared levels.

Run with the Editor closed. Backups/journals stay outside Content. No review is
granted here, and no model or material is duplicated. Interrupted runs must be
restored from their journal before retrying.
"""
import json
import shutil
import sys
import time
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from shared_city_sources import CITIES, RECEIPT, digest, package_file, routing, can_preserve_siege_review

OUT = ROOT / 'artifacts/unreal/shared-cities'
SIEGE = '/Game/Capitals/Siege/AegisCapital_Siege'
assets = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


from shared_city_authoring import write, world, load, own, save, detach, prepare_city


def main():
    build, manifest, manifest_file = routing(ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    pending = OUT / 'pending.json'
    if pending.exists():
        raise RuntimeError('An interrupted city migration needs recovery: ' + str(pending))
    prior = json.loads((ROOT / RECEIPT).read_text()) if (ROOT / RECEIPT).exists() else {}
    run = OUT / str(time.time_ns())
    run.mkdir()
    journal = dict(run=str(run), backups={}, created=[], complete=False)

    def backup(file):
        key = file.relative_to(ROOT).as_posix()
        if key in journal['backups']:
            return
        target = run / 'backup' / key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        journal['backups'][key] = digest(file)
        write(pending, journal)

    for file in [ROOT / 'artifacts/unreal/world-portals/build.json', manifest_file]:
        backup(file)
    for package in [build['map'], build['layer'], SIEGE]:
        backup(package_file(ROOT, package))
    if (ROOT / RECEIPT).exists():
        backup(ROOT / RECEIPT)
    def record_created(package):
        journal['created'].append(package)
        write(pending, journal)

    cities = []
    for zone_id in CITIES:
        zone = next(z for z in manifest['zones'] if z['id'] == zone_id)
        previous_city = next((c for c in prior.get('cities', []) if c['id'] == zone_id), {})
        city = prepare_city(zone, '/Game/Cities/Shared/' + zone_id + '/City', backup, record_created, run,
                            protected_sources=previous_city.get('dependencyHashes', {}))
        manifest['packageHashes'].update({p: city['packageHashes'][p] for p in city['sceneryLevels'] + city['gameplayLevels']})
        cities.append(city)

    load(build['layer'])
    for city in cities:
        anchor = next(a for a in own(build['layer']) if isinstance(a, unreal.WarZoneAnchor)
                      and str(a.get_editor_property('zone_id')) == city['id'])
        anchor.set_editor_property('city_definition', assets.load_asset(city['definition']))
        anchor.set_editor_property('content_levels', city['gameplayLevels'])
    save(build['layer'])
    manifest['packageHashes'][build['layer']] = digest(package_file(ROOT, build['layer']))
    load(build['map'])
    for city in cities:
        for package in city['sceneryLevels'] + city['gameplayLevels']:
            stream = unreal.GameplayStatics.get_streaming_level(world(), package)
            if not stream:
                stream = unreal.EditorLevelUtils.add_level_to_world(world(), package, unreal.LevelStreamingDynamic)
                if not stream:
                    raise RuntimeError('Cannot attach shared campaign content')
                stream.set_editor_property('initially_loaded', False)
                stream.set_editor_property('initially_visible', False)
    save(build['map'])
    manifest['mainSha256'] = build['capitalSha256After'] = digest(package_file(ROOT, build['map']))

    aegis = cities[0]
    siege_receipt = ROOT / 'artifacts/unreal/scenario-queues/capital-scenery.json'
    old_review = json.loads(siege_receipt.read_text()) if siege_receipt.exists() else {}
    overlay_hash = digest(package_file(ROOT, SIEGE))
    load(SIEGE)
    field = next(a for a in own(SIEGE) if isinstance(a, unreal.WarSiegeBattlefield))
    old_layers = {level.get_outer().get_path_name().split('.')[0] for level in unreal.EditorLevelUtils.get_levels(world())} - {SIEGE}
    for package in old_layers:
        if package not in aegis['sceneryLevels']:
            if not package.startswith('/Game/Capitals/Siege/'):
                raise RuntimeError('Unexpected siege attachment; preserve and inspect: ' + package)
            detach(package)
    for package in aegis['sceneryLevels']:
        if not unreal.GameplayStatics.get_streaming_level(world(), package):
            if not unreal.EditorLevelUtils.add_level_to_world(world(), package, unreal.LevelStreamingAlwaysLoaded):
                raise RuntimeError('Cannot attach shared siege scenery')
    field.set_editor_property('city_definition', assets.load_asset(aegis['definition']))
    previous = next((c for c in prior.get('cities', []) if c['id'] == 'aegis_capital'), {})
    changed = not can_preserve_siege_review(previous, aegis, old_review, overlay_hash)
    if changed:
        field.set_editor_property('reviewed_city_revision', '')
        field.set_editor_property('lower_city_reviewed', False)
        field.set_editor_property('traversal_reviewed', False)
    save(SIEGE)
    if siege_receipt.exists():
        backup(siege_receipt)
    if changed:
        old_review = {}
    updated_review = dict(old_review)
    updated_review.update(version=2, revision=aegis['revision'], cityDefinition=aegis['definition'],
        layers=aegis['sceneryLevels'], map=SIEGE, mapSha256=digest(package_file(ROOT, SIEGE)),
        navigationVerified=old_review.get('navigationVerified', False), visualVerified=old_review.get('visualVerified', False))
    write(siege_receipt, updated_review)
    write(manifest_file, manifest)
    write(ROOT / 'artifacts/unreal/world-portals/build.json', build)
    receipt = dict(schemaVersion=1, campaignMap=build['map'], cities=cities,
        campaignHashes={p: digest(package_file(ROOT, p)) for p in (build['map'], build['layer'])},
        removedSiegeAttachments=sorted(old_layers - set(aegis['sceneryLevels'])), backup=str(run), releaseApproved=False)
    write(ROOT / RECEIPT, receipt)
    journal['complete'] = True
    write(run / 'journal.json', journal)
    pending.unlink()
    unreal.log('WAR_SHARED_CITIES=' + json.dumps({c['id']: c['revision'] for c in cities}))


main()
