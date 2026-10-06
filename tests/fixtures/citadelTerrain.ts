import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

/** Portable array fixtures and explicitly unusable package bytes; no native observation is claimed. */
export function citadelTerrainFixture(repository: string, revision: string, sourceHashes: Record<string, string>) {
  const hash = (bytes: string) => createHash('sha256').update(bytes).digest('hex');
  const run = path.join(repository, 'artifacts/unreal/aegis-citadel', revision);
  const sourcePackage = '/Game/WorldRebuild/DutchBastion_d105951f4aab/Layers/authored';
  const sourceMeshPackage = '/Game/Capitals/crownward/Terrain_mountain', sourceMesh = sourceMeshPackage + '.Terrain_mountain';
  const ownedMesh = `/Game/WorldRebuild/AegisCitadel_${revision}/Meshes/SM_HallCarvedMountain`;
  const actorState = { class: 'StaticMeshActor', label: 'Crownward authored mountain massif',
    transform: [25000, 0, 0, 0, 0, 0, 1, 1, 1, 1], tags: ['WarCrownwardTerrain', 'WarZoneObject_aegis_capital_StaticMeshActor_306'],
    components: [{ name: 'StaticMeshComponent0', class: 'StaticMeshComponent', tags: [], transform: [25000, 0, 0, 0, 0, 0, 1, 1, 1, 1],
      visible: true, mobility: 'Static', collision: 'BlockAll', collisionEnabled: 'QueryAndPhysics',
      mesh: sourceMesh, materials: ['/Game/Materials/Portable.Portable'] }] };
  const stateSha = hash(JSON.stringify(actorState)); // Rebound by the canonical Python fixture below.
  const transform = { translationCm: [25000, 0, 0], rotationQuaternion: [0, 0, 0, 1], scale: [1, 1, 1] };
  const volume = { id: 'occupied_commander_hall', coordinateSpace: 'world_cm', bounds: [[25960, -4260, 5980], [33460, 4260, 24000]] };
  const source = { schemaVersion: 1, readOnly: true, available: true, valid: true, lod: 0, mesh: sourceMesh, invalidValues: 0,
    sourcePolicy: 'committed_mesh_description_bulk_data_no_working_copy', coordinateSpace: 'mesh_local_cm',
    triangleOrder: 'native_triangle_ids_and_corner_order', optionalAttributePolicy: 'stored_registered_values_authorship_not_inferred',
    sourceTriangleCount: 2, sourceVertexCount: 6, sourceVertexInstanceCount: 6,
    triangleIds: [0, 1], trianglePolygonIds: [0, 1], trianglePolygonGroupIds: [0, 0],
    cornerVertexIds: [0, 1, 2, 3, 4, 5], cornerVertexInstanceIds: [0, 1, 2, 3, 4, 5],
    materialSlots: [{ index: 0, slotName: 'Surface', importedSlotName: 'Surface', material: '/Game/Materials/Portable.Portable' }],
    polygonGroups: [{ id: 0, slotName: 'Surface', materialIndex: 0 }],
    data: { positions: [[0, 0, 0], [100, 0, 0], [0, 100, 0], [900, 0, 6010], [1100, 0, 6010], [900, 200, 6010]],
      indices: [0, 1, 2, 3, 4, 5], normals: Array.from({ length: 6 }, () => [0, 0, 1]),
      tangents: Array.from({ length: 6 }, () => [1, 0, 0]), binormalSigns: Array(6).fill(1),
      vertexColors: Array.from({ length: 6 }, () => [1, 1, 1, 1]),
      uvs: [[0, 0], [1, 0], [0, 1], [0, 0], [1, 0], [0, 1]],
      uvChannels: [[[0, 0], [1, 0], [0, 1], [0, 0], [1, 0], [0, 1]]], triangleMaterials: [0, 0] } };
  // Native Windows exports bind CRLF bytes; text-mode verification must not
  // silently turn their source payload into an LF document.
  const raw = JSON.stringify(source, null, 2).replace(/\n/g, '\r\n');
  const result = spawnSync('python', ['-B', '-c',
    'import sys,json;sys.path.insert(0,"scripts/unreal");from aegis_citadel_terrain import native_terrain_carve_document;from citadel_terrain_evidence import value_sha;v=json.load(sys.stdin);print(json.dumps(dict(document=native_terrain_carve_document(v["raw"],source_provenance={"portableFixture":True}),stateSha=value_sha(v["state"]))))'],
  { input: JSON.stringify({ raw, state: actorState }), encoding: 'utf8', windowsHide: true });
  if (result.error || result.status !== 0) throw new Error(result.error?.message ?? result.stderr);
  const generated = JSON.parse(result.stdout), document = generated.document;
  const actualState = structuredClone(actorState); actualState.components[0].mesh = ownedMesh + '.SM_HallCarvedMountain';
  const actualShaResult = spawnSync('python', ['-B', '-c',
    'import sys,json;sys.path.insert(0,"scripts/unreal");from citadel_terrain_evidence import value_sha;print(value_sha(json.load(sys.stdin)))'],
  { input: JSON.stringify(actualState), encoding: 'utf8', windowsHide: true });
  if (actualShaResult.error || actualShaResult.status !== 0) throw new Error(actualShaResult.error?.message ?? actualShaResult.stderr);
  const original = 'artifacts/unreal/portable-terrain/source.json', originalReceipt = 'artifacts/unreal/portable-terrain/receipt.json';
  function textFile(file: string, bytes: string) { mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, bytes); return hash(bytes); }
  const meshHash = textFile(path.join(repository, 'unreal/AegisWar/Content/Capitals/crownward/Terrain_mountain.uasset'), 'PORTABLE TERRAIN SOURCE ONLY');
  const ownedHash = textFile(path.join(repository, 'unreal/AegisWar/Content', ownedMesh.slice(6)) + '.uasset', 'PORTABLE CARVED TERRAIN ONLY');
  textFile(path.join(repository, original), raw); textFile(path.join(run, 'terrain-carves/mountain-source.json'), raw);
  const clipHash = textFile(path.join(run, 'terrain-carves/hall-carve.json'), JSON.stringify(document));
  const before = { [sourcePackage]: sourceHashes[sourcePackage], [sourceMeshPackage]: meshHash };
  const receipt = { readOnly: true, noPackagesSaved: true, nativeSourceExportObserved: true, inspectionOnly: true,
    sourcePackage, sourceMesh, actor: 'StaticMeshActor_306', actorTransform: transform, sourceSha256: hash(raw),
    sourceActorState: actorState, sourceActorStateSha256: generated.stateSha, packagesBefore: before, packagesAfter: before };
  const receiptHash = textFile(path.join(repository, originalReceipt), JSON.stringify(receipt));
  const identity = { id: 'occupied_commander_hall', actor: 'StaticMeshActor_306', klass: 'StaticMeshActor',
    label: actorState.label, component: 'StaticMeshComponent0', requiredTag: actorState.tags[1] };
  const spec = { ...identity, package: sourcePackage, sourceStateHash: generated.stateSha || stateSha,
    sourceMesh, sourceMeshPackageSha256: meshHash, actorTransform: transform, worldVolumes: [volume],
    localVolumeBounds: document.localVolumeBounds, sourceExportFile: original, sourceExportSha256: hash(raw),
    sourceReceiptFile: originalReceipt, sourceReceiptSha256: receiptHash };
  const readbackResult = spawnSync('python', ['-B', '-c', [
    'import sys,runpy',
    'sys.path.insert(0,"scripts/unreal")',
    'runpy.run_path("tests/fixtures/citadelTerrainReadback.py",run_name="__main__")',
  ].join('\n')], { input: JSON.stringify({ document, mesh: ownedMesh + '.SM_HallCarvedMountain' }), encoding: 'utf8', windowsHide: true });
  if (readbackResult.error || readbackResult.status !== 0) throw new Error(readbackResult.error?.message ?? readbackResult.stderr);
  const generatedReadback = JSON.parse(readbackResult.stdout);
  const binding = (name: string, value: unknown) => { const relative = 'terrain-carves/' + name;
    return { path: relative, sha256: textFile(path.join(run, relative), JSON.stringify(value)) }; };
  const helpers = ['aegis_citadel_terrain_readback.py', 'aegis_citadel_terrain_render_readback.py'];
  const helperHashes = Object.fromEntries(helpers.map(helper => [helper,
    textFile(path.join(repository, 'scripts/unreal', helper), readFileSync(path.join('scripts/unreal', helper), 'utf8'))]));
  const policy = generatedReadback.policy;
  const surveyPath = 'artifacts/unreal/portable-terrain/policy-survey.json';
  const policySurvey = { schemaVersion: 2, file: surveyPath, readOnly: true, nativeGeometryApproved: false,
    packageHashes: before, terrainSourcePolicies: { [sourceMesh]: { package: sourcePackage, actor: identity.actor, sourceMeshSha256: meshHash, policy } },
    actors: { [sourcePackage]: [{ actor: identity.actor, state: actorState }] } };
  const surveyBytes = JSON.stringify(policySurvey), surveySha = textFile(path.join(repository, surveyPath), surveyBytes);
  const immutableSurveyPath = 'artifacts/unreal/aegis-citadel/surveys/' + surveySha + '.json';
  textFile(path.join(repository, immutableSurveyPath), surveyBytes);
  const { actors: _actors, ...baseline } = policySurvey;
  const nativeReadback = { comparison: generatedReadback.comparison,
    referencedSource: binding('hall-carve-committed-source.json', generatedReadback.referenced),
    storedCorners: binding('hall-carve-stored-corners.json', generatedReadback.stored),
    renderDataAudit: binding('hall-carve-render-data.json', generatedReadback.render),
    originalStoredCorners: binding('hall-carve-original-stored-corners.json', generatedReadback.originalStored),
    originalRenderedFaces: binding('hall-carve-original-rendered-faces.json', generatedReadback.originalFaces),
    renderedFaces: binding('hall-carve-rendered-faces.json', generatedReadback.renderedFaces),
    renderedComparison: generatedReadback.renderedComparison,
    sourcePolicy: policy, actualPolicy: policy, nativePolicyPreserved: true };
  const row = { ...identity, sourcePackage, package: `/Game/WorldRebuild/AegisCitadel_${revision}/Layers/RetainedCity_0`,
    sourceMesh, sourceMeshSha256: meshHash, mesh: ownedMesh + '.SM_HallCarvedMountain', meshSha256: ownedHash,
    actorTransform: transform, worldVolumes: [volume], localVolumeBounds: document.localVolumeBounds,
    sourceActorState: actorState, sourceActorStateHash: generated.stateSha, actualActorState: actualState,
    actualActorStateHash: actualShaResult.stdout.trim(), actualTags: actorState.tags,
    sourceExport: { path: 'terrain-carves/mountain-source.json', sha256: hash(raw) },
    clippedDocument: { path: 'terrain-carves/hall-carve.json', sha256: clipHash },
    outsidePreservation: document.carveReceipt.outsidePreservation, nativeSourcePrefixPreserved: true, nativeReadback };
  return { terrainCarves: [row], planTerrainCarves: [{ ...spec, sourceNativePolicy: policy, sourcePolicySurvey: { path: immutableSurveyPath, sha256: surveySha } }],
    baseline, sourceHashes: { [sourceMeshPackage]: meshHash },
    packageHashes: { [ownedMesh]: ownedHash }, sourceRecipes: helperHashes, stageDependencySha256: helperHashes };
}
