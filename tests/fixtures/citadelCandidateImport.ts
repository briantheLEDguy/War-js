import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { CITADEL_NATIVE_IMPORT_CONVENTION, CITADEL_NATIVE_MESH_BUILD_SETTINGS, CITADEL_NATIVE_TANGENT_POLICY, CITADEL_MATTE_NAVY } from '../../scripts/unreal/citadel-import-evidence';

/** Portable boundary data only; these bytes are not usable native model assets. */
export function citadelCandidateImportFixture(repository: string, revision: string, signature: string) {
  const directory = path.join(repository, 'artifacts/unreal/aegis-citadel', revision);
  const prefix = `/Game/WorldRebuild/AegisCitadel_${revision}`;
  const hash = (value: string) => createHash('sha256').update(value).digest('hex');
  const assets: any[] = [], bindings: any[] = [], packageHashes: Record<string, string> = {};
  const contents = JSON.stringify({ positions: [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
    normals: [[0, 0, 1], [0, 0, 1], [0, 0, 1]], uvs: [[0, 0], [1, 0], [0, 1]], indices: [0, 1, 2] });
  mkdirSync(path.join(directory, 'runtime'), { recursive: true });
  for (let i = 0; i < 38; i++) {
    const id = `asset_${String(i).padStart(2, '0')}`, meshFile = `runtime/${id}.mesh.json`;
    writeFileSync(path.join(directory, meshFile), contents);
    const packageName = `${prefix}/Meshes/SM_${id}`, bytes = `PORTABLE TEST PACKAGE ONLY: ${id}`;
    const file = path.join(repository, 'unreal/AegisWar/Content', packageName.slice(6)) + '.uasset';
    mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, bytes); packageHashes[packageName] = hash(bytes);
    assets.push({ id, meshFile, sha256: hash(contents), triangles: 1, gateLeaf: false });
    const renderDataAudit = { readOnly: true, available: true, mesh: `${packageName}.SM_${id}`, lods: [
      { lod: 0, cpuReadable: true, vertices: 3, indices: 3, uvChannels: 2, invalidPositions: 0, invalidNormals: 0,
        nonUnitNormals: 0, invalidUVs: 0, committedSourcePositionMissing: 0, committedSourceNormalDifferent: 0, committedSourceNormalMatches: 3,
        sourcePositionToleranceCm: .1, sourceNormalDotThreshold: .995,
        sourceMatchingPolicy: 'oriented_triangle_corners_material_and_uv0', committedSourceTriangleMatches: 1,
        committedSourceTrianglesMissing: 0, committedSourceTrianglesDifferent: 0,
        sourceUvAbsoluteTolerance: .0005, sourceUvRelativeTolerance: .001,
        tangentBasis: { ...CITADEL_NATIVE_TANGENT_POLICY, invalidVertices: 0, orthogonalVertices: 3,
          badVertexSamples: [], badVertexSamplesTruncated: false,
          axes: Object.fromEntries(['x', 'y', 'z'].map(axis => [axis, { finite: 3, nonFinite: 0, nearZero: 0, unit: 3, nonUnit: 0,
            unitSquaredTolerance: Math.fround(axis === 'y' ? .04 : .02), minimumLength: 1, maximumLength: 1 }])),
          pairs: Object.fromEntries(['xy', 'xz', 'yz'].map(pair => [pair, { evaluated: 3, skipped: 0, orthogonal: 3,
            nonOrthogonal: 0, maximumAbsoluteNormalizedDot: 0 }])) } }] };
    const renderDataAuditPayload = JSON.stringify(renderDataAudit);
    bindings.push({ id, mesh: packageName, sha256: hash(bytes), gateLeaf: false, triangles: [1],
      sourceIndicesSha256: hash('[0,1,2]'), nativeIndicesSha256: hash('[0,2,1]'),
      sourceArrayHashConvention: 'sha256_raw_utf8_mesh_json_member_array',
      sourcePositionsSha256: hash('[[0,0,0],[1,0,0],[0,1,0]]'), sourceNormalsSha256: hash('[[0,0,1],[0,0,1],[0,0,1]]'),
      sourceUVsSha256: hash('[[0,0],[1,0],[0,1]]'), nativeMeshBuildSettings: { ...CITADEL_NATIVE_MESH_BUILD_SETTINGS },
      renderDataAudit, renderDataAuditPayload, renderDataAuditSha256: hash(renderDataAuditPayload) });
  }
  const geometrySignature = hash(JSON.stringify(assets.map(asset => [asset.id, asset.sha256])));
  const materialPackage=prefix+'/Materials/M_blue',materialBytes='PORTABLE MATTE GRAPH FIXTURE ONLY';
  const materialFile=path.join(repository,'unreal/AegisWar/Content',materialPackage.slice(6))+'.uasset';
  mkdirSync(path.dirname(materialFile),{recursive:true});writeFileSync(materialFile,materialBytes);
  packageHashes[materialPackage]=hash(materialBytes);
  const materialSpecs={blue:structuredClone(CITADEL_MATTE_NAVY)};
  const materialBindings=[{role:'blue',package:materialPackage,sha256:hash(materialBytes),sourceSpec:structuredClone(CITADEL_MATTE_NAVY),
    actualConstantReadback:{tint:CITADEL_MATTE_NAVY.tint.map(Math.fround),roughness:Math.fround(.92),metallic:0,specular:.25,
      normalInputConnected:false,ambientOcclusionInputConnected:false}}];
  const master = 'PORTABLE TEST SOURCE ONLY'; mkdirSync(path.join(directory, 'sources'), { recursive: true });
  writeFileSync(path.join(directory, 'sources/fixture.blend'), master);
  writeFileSync(path.join(directory, 'assets-source.json'), JSON.stringify({ schemaVersion: 1, revision,
    blueprintSignature: signature, geometrySignature, assets, materialSpecs, sourceMaster: { path: 'sources/fixture.blend', sha256: hash(master) } }));
  const teamSpawns = Array.from({ length: 6 }, () => [0, 0, 0]);
  const proofStart = { actor: `${prefix}/SiegeCandidate.SiegeCandidate:PersistentLevel.PlayerStart_0`,
    sourceTeamSpawnIndex: 1, signedFloorCm: [0, 0, 0], locationCm: [0, 0, 99], actualFloorZCm: 0,
    capsuleRadiusCm: 42, capsuleHalfHeightCm: 96, traceChannel: 'Visibility', traceComplex: true,
    capsuleClear: true, otherStartsPreserved: 0 };
  return { geometrySignature, nativeImportConvention: { ...CITADEL_NATIVE_IMPORT_CONVENTION }, bindings,
    packageHashes, proofStart, teamSpawns, directory, assets, materialSpecs, materialBindings };
}
