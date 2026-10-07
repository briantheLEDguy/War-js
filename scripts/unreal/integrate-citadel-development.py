"""Journal one verified city into normal Development campaign/scenario/frontend.

Run only in the serialized Editor commandlet with exact stage/checkpoint paths
and SHA-256 values in WAR_CITADEL_DEVELOPMENT_{STAGE,CHECKPOINT}_{PATH,SHA256}.
This selects content, keeps competitive admission closed, and preserves rollback
bytes. It does not replace the fully gated production publication tool.
"""
import copy
import importlib.util
import json
import os
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from citadel_development_integration import development_manifests, integration_packages, selected_config
from shared_city_authoring import load, own, save, detach, world
from shared_city_sources import RECEIPT, digest, package_file, protected_source_file, routing, source_plan
from citadel_review_world import routing_bindings
from world_actor_state import snapshot

spec = importlib.util.spec_from_file_location('citadel_publisher', Path(__file__).with_name('publish-aegis-citadel.py'))
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
read, write = publisher.read, publisher.write


def signed_input(kind):
    file = publisher.confined(ROOT, os.environ['WAR_CITADEL_DEVELOPMENT_' + kind + '_PATH'])
    if digest(file) != os.environ['WAR_CITADEL_DEVELOPMENT_' + kind + '_SHA256']:
        raise ValueError('Changed signed development input: ' + kind)
    return file, read(file)


stage_file, stage = signed_input('STAGE')
checkpoint_file, checkpoint = signed_input('CHECKPOINT')
revision = checkpoint['privateDecor']
packages = integration_packages(revision)
run = ROOT / 'artifacts/unreal/citadel-development' / revision
if run.exists():
    raise ValueError('Preserve existing integration, including an interrupted journal: ' + str(run))
review_file = Path(stage['reviewReceipt'])
review = read(review_file)
if (checkpoint['evidenceHashes'].get(str(stage_file)) != digest(stage_file)
        or checkpoint['evidenceHashes'].get(str(review_file)) != digest(review_file)
        or checkpoint['cityRevision'] != stage['cityRevision'] or checkpoint['heldExterior'] != '0284fb4947a8'
        or stage['acceptedExteriorSourceRevision'] != checkpoint['heldExterior']
        or stage['additions'] != 56 or len(stage['warmPracticals']) != 34
        or len(stage['residentsRetained']) != 8 or not stage['acceptedExteriorUnchanged']
        or not stage['existing52ActorStatesExact'] or not stage['existing52GeometryAndCollisionUnchanged']
        or checkpoint['traversal']['directedWalks'] != 92 or checkpoint['traversal']['widthSamples'] != 27680
        or checkpoint['traversal']['routeFailures'] or checkpoint['traversal']['physicalFailures']
        or checkpoint['verification']['nativeFoundation'] != 139
        or any(checkpoint[key] is not False for key in ('visualApproved', 'lightingApproved', 'populatedPerformanceVerified',
                                                       'fullSiegeApproved', 'releaseAcceptance', 'shutdownAllowed'))):
    raise ValueError('Complete verified development checkpoint required; approvals cannot be transferred')
for file, expected in checkpoint['evidenceHashes'].items():
    if digest(Path(file)) != expected:
        raise ValueError('Changed native proof evidence: ' + file)
for package, expected in {**review['sourcePackageHashes'], **review['packageHashes']}.items():
    if digest(protected_source_file(ROOT, package, expected)) != expected:
        raise ValueError('Changed prior native review binding: ' + package)
plan = source_plan(ROOT)
build, manifest, manifest_file = routing(ROOT)
prior_receipt = read(ROOT / RECEIPT)
old_city = plan['cities'][0]
config_file = ROOT / 'unreal/AegisWar/Config/DefaultEngine.ini'
config_before = config_file.read_bytes()
config_after = selected_config(config_before, build['map'], packages['map'])
assets = unreal.EditorAssetLibrary
for package in packages.values():
    if assets.does_asset_exist(package):
        raise ValueError('Preserve existing or partially authored integration package: ' + package)
source_siege = ROOT / 'artifacts/unreal/aegis-citadel/0284fb4947a8/candidate.json'
scenario_source = read(source_siege)['siegeMap']
frontend = assets.load_asset(publisher.FRONTEND)
publisher.require_frontend_source_owner(assets, frontend)
run.mkdir(parents=True)
journal = publisher.Journal(ROOT, run, 'development-integration')
mutable = [config_file, manifest_file, ROOT / 'artifacts/unreal/world-portals/build.json', ROOT / RECEIPT,
           ROOT / 'artifacts/unreal/frontend/build.json', ROOT / 'artifacts/unreal/scenario-queues/capital-scenery.json',
           ROOT / 'artifacts/unreal/citadel-siege/full-siege-approval.json',
           ROOT / 'artifacts/unreal/shared-cities/native-verification.json']
for file in mutable:
    if file.exists(): journal.backup(file)
    else:
        journal.value.setdefault('createdFiles', []).append(file.relative_to(ROOT).as_posix())
        write(journal.pending, journal.value)
for package in (publisher.SIEGE, publisher.FRONTEND):
    file = package_file(ROOT, package)
    journal.backup(file)
    for extension in ('.uexp', '.ubulk', '.uptnl'):
        if file.with_suffix(extension).exists(): journal.backup(file.with_suffix(extension))


def duplicate(source, target):
    journal.created(target)
    if not assets.duplicate_asset(source, target):
        raise RuntimeError('Cannot duplicate native integration package: ' + target)


duplicate(review['population'], packages['population'])
load(packages['population'])
population_before = {actor.get_name(): snapshot(actor) for actor in own(packages['population'])}
if len([actor for actor in own(packages['population']) if isinstance(actor, unreal.WarCityNpc)]) != 8:
    raise RuntimeError('The eight verified residents must remain intact')
save(packages['population'])
if {actor.get_name(): snapshot(actor) for actor in own(packages['population'])} != population_before:
    raise RuntimeError('Resident state changed during development integration')

duplicate(review['routing'], packages['routing'])
load(packages['routing'])
router_before = {actor.get_name(): snapshot(actor) for actor in own(packages['routing'])}
bindings_before = routing_bindings(own(packages['routing']))
anchors = [actor for actor in own(packages['routing']) if isinstance(actor, unreal.WarZoneAnchor)]
portals = [actor for actor in own(packages['routing']) if isinstance(actor, unreal.WarZonePortal)]
if len(anchors) != 32 or len(portals) != 70 or sorted(str(actor.get_editor_property('route_id')) for actor in portals) != sorted(build['portals']):
    raise RuntimeError('All 32 zones and 70 directed portals must remain intact')
anchor = next(actor for actor in anchors if str(actor.get_editor_property('zone_id')) == 'aegis_capital')
if anchor.get_editor_property('city_definition').get_path_name().split('.')[0] != stage['city']['definition']:
    raise RuntimeError('Routing lost the verified city definition')
gameplay = [packages['population'] if level == review['population'] else level
            for level in map(str, anchor.get_editor_property('content_levels'))]
if gameplay != [*old_city['gameplayLevels'], stage['overlay'], packages['population']]:
    raise RuntimeError('Campaign services/live overlay/residents differ from the verified review')
anchor.set_editor_property('content_levels', gameplay)
bindings_after = routing_bindings(own(packages['routing']))
expected_bindings = copy.deepcopy(bindings_before)
next(row for row in expected_bindings if row.get('zone') == 'aegis_capital')['levels'] = gameplay
if bindings_after != expected_bindings or {actor.get_name(): snapshot(actor) for actor in own(packages['routing'])} != router_before:
    raise RuntimeError('Unrelated campaign actor or routing state changed')
save(packages['routing'])

duplicate(review['map'], packages['map'])
load(packages['map'])
map_before = {actor.get_name(): snapshot(actor) for actor in own(packages['map'])}
streams_before = list(unreal.WarImportLibrary.get_streaming_level_package_names(world()))
if streams_before != review['streamingDeclarations']:
    raise RuntimeError('Campaign streaming declarations changed after native review')
detach(review['routing'])
detach(review['population'])
for package in (packages['routing'], packages['population']):
    stream = unreal.EditorLevelUtils.add_level_to_world(world(), package,
        unreal.LevelStreamingAlwaysLoaded if package == packages['routing'] else unreal.LevelStreamingDynamic)
    if not stream: raise RuntimeError('Cannot attach combined campaign gameplay')
    if package == packages['population']:
        stream.set_editor_property('initially_loaded', False)
        stream.set_editor_property('initially_visible', False)
streams = list(unreal.WarImportLibrary.get_streaming_level_package_names(world()))
expected_streams = sorted([level for level in streams_before if level not in (review['routing'], review['population'])]
                          + [packages['routing'], packages['population']])
if streams != expected_streams or {actor.get_name(): snapshot(actor) for actor in own(packages['map'])} != map_before:
    raise RuntimeError('Persistent campaign state or unrelated streaming declaration changed')
save(packages['map'])

duplicate(scenario_source, packages['scenario'])
load(packages['scenario'])
for level in list(unreal.EditorLevelUtils.get_levels(world())):
    package = level.get_outer().get_path_name().split('.')[0]
    if package != packages['scenario']: detach(package)
fields = [actor for actor in own(packages['scenario']) if isinstance(actor, unreal.WarSiegeBattlefield)]
if len(fields) != 1 or fields[0].get_editor_property('definition_version') != 2:
    raise RuntimeError('Exactly one current scenario gameplay definition is required')
fields[0].set_editor_property('city_definition', assets.load_asset(stage['city']['definition']))
fields[0].set_editor_property('live_capital_overlay', False)
fields[0].set_editor_property('reviewed_city_revision', '')
for package in stage['city']['sceneryLevels']:
    if not unreal.EditorLevelUtils.add_level_to_world(world(), package, unreal.LevelStreamingAlwaysLoaded):
        raise RuntimeError('Cannot attach the same verified scenery to the scenario')
save(packages['scenario'])

# Save a copy through Unreal's map authoring API; deletion can retain a registry entry.
load(packages['scenario'])
if not unreal.EditorLoadingAndSavingUtils.save_map(world(), publisher.SIEGE):
    raise RuntimeError('Canonical scenario replacement failed; recover from the durable journal')
frontend = assets.load_asset(publisher.FRONTEND)
cities = list(frontend.get_editor_property('cities'))
selected = [city for city in cities if str(city.get_editor_property('zone_id')) == 'aegis_capital']
if len(selected) != 1: raise RuntimeError('A unique frontend Aegis city is required')
selected[0].set_editor_property('city_definition', assets.load_asset(stage['city']['definition']))
frontend.set_editor_property('cities', cities)
if not assets.save_loaded_asset(frontend, False): raise RuntimeError('Cannot save combined frontend binding')

hashes = {package: digest(package_file(ROOT, package)) for package in [*packages.values(),
    stage['city']['definition'], *stage['city']['sceneryLevels'], *gameplay, publisher.SIEGE, publisher.FRONTEND]}
new_build, new_manifest, new_receipt = development_manifests(build, manifest, prior_receipt, stage['city'], gameplay, packages, hashes)
if config_file.read_bytes() != config_before:
    raise RuntimeError('Startup configuration changed during native integration')
for package, expected in {**review['sourcePackageHashes'], **review['packageHashes']}.items():
    if package not in (publisher.SIEGE, publisher.FRONTEND) and digest(protected_source_file(ROOT, package, expected)) != expected:
        raise RuntimeError('Protected prior native package changed: ' + package)
publisher.write_bytes(config_file, config_after)
write(manifest_file, new_manifest)
write(ROOT / 'artifacts/unreal/world-portals/build.json', new_build)
write(ROOT / RECEIPT, new_receipt)
frontend_receipt = read(ROOT / 'artifacts/unreal/frontend/build.json')
frontend_receipt.update(sourcePlan=source_plan(ROOT), visualApproved=False, sourceMapsModified=False)
frontend_receipt['outputPackages'][publisher.FRONTEND] = hashes[publisher.FRONTEND]
write(ROOT / 'artifacts/unreal/frontend/build.json', frontend_receipt)
write(ROOT / 'artifacts/unreal/scenario-queues/capital-scenery.json', dict(version=2, revision=stage['cityRevision'],
    cityDefinition=stage['city']['definition'], layers=stage['city']['sceneryLevels'], map=publisher.SIEGE,
    mapSha256=hashes[publisher.SIEGE], navigationVerified=False, visualVerified=False, developmentOnly=True))
write(ROOT / 'artifacts/unreal/citadel-siege/full-siege-approval.json', dict(version=1, rulesVersion=2,
    battlefieldDefinitionVersion=2, revision=stage['cityRevision'], capacity=18, objectiveCount=8, optionalCount=3,
    published=False, admissionApproved=False, developmentOnly=True,
    reason='Development content selection does not grant full-siege, campaign or release acceptance.'))
receipt = dict(schemaVersion=1, revision=revision, city=stage['city']['definition'], cityRevision=stage['cityRevision'],
    **packages, packageHashes=hashes, stagePath=str(stage_file), stageSha256=digest(stage_file),
    checkpointPath=str(checkpoint_file), checkpointSha256=digest(checkpoint_file),
    streamingDeclarations=streams, routingBindings=bindings_after, zones=32, directedRoutes=70,
    decorObjects=56, practicalLights=34, residents=8, canonicalScenario=publisher.SIEGE,
    canonicalFrontend=publisher.FRONTEND, defaultMapSelected=True, servicesRetained=True,
    developmentOnly=True, fullSiegeAdmissionApproved=False, visualApproved=False,
    lightingApproved=False, populatedPerformanceVerified=False, releaseAcceptance=False, shutdownAllowed=False)
write(run / 'integrated.json', receipt)
# Bind the ordinary GM proof to this exact configured default and its sources.
owned = {package: hashes[package] for package in (packages['map'], packages['routing'], packages['population'])}
protected = {**review['sourcePackageHashes'], **review['packageHashes'],
             **stage['city']['packageHashes'], **stage['city']['dependencyHashes'], **hashes}
for package in owned: protected.pop(package, None)
for package, expected in protected.items():
    if digest(protected_source_file(ROOT, package, expected)) != expected:
        raise RuntimeError('Changed integrated GM source binding: ' + package)
write(run / 'gm-receipt.json', dict(schemaVersion=1, signature=stage['signature'], sourceRevision=revision,
    map=packages['map'], routing=packages['routing'], population=packages['population'],
    city=stage['city']['definition'], cityRevision=stage['cityRevision'], mapSha256=hashes[packages['map']],
    packageHashes=owned, sourcePackageHashes=protected, sourcePackagesUnchanged=True,
    requiresDevelopmentGM=True, ordinaryLocalDevelopmentEntry=True, servicesRetained=True,
    residentPopulationPrivateReviewOnly=False, directedRoutes=70, zones=32, streamingDeclarations=streams,
    published=False, visualApproved=False, gameplayApproved=False, developmentOnly=True,
    defaultMapSelected=True, fullSiegeAdmissionApproved=False, launchSelectedMapArgument=''))
journal.complete()
unreal.log('WAR_CITADEL_DEVELOPMENT_INTEGRATED=' + packages['map'])
