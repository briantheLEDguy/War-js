"""Root-run, read-only committed terrain export from an explicit private revision.

Set WAR_CITADEL_TERRAIN_INSPECTION_REVISION to the reviewed 12-hex candidate.
This does not build, commit, save, alter an actor, or modify native Content.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_terrain import (MOUNTAIN_ACTOR_TRANSFORM, checked_native_terrain_source,
                                   hall_terrain_probe_points)
from shared_city_sources import package_file
from shared_city_authoring import load, own
from world_actor_state import snapshot

REVISION = os.environ.get('WAR_CITADEL_TERRAIN_INSPECTION_REVISION', '')
if not re.fullmatch('[a-f0-9]{12}', REVISION):
    raise RuntimeError('An explicit private terrain inspection revision is required.')
RUN = ROOT / 'artifacts/unreal/aegis-citadel' / REVISION
RECEIPT_FILE = RUN / 'candidate.json'
candidate = json.loads(RECEIPT_FILE.read_text(encoding='utf-8-sig'))
PREFIX = '/Game/WorldRebuild/AegisCitadel_' + REVISION
SOURCE = '/Game/WorldRebuild/DutchBastion_d105951f4aab/Layers/authored'
MESH_PACKAGE = '/Game/Capitals/crownward/Terrain_mountain'
MESH = MESH_PACKAGE + '.Terrain_mountain'
ACTOR = 'StaticMeshActor_306'
LABEL = 'Crownward authored mountain massif'
TAG = 'WarZoneObject_aegis_capital_StaticMeshActor_306'
if (candidate.get('revision') != REVISION or candidate.get('map') != PREFIX + '/ReviewCandidate'
        or candidate.get('published') is not False or candidate.get('nativeImported') is not True):
    raise RuntimeError('Terrain inspection receipt differs from the explicit private candidate.')
copies = [row['candidate'] for row in candidate.get('outsideMaskPreservation', []) if row.get('source') == SOURCE]
if len(copies) != 1 or not re.fullmatch(re.escape(PREFIX) + '/Layers/RetainedCity_[0-9]+', copies[0]):
    raise RuntimeError('The exact copied mountain source layer is ambiguous.')
COPIED = copies[0]
bound = {**candidate.get('sourceHashes', {}), **candidate.get('packageHashes', {}),
         **candidate.get('city', {}).get('dependencyHashes', {})}
packages = [SOURCE, COPIED, MESH_PACKAGE, candidate['map'], candidate['city']['definition'], *candidate['sceneryLevels']]
packages = list(dict.fromkeys(packages))

def sha(file): return hashlib.sha256(file.read_bytes()).hexdigest()
def hash_packages(): return {name: sha(package_file(ROOT, name)) for name in packages}
native_binary = ROOT / 'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWarEditorTools.dll'
source_files = [Path(__file__), Path(__file__).with_name('aegis_citadel_terrain.py'),
    Path(__file__).with_name('world_actor_state.py'), Path(__file__).with_name('shared_city_authoring.py'),
    Path(__file__).with_name('shared_city_sources.py'),
    ROOT / 'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarImportLibrary.cpp',
    ROOT / 'unreal/AegisWar/Source/AegisWarEditorTools/Public/WarImportLibrary.h']
native_binary_sha = sha(native_binary)
source_hashes = {str(file.relative_to(ROOT)).replace('\\', '/'): sha(file) for file in source_files}
before = hash_packages()
if any(bound.get(name) != value for name, value in before.items()):
    raise RuntimeError('Actual native source/candidate package changed before read-only terrain inspection.')
receipt_before = sha(RECEIPT_FILE)

def actor_in(package):
    matches = [actor for actor in own(package) if actor.get_name() == ACTOR]
    if len(matches) != 1: raise RuntimeError('Exact mountain actor is unavailable: ' + package)
    actor = matches[0]
    if actor.get_class().get_name() != 'StaticMeshActor' or actor.get_actor_label() != LABEL or TAG not in map(str, actor.tags):
        raise RuntimeError('The actual mountain actor identity changed.')
    component = actor.static_mesh_component
    if component.get_name() != 'StaticMeshComponent0' or component.static_mesh.get_path_name() != MESH:
        raise RuntimeError('The actual mountain component no longer references its unchanged source mesh.')
    transform = actor.get_actor_transform()
    actual = dict(translationCm=[transform.translation.x, transform.translation.y, transform.translation.z],
        rotationQuaternion=[transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w],
        scale=[transform.scale3d.x, transform.scale3d.y, transform.scale3d.z])
    if actual != MOUNTAIN_ACTOR_TRANSFORM:
        raise RuntimeError('The measured mountain actor transform differs from the signed carve frame.')
    return actor, snapshot(actor), actual

load(SOURCE)
source_actor, source_state, transform = actor_in(SOURCE)
source_state_after = snapshot(source_actor)
mesh = unreal.load_asset(MESH_PACKAGE)
raw = unreal.WarImportLibrary.describe_static_mesh_source_data(mesh, 0)
source_export = json.loads(raw)
data = checked_native_terrain_source(source_export, MESH)
if snapshot(source_actor) != source_state_after:
    raise RuntimeError('Source actor changed during its read-only committed export.')
load(COPIED)
copied_actor, copied_state, copied_transform = actor_in(COPIED)
if copied_state != source_state or copied_transform != transform:
    raise RuntimeError('The candidate mountain actor differs from the preserved original actor.')
after = hash_packages()
if (before != after or sha(RECEIPT_FILE) != receipt_before or snapshot(copied_actor) != copied_state
        or sha(native_binary) != native_binary_sha
        or any(sha(ROOT / name) != value for name, value in source_hashes.items())):
    raise RuntimeError('Read-only terrain inspection changed native packages, receipt or actor state.')

def write_once_or_same(path, text):
    encoded = text.encode('utf-8')
    if path.exists():
        if path.read_bytes() != encoded: raise RuntimeError('Preserve existing different native terrain evidence: ' + str(path))
    else:
        with path.open('xb') as stream: stream.write(encoded)
    return sha(path)

raw_file = RUN / 'native-terrain-source.json'
raw_sha = write_once_or_same(raw_file, raw)
mesh_file = RUN / 'native-terrain-carve-input.json'
mesh_sha = write_once_or_same(mesh_file, json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False))
evidence = dict(schemaVersion=1, revision=REVISION, inspectionOnly=True, readOnly=True, noPackagesSaved=True,
    sourcePackage=SOURCE, candidatePackage=COPIED, actor=ACTOR, actorClass='StaticMeshActor', label=LABEL,
    component='StaticMeshComponent0', requiredTag=TAG, sourceMesh=MESH, actorTransform=transform,
    sourceActorState=source_state, candidateActorState=copied_state,
    sourceActorStateSha256=hashlib.sha256(json.dumps(source_state, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    sourceFile=str(raw_file.relative_to(ROOT)).replace('\\', '/'), sourceSha256=raw_sha,
    inputFile=str(mesh_file.relative_to(ROOT)).replace('\\', '/'), inputSha256=mesh_sha,
    sourcePolicy=source_export['sourcePolicy'], coordinateSpace=source_export['coordinateSpace'],
    materialSlots=source_export['materialSlots'], polygonGroups=source_export['polygonGroups'],
    packagesBefore=before, packagesAfter=after, candidateReceiptSha256=receipt_before,
    nativeBinary=str(native_binary.relative_to(ROOT)).replace('\\', '/'), nativeBinarySha256=native_binary_sha,
    sourceHashes=source_hashes,
    sourceTriangleCount=source_export['sourceTriangleCount'], probes=hall_terrain_probe_points(),
    scriptSha256=sha(Path(__file__)), nativeSourceExportObserved=True,
    nativeCollisionVerified=False, visualApproved=False, published=False)
write_once_or_same(RUN / 'native-terrain-source-receipt.json', json.dumps(evidence, indent=2) + '\n')
unreal.log('WAR_CITADEL_NATIVE_TERRAIN_SOURCE=' + str(raw_file))
