"""Portable deterministic verifier for the one explicitly occupied hall terrain cut."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from aegis_citadel_terrain import (HALL_CARVE_WORLD, MOUNTAIN_ACTOR_TRANSFORM,
                                   native_terrain_carve_document)
from aegis_citadel_terrain_readback import checked_committed_carve
from aegis_citadel_terrain_render_readback import checked_rendered_carve

SOURCE_PACKAGE = '/Game/WorldRebuild/DutchBastion_d105951f4aab/Layers/authored'
SOURCE_MESH_PACKAGE = '/Game/Capitals/crownward/Terrain_mountain'
SOURCE_MESH = SOURCE_MESH_PACKAGE + '.Terrain_mountain'
IDENTITY = dict(id='occupied_commander_hall', actor='StaticMeshActor_306', klass='StaticMeshActor',
    label='Crownward authored mountain massif', component='StaticMeshComponent0',
    requiredTag='WarZoneObject_aegis_capital_StaticMeshActor_306')
LOCAL_BOUNDS = [[[960, -4260, 5980], [8460, 4260, 24000]]]


AUDITED_FILES = None


def sha(file):
    resolved = file.resolve()
    value = hashlib.sha256(resolved.read_bytes()).hexdigest()
    if AUDITED_FILES is not None:
        previous = AUDITED_FILES.get(str(resolved))
        if previous is not None and previous != value:
            raise ValueError('Terrain audit input changed while it was being verified.')
        AUDITED_FILES[str(resolved)] = value
    return value
def value_sha(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
def hash_value(value): return isinstance(value, str) and bool(re.fullmatch('[a-f0-9]{64}', value))


def bound_file(root, relative, expected):
    if (not isinstance(relative, str) or not relative or '\\' in relative or Path(relative).is_absolute()
            or any(part in ('', '.', '..') for part in relative.split('/')) or not hash_value(expected)):
        raise ValueError('A confined source-bound terrain evidence file is required.')
    file = (root / relative).resolve()
    file.relative_to(root.resolve())
    if not file.is_file() or file.stat().st_size > 128 * 1024 * 1024 or sha(file) != expected:
        raise ValueError('Actual terrain evidence bytes changed or are unbounded.')
    return file


def require_native_readback(root, run, plan, city, spec, row, document):
    """Recompute committed attribute custody from actual saved raw API documents."""
    for helper in ('aegis_citadel_terrain_readback.py', 'aegis_citadel_terrain_render_readback.py'):
        helper_sha = sha(root / 'scripts/unreal' / helper)
        if (plan.get('sourceRecipes', {}).get(helper) != helper_sha
                or city.get('stageDependencySha256', {}).get(helper) != helper_sha):
            raise ValueError('Terrain committed/rendered readback helper is not signed and stage-bound.')
    readback = row.get('nativeReadback')
    if (not isinstance(readback, dict) or set(readback) != {'comparison', 'referencedSource', 'storedCorners',
            'renderDataAudit', 'sourcePolicy', 'actualPolicy', 'nativePolicyPreserved',
            'originalStoredCorners', 'originalRenderedFaces', 'renderedFaces', 'renderedComparison'}
            or readback.get('nativePolicyPreserved') is not True):
        raise ValueError('Actual post-save committed terrain readback is required.')
    payloads = {}
    for key, name in (('referencedSource', 'hall-carve-committed-source.json'),
                      ('storedCorners', 'hall-carve-stored-corners.json'), ('renderDataAudit', 'hall-carve-render-data.json'),
                      ('originalStoredCorners', 'hall-carve-original-stored-corners.json'),
                      ('originalRenderedFaces', 'hall-carve-original-rendered-faces.json'),
                      ('renderedFaces', 'hall-carve-rendered-faces.json')):
        binding = readback.get(key)
        if not isinstance(binding, dict) or set(binding) != {'path', 'sha256'} or binding['path'] != 'terrain-carves/' + name:
            raise ValueError('Terrain committed readback escaped its exact candidate files.')
        payloads[key] = json.loads(bound_file(run, binding['path'], binding['sha256']).read_text(encoding='utf-8-sig'))
    referenced, stored, original_stored = payloads['referencedSource'], payloads['storedCorners'], payloads['originalStoredCorners']
    if (referenced.get('schemaVersion') != 1 or referenced.get('lod') != 0 or stored.get('lod') != 0
            or referenced.get('coordinateSpace') != 'mesh_local_cm'
            or referenced.get('triangleOrder') != 'native_triangle_ids_and_corner_order'
            or original_stored.get('lod') != 0 or original_stored.get('invalidValues') != 0
            or any(value.get('optionalAttributePolicy') != 'stored_registered_values_authorship_not_inferred'
                   for value in (referenced, stored, original_stored))):
        raise ValueError('Committed terrain readback uses unknown native corner/attribute semantics.')
    comparison = checked_committed_carve(document, referenced, stored, row['mesh'], original_stored)
    if readback['comparison'] != comparison or row['nativeSourcePrefixPreserved'] != comparison['nativeSourcePrefixPreserved']:
        raise ValueError('Terrain committed comparison contradicts its actual saved attributes.')
    policy = readback['sourcePolicy']
    binding = spec.get('sourcePolicySurvey')
    if (not isinstance(binding, dict) or set(binding) != {'path', 'sha256'} or not hash_value(binding.get('sha256'))
            or binding.get('path') != 'artifacts/unreal/aegis-citadel/surveys/' + binding['sha256'] + '.json'):
        raise ValueError('Independent native terrain policy survey must be source-signed and file-bound.')
    survey = json.loads(bound_file(root, binding['path'], binding['sha256']).read_text(encoding='utf-8-sig'))
    observed = survey.get('terrainSourcePolicies', {}).get(SOURCE_MESH)
    actors = [actor for actor in survey.get('actors', {}).get(SOURCE_PACKAGE, []) if actor.get('actor') == IDENTITY['actor']]
    if (survey.get('schemaVersion') != 2 or survey.get('readOnly') is not True or survey.get('nativeGeometryApproved') is not False
            or survey.get('file') != plan.get('baseline', {}).get('file')
            or {key: value for key, value in survey.items() if key != 'actors'} != plan.get('baseline')
            or not isinstance(observed, dict) or set(observed) != {'package', 'actor', 'sourceMeshSha256', 'policy'}
            or observed['package'] != SOURCE_PACKAGE or observed['actor'] != IDENTITY['actor']
            or observed['sourceMeshSha256'] != row['sourceMeshSha256'] or observed['policy'] != policy
            or survey.get('packageHashes', {}).get(SOURCE_MESH_PACKAGE) != row['sourceMeshSha256']
            or survey.get('packageHashes', {}).get(SOURCE_PACKAGE) != city['sourceHashes'].get(SOURCE_PACKAGE)
            or len(actors) != 1 or actors[0].get('state') != row['sourceActorState']):
        raise ValueError('Independent original terrain policy, package or actor survey witness changed.')
    if (not isinstance(policy, dict) or policy != spec.get('sourceNativePolicy') or policy != readback['actualPolicy']
            or set(policy) != {'sourceLods', 'buildSettings', 'reductionSettings', 'mesh', 'bodySetup'}
            or type(policy.get('sourceLods')) is not int or not 1 <= policy['sourceLods'] <= 8
            or any(not isinstance(policy.get(key), list) or len(policy[key]) != policy['sourceLods']
                   for key in ('buildSettings', 'reductionSettings'))
            or not isinstance(policy.get('mesh'), dict) or not isinstance(policy.get('bodySetup'), dict)):
        raise ValueError('Private terrain clone does not retain its source-signed original native policy.')
    audit = payloads['renderDataAudit']
    lods = audit.get('lods', [])
    if (audit.get('readOnly') is not True or audit.get('available') is not True or audit.get('mesh') != row['mesh']
            or not isinstance(lods, list) or len(lods) != policy['sourceLods']
            or [lod.get('lod') for lod in lods] != list(range(policy['sourceLods']))):
        raise ValueError('Actual saved terrain render LODs are incomplete.')
    for lod in lods:
        vertices, indices, basis = lod.get('vertices'), lod.get('indices'), lod.get('tangentBasis', {})
        if (lod.get('cpuReadable') is not True or type(vertices) is not int or vertices <= 0
                or type(indices) is not int or indices <= 0 or indices % 3
                or type(lod.get('uvChannels')) is not int or lod['uvChannels'] < comparison['uvChannels']
                or any(lod.get(key) != 0 for key in ('invalidPositions', 'invalidNormals', 'nonUnitNormals', 'invalidUVs'))
                or basis.get('invalidVertices') != 0 or basis.get('orthogonalVertices') != vertices):
            raise ValueError('Actual saved terrain render attributes are invalid or unavailable.')
    rendered = checked_rendered_carve(document, payloads['originalRenderedFaces'],
        payloads['renderedFaces'], policy, row['mesh'])
    if (readback['renderedComparison'] != rendered or rendered['nativeExteriorRenderPreserved'] is not True
            or lods[0]['indices'] != rendered['cloneTriangles'] * 3
            or lods[0]['uvChannels'] != payloads['renderedFaces']['uvChannels']):
        raise ValueError('Actual original/clone exterior rendered-face comparison contradicts the saved buffers.')


def require_terrain_carves(root, run, plan, city):
    """Rerun clipping and compare complete data, source state and exact actor exception."""
    specs, rows = plan.get('terrainCarves'), city.get('terrainCarves')
    if not isinstance(specs, list) or len(specs) != 1 or not isinstance(rows, list) or len(rows) != 1:
        raise ValueError('The explicit source-bound occupied hall terrain carve is required.')
    spec, row = specs[0], rows[0]
    if not isinstance(spec, dict) or not isinstance(row, dict): raise ValueError('Malformed terrain carve identity.')
    prefix = '/Game/WorldRebuild/AegisCitadel_' + str(city.get('revision'))
    owned_mesh = prefix + '/Meshes/SM_HallCarvedMountain'
    if (not re.fullmatch('[a-f0-9]{12}', str(city.get('revision')))
            or any(row.get(k) != v or spec.get(k) != v for k, v in IDENTITY.items())
            or spec.get('package') != SOURCE_PACKAGE or row.get('sourcePackage') != SOURCE_PACKAGE
            or not re.fullmatch(re.escape(prefix) + r'/Layers/RetainedCity_[0-9]+', str(row.get('package')))
            or row.get('package') not in city.get('sceneryLevels', [])
            or not hash_value(city.get('packageHashes', {}).get(row.get('package')))
            or spec.get('sourceMesh') != SOURCE_MESH or row.get('sourceMesh') != SOURCE_MESH
            or not hash_value(spec.get('sourceMeshPackageSha256'))
            or row.get('sourceMeshSha256') != spec['sourceMeshPackageSha256']
            or city.get('sourceHashes', {}).get(SOURCE_MESH_PACKAGE) != spec['sourceMeshPackageSha256']
            or SOURCE_MESH_PACKAGE in city.get('packageHashes', {})
            or row.get('mesh') != owned_mesh + '.SM_HallCarvedMountain'
            or not hash_value(row.get('meshSha256')) or city.get('packageHashes', {}).get(owned_mesh) != row['meshSha256']
            or row.get('actorTransform') != MOUNTAIN_ACTOR_TRANSFORM or spec.get('actorTransform') != MOUNTAIN_ACTOR_TRANSFORM
            or row.get('worldVolumes') != [HALL_CARVE_WORLD] or spec.get('worldVolumes') != [HALL_CARVE_WORLD]
            or row.get('localVolumeBounds') != LOCAL_BOUNDS or spec.get('localVolumeBounds') != LOCAL_BOUNDS
            or row.get('nativeSourcePrefixPreserved') is not True):
        raise ValueError('Terrain source, private ownership, transform or occupied cut volume changed.')
    source = row.get('sourceActorState'); actual = row.get('actualActorState')
    if (not isinstance(source, dict) or not isinstance(actual, dict)
            or value_sha(source) != spec.get('sourceStateHash') or value_sha(source) != row.get('sourceActorStateHash')
            or value_sha(actual) != row.get('actualActorStateHash')
            or source.get('class') != IDENTITY['klass'] or source.get('label') != IDENTITY['label']
            or source.get('transform') != [25000, 0, 0, 0, 0, 0, 1, 1, 1, 1]
            or IDENTITY['requiredTag'] not in source.get('tags', []) or row.get('actualTags') != source.get('tags')):
        raise ValueError('Actual source or retained mountain actor state changed.')
    expected = deepcopy(source)
    components = [component for component in expected.get('components', []) if component.get('name') == IDENTITY['component']]
    if (len(components) != 1 or components[0].get('mesh') != SOURCE_MESH
            or components[0].get('class') != 'StaticMeshComponent'
            or components[0].get('transform') != source['transform']):
        raise ValueError('The exact original mountain mesh component is unavailable.')
    components[0]['mesh'] = row['mesh']
    if expected != actual:
        raise ValueError('Terrain exception changed an unrelated actor/component attribute.')
    export_binding = row.get('sourceExport', {}); clip_binding = row.get('clippedDocument', {})
    if export_binding.get('path') != 'terrain-carves/mountain-source.json' or clip_binding.get('path') != 'terrain-carves/hall-carve.json':
        raise ValueError('Terrain carve evidence escaped its explicit candidate files.')
    source_file = bound_file(run, export_binding['path'], export_binding.get('sha256'))
    clip_file = bound_file(run, clip_binding['path'], clip_binding.get('sha256'))
    if export_binding['sha256'] != spec.get('sourceExportSha256'):
        raise ValueError('Candidate terrain source differs from its original native export.')
    original_source = bound_file(root, spec.get('sourceExportFile'), spec.get('sourceExportSha256'))
    if original_source.read_bytes() != source_file.read_bytes():
        raise ValueError('Actual committed terrain source was substituted in the candidate.')
    original_receipt = json.loads(bound_file(root, spec.get('sourceReceiptFile'), spec.get('sourceReceiptSha256')).read_text(encoding='utf-8-sig'))
    before, after = original_receipt.get('packagesBefore'), original_receipt.get('packagesAfter')
    if (original_receipt.get('readOnly') is not True or original_receipt.get('noPackagesSaved') is not True
            or original_receipt.get('nativeSourceExportObserved') is not True or original_receipt.get('inspectionOnly') is not True
            or original_receipt.get('sourcePackage') != SOURCE_PACKAGE or original_receipt.get('sourceMesh') != SOURCE_MESH
            or original_receipt.get('actor') != IDENTITY['actor'] or original_receipt.get('actorTransform') != MOUNTAIN_ACTOR_TRANSFORM
            or original_receipt.get('sourceSha256') != export_binding['sha256']
            or original_receipt.get('sourceActorState') != source or original_receipt.get('sourceActorStateSha256') != value_sha(source)
            or not isinstance(before, dict) or before != after or before.get(SOURCE_MESH_PACKAGE) != row['sourceMeshSha256']
            or before.get(SOURCE_PACKAGE) != city.get('sourceHashes', {}).get(SOURCE_PACKAGE)):
        raise ValueError('Native terrain source receipt does not prove unchanged original source custody.')
    document = json.loads(clip_file.read_text(encoding='utf-8-sig'))
    if not isinstance(document, dict) or not isinstance(document.get('carveReceipt'), dict):
        raise ValueError('Native terrain clipped document is malformed.')
    # Descriptive provenance is preserved but grants no trust. Raw arrays and every
    # clipped triangle/attribute are independently regenerated from actual export.
    # The importer binds the literal export bytes. Text-mode newline conversion
    # would substitute a different source payload before regenerating geometry.
    reproduced = native_terrain_carve_document(source_file.read_bytes().decode('utf-8'),
        source_provenance=document['carveReceipt'].get('sourceProvenance'))
    if reproduced != document or row.get('outsidePreservation') != reproduced['carveReceipt']['outsidePreservation']:
        raise ValueError('Clipped terrain topology/attributes or unaffected-triangle witness changed.')
    require_native_readback(root, run, plan, city, spec, row, document)
    for boundary in city.get('outsideMaskPreservation', []):
        expected_ids = [IDENTITY['id']] if boundary.get('source') == SOURCE_PACKAGE and boundary.get('candidate') == row['package'] else []
        if boundary.get('explicitTerrainCarves') != expected_ids:
            raise ValueError('An unrelated actor was allowed through terrain preservation exceptions.')
    if not any(boundary.get('source') == SOURCE_PACKAGE and boundary.get('candidate') == row['package']
               for boundary in city.get('outsideMaskPreservation', [])):
        raise ValueError('Terrain carve lacks its exact copied-layer preservation boundary.')


if __name__ == '__main__':
    try:
        root, run = [Path(value).resolve() for value in sys.argv[1:3]]
        run.relative_to(root / 'artifacts/unreal/aegis-citadel')
        AUDITED_FILES = {}
        for module in (__file__, sys.modules['aegis_citadel_terrain'].__file__,
                       sys.modules['aegis_citadel_terrain_readback'].__file__,
                       sys.modules['aegis_citadel_terrain_render_readback'].__file__):
            sha(Path(module))
        sha(run / 'blueprint.json')
        sha(run / 'candidate.json')
        plan = json.loads((run / 'blueprint.json').read_text(encoding='utf-8-sig'))
        city = json.loads((run / 'candidate.json').read_text(encoding='utf-8-sig'))
        require_terrain_carves(root, run, plan, city)
        inputs = dict(AUDITED_FILES)
        for filename, expected in inputs.items():
            if sha(Path(filename)) != expected:
                raise ValueError('Terrain audit input changed before its result was emitted.')
        print(json.dumps(dict(schemaVersion=1, passed=True, physicalApproval=False,
            visualApproval=False, inputHashes=inputs), sort_keys=True))
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
