import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, expect, test } from 'vitest';
import { requireNativeCitadelImport,requireNativeCitadelMaterials,requireNativeCitadelNormalTextures,requireVersionedCitadelMeshBindings } from '../scripts/unreal/citadel-import-evidence';
import { citadelCandidateImportFixture } from './fixtures/citadelCandidateImport';

const roots: string[] = [];
test('mesh recipe preserves legacy manifests and requires the new footing identity', () => {
  const legacy = Array.from({ length: 38 }, (_, i) => ({ id: `asset_${i}` }));
  const current = [...legacy, { id: 'wing_foundation_repairs' }];
  for (const recipeVersion of [1, 6, 7, 8]) {
    expect(() => requireVersionedCitadelMeshBindings({ recipeVersion }, legacy, legacy)).not.toThrow();
    expect(() => requireVersionedCitadelMeshBindings({ recipeVersion }, current, current)).toThrow();
  }
  expect(() => requireVersionedCitadelMeshBindings({ recipeVersion: 9 }, current, current)).not.toThrow();
  for (const [assets, bindings] of [[legacy, legacy], [current, legacy],
    [current, [...legacy, legacy[0]]], [current, [...legacy, { id: 'wrong_mesh' }]],
    [[...legacy, { id: 'wrong_mesh' }], [...legacy, { id: 'wrong_mesh' }]]]) {
    expect(() => requireVersionedCitadelMeshBindings({ recipeVersion: 9 }, assets, bindings)).toThrow();
  }
  for (const recipeVersion of [0, 13, true, '9', null, 9.5])
    expect(() => requireVersionedCitadelMeshBindings({ recipeVersion }, current, current)).toThrow();
});
test('recipe ten requires every room and terrace furnishing group without reinterpreting old revisions', () => {
  const current = [...Array.from({length:38},(_,i)=>({id:`asset_${i}`})), {id:'wing_foundation_repairs'}];
  const dressed = [...current,...['forehall','throne_hall','west_archive','east_treasury','west_terrace','east_terrace'].map(key=>({id:`dressing_${key}`}))];
  for (const recipeVersion of [10, 11, 12])
    expect(() => requireVersionedCitadelMeshBindings({recipeVersion},dressed,dressed)).not.toThrow();
  for (const key of dressed.slice(39)) {
    const wrong = dressed.map(row=>row===key?{id:'unrecorded_room'}:row);
    for (const recipeVersion of [10, 11, 12])
      expect(() => requireVersionedCitadelMeshBindings({recipeVersion},wrong,wrong)).toThrow(/Furnishing groups/);
  }
  expect(() => requireVersionedCitadelMeshBindings({recipeVersion:9},dressed,dressed)).toThrow();
});
test('recipe eleven requires original OpenGL texture conversion while preserving historical imports', () => {
  const file='public/assets/textures/aegis_citadel_interiors/citadel_normal.png';
  const packageName='/Game/WorldRebuild/AegisCitadel_0123456789ab/Textures/T_citadel_normal_normal';
  const source={materialSpecs:{furniture:{normal:file,normalConvention:'gltf_opengl_positive_y'}},materialSources:{[file]:'a'.repeat(64)}};
  const receipt={revision:'0123456789ab',packageHashes:{[packageName]:'b'.repeat(64)},nativeNormalTextureBindings:[{
    source:file,sourceSha256:'a'.repeat(64),sourceConvention:'gltf_opengl_positive_y',package:packageName,sha256:'b'.repeat(64),
    actualFlipGreenChannel:true,actualSrgb:false,actualCompression:'TC_NORMALMAP',
  }]};
  expect(() => requireNativeCitadelNormalTextures({},source,{recipeVersion:10})).not.toThrow();
  expect(() => requireNativeCitadelNormalTextures(receipt,source,{recipeVersion:11})).not.toThrow();
  for (const change of [{actualFlipGreenChannel:false},{actualSrgb:true},{actualCompression:'TC_DEFAULT'},
    {sourceConvention:'unrecorded'},{sha256:'c'.repeat(64)},{sourceSha256:'c'.repeat(64)},
    {package:'/Game/Other/T_citadel_normal_normal'}]) {
    const invalid=structuredClone(receipt);Object.assign(invalid.nativeNormalTextureBindings[0],change);
    expect(() => requireNativeCitadelNormalTextures(invalid,source,{recipeVersion:11})).toThrow(/normal/);
  }
  const duplicate=structuredClone(receipt);duplicate.nativeNormalTextureBindings.push(duplicate.nativeNormalTextureBindings[0]);
  expect(() => requireNativeCitadelNormalTextures(duplicate,source,{recipeVersion:11})).toThrow(/normal/);
  const unsigned=structuredClone(source);unsigned.materialSpecs.furniture.normalConvention='unrecorded';
  expect(() => requireNativeCitadelNormalTextures(receipt,unsigned,{recipeVersion:11})).toThrow(/normal/);
});
test('portable publication/import invariants run with the normal Unreal tooling suite', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealCitadelPublication.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
afterEach(() => roots.splice(0).forEach(root => rmSync(root, { recursive: true, force: true })));
function fixture() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'citadel-import-evidence-')); roots.push(root);
  const revision = '0123456789ab', signature = 'a'.repeat(64);
  const imported = citadelCandidateImportFixture(root, revision, signature);
  const receipt = { ...imported, revision, signature, siegeMap: `/Game/WorldRebuild/AegisCitadel_${revision}/SiegeCandidate` };
  return { ...imported, receipt, blueprint: { teamSpawns: imported.teamSpawns } };
}
function bindAudit(binding: any) {
  binding.renderDataAuditPayload = JSON.stringify(binding.renderDataAudit);
  binding.renderDataAuditSha256 = createHash('sha256').update(binding.renderDataAuditPayload).digest('hex');
}
test('matte navy requires actual scalar graph witnesses, original tint and no unrelated normal or AO input', () => {
  const f=fixture();
  expect(() => requireNativeCitadelMaterials(f.receipt,{materialSpecs:f.materialSpecs})).not.toThrow();
  for (const alter of [
    (r:any) => { delete r.materialBindings; }, (r:any) => { r.materialBindings.push(r.materialBindings[0]); },
    (r:any) => { r.materialBindings[0].sha256='0'.repeat(64); },
    (r:any) => { r.materialBindings[0].package='/Game/Other/M_blue'; },
    (r:any) => { r.materialBindings[0].sourceSpec.tint=[.018,.075,.23]; },
    (r:any) => { r.materialBindings[0].actualConstantReadback.tint[0]=.018; },
    (r:any) => { r.materialBindings[0].actualConstantReadback.specular=.5; },
    (r:any) => { r.materialBindings[0].actualConstantReadback.roughness=NaN; },
    (r:any) => { r.materialBindings[0].actualConstantReadback.normalInputConnected=true; },
    (r:any) => { r.materialBindings[0].actualConstantReadback.ambientOcclusionInputConnected=true; },
    (r:any) => { delete r.materialBindings[0].actualConstantReadback.normalInputConnected; },
  ]) { const receipt=structuredClone(f.receipt);alter(receipt);
    expect(() => requireNativeCitadelMaterials(receipt,{materialSpecs:f.materialSpecs})).toThrow(/matte navy/); }
  const source=structuredClone(f.materialSpecs); (source.blue as any).normal='unrelated texture';
  expect(() => requireNativeCitadelMaterials(f.receipt,{materialSpecs:source})).toThrow(/matte navy/);
});
test('all thirty-eight native meshes bind the index-only convention and preserved source bytes', () => {
  const f = fixture(), before = JSON.stringify(f.receipt);
  expect(() => requireNativeCitadelImport(f.directory, f.receipt, f.blueprint)).not.toThrow();
  expect(JSON.stringify(f.receipt)).toBe(before);
  for (const alter of [
    (r: typeof f.receipt) => { r.nativeImportConvention.normalPolicy = 'recompute'; },
    (r: typeof f.receipt) => { r.bindings[0].nativeIndicesSha256 = r.bindings[0].sourceIndicesSha256; },
    (r: typeof f.receipt) => { r.bindings[0].mesh = '/Game/OtherMesh'; },
    (r: typeof f.receipt) => { r.bindings[1].id = r.bindings[0].id; },
    (r: typeof f.receipt) => { r.bindings.pop(); },
  ]) { const receipt = structuredClone(f.receipt); alter(receipt); expect(() => requireNativeCitadelImport(f.directory, receipt, f.blueprint)).toThrow(); }
});
test('a source cannot claim CCW outward faces after its normals or triangle order reverse', () => {
  const f = fixture(), file = path.join(f.directory, f.assets[0].meshFile);
  const mesh = JSON.parse(readFileSync(file, 'utf8')); mesh.indices = [0, 2, 1];
  const contents = JSON.stringify(mesh); writeFileSync(file, contents);
  const manifestFile = path.join(f.directory, 'assets-source.json'), source = JSON.parse(readFileSync(manifestFile, 'utf8'));
  source.assets[0].sha256 = createHash('sha256').update(contents).digest('hex');
  source.geometrySignature = createHash('sha256').update(JSON.stringify(source.assets.map((row: any) => [row.id, row.sha256]))).digest('hex');
  f.receipt.geometrySignature = source.geometrySignature; writeFileSync(manifestFile, JSON.stringify(source));
  expect(() => requireNativeCitadelImport(f.directory, f.receipt, f.blueprint)).toThrow(/outward-normal winding/);
});
test('private proof admission cannot move from the signed safe spawn or fabricate collision clearance', () => {
  const f = fixture();
  for (const change of [{ locationCm: [0, 0, 5000] }, { actualFloorZCm: 100 }, { capsuleClear: false },
    { actor: '/Game/Other.Other:PersistentLevel.PlayerStart_0' }, { capsuleRadiusCm: 10 }, { traceComplex: false }]) {
    const receipt = { ...f.receipt, proofStart: { ...f.receipt.proofStart, ...change } };
    expect(() => requireNativeCitadelImport(f.directory, receipt, f.blueprint)).toThrow(/private proof start/);
  }
  writeFileSync(path.join(f.directory, 'sources/fixture.blend'), 'independently changed author source');
  expect(() => requireNativeCitadelImport(f.directory, f.receipt, f.blueprint)).toThrow(/Blender master changed/);
});
test('actual render buffers bind every LOD and committed authored normals independently of reduced Python UV exposure', () => {
  const f = fixture();
  for (const change of [
    (b: any) => { delete b.renderDataAuditPayload; },
    (b: any) => { b.sourceNormalsSha256 = '0'.repeat(64); },
    (b: any) => { b.nativeMeshBuildSettings.recompute_normals = true; },
    ...['cpuReadable', 'uvChannels', 'invalidNormals', 'nonUnitNormals', 'invalidUVs', 'committedSourceNormalDifferent',
      'committedSourcePositionMissing', 'committedSourceNormalMatches', 'sourcePositionToleranceCm', 'sourceNormalDotThreshold'].map(key => (b: any) => {
      b.renderDataAudit.lods[0][key] = key === 'cpuReadable' ? false : key === 'uvChannels' ? 0 : 1;
      b.renderDataAuditPayload = JSON.stringify(b.renderDataAudit);
      b.renderDataAuditSha256 = createHash('sha256').update(b.renderDataAuditPayload).digest('hex');
    }),
  ]) {
    const receipt = structuredClone(f.receipt); change(receipt.bindings[0]);
    expect(() => requireNativeCitadelImport(f.directory, receipt, f.blueprint)).toThrow(/render|source normal/);
  }
  (f.receipt.bindings[0] as any).sourceDescriptionUVChannels = 0;
  expect(() => requireNativeCitadelImport(f.directory, f.receipt, f.blueprint)).not.toThrow();
});
test('oriented triangle corner, material and UV matching is mandatory even when all vertex normals pass', () => {
  const f = fixture();
  for (const [key, value] of [
    ['sourceMatchingPolicy', 'position_only'], ['committedSourceTriangleMatches', 0], ['committedSourceTrianglesMissing', 1],
    ['committedSourceTrianglesDifferent', 1], ['sourceUvAbsoluteTolerance', .1], ['sourceUvRelativeTolerance', .1],
    ['sourceMatchingPolicy', undefined],
  ]) {
    const receipt = structuredClone(f.receipt), binding = receipt.bindings[0];
    binding.renderDataAudit.lods[0][String(key)] = value;
    binding.renderDataAuditPayload = JSON.stringify(binding.renderDataAudit);
    binding.renderDataAuditSha256 = createHash('sha256').update(binding.renderDataAuditPayload).digest('hex');
    expect(() => requireNativeCitadelImport(f.directory, receipt, f.blueprint)).toThrow(/render/);
  }
});

test('actual tangent evidence covers every reduced LOD as well as the original source faces', () => {
  const f = fixture(), binding = f.receipt.bindings[0], original = binding.renderDataAudit.lods[0];
  binding.renderDataAudit.lods.push({ ...structuredClone(original), lod: 1 }, { ...structuredClone(original), lod: 2 });
  binding.triangles = [1, 1, 1]; bindAudit(binding);
  expect(() => requireNativeCitadelImport(f.directory, f.receipt, f.blueprint)).not.toThrow();
  for (const lod of [0, 1, 2]) {
    const receipt = structuredClone(f.receipt), row = receipt.bindings[0].renderDataAudit.lods[lod];
    row.tangentBasis.axes.x.nearZero = 1; bindAudit(receipt.bindings[0]);
    expect(() => requireNativeCitadelImport(f.directory, receipt, f.blueprint)).toThrow(/render tangent basis/);
  }
});

test('missing, degenerate or weakened tangent basis diagnostics fail without admitting content', () => {
  const f = fixture();
  const changes: ((basis: any) => void)[] = [
    b => { b.version = 2; }, b => { b.diagnosticOnly = false; }, b => { b.highPrecision = false; },
    b => { b.basisSource = 'source_mesh_description'; }, b => { b.nearZeroComponentTolerance = .0001; },
    b => { b.orthogonalityAbsoluteNormalizedDotTolerance = .1; }, b => { b.sampleComponentPolicy = 'omit_bad_values'; },
    b => { b.badVertexSampleLimit = 1024; }, b => { b.badVertexSamplesTruncated = true; },
    b => { b.badVertexSamples = [{ index: 0 }]; }, b => { b.invalidVertices = 1; }, b => { b.orthogonalVertices = 2; },
    b => { delete b.axes.y; }, b => { b.axes.x.finite = 2; }, b => { b.axes.x.unit = 2; },
    ...['nonFinite', 'nearZero', 'nonUnit'].map(key => (b: any) => { b.axes.z[key] = 1; }),
    b => { b.axes.y.unitSquaredTolerance = .04; }, b => { b.axes.x.minimumLength = 0; }, b => { b.axes.y.maximumLength = 2; },
    b => { delete b.pairs.yz; }, b => { b.pairs.xz.evaluated = 2; }, b => { b.pairs.xz.orthogonal = 2; },
    b => { b.pairs.xy.skipped = 1; }, b => { b.pairs.xz.nonOrthogonal = 1; },
    b => { b.pairs.xz.maximumAbsoluteNormalizedDot = .5; }, b => { b.pairs.xy.maximumAbsoluteNormalizedDot = -1; },
  ];
  for (const change of changes) {
    const receipt = structuredClone(f.receipt), binding = receipt.bindings[0];
    change(binding.renderDataAudit.lods[0].tangentBasis); bindAudit(binding);
    expect(() => requireNativeCitadelImport(f.directory, receipt, f.blueprint)).toThrow(/render tangent basis/);
  }
  const missing = structuredClone(f.receipt); delete missing.bindings[0].renderDataAudit.lods[0].tangentBasis;
  bindAudit(missing.bindings[0]);
  expect(() => requireNativeCitadelImport(f.directory, missing, f.blueprint)).toThrow(/render tangent basis/);
  expect(f.receipt).not.toHaveProperty('productionAdmission');
});

test('raw tangent payload, its hash and the redundant parsed audit must agree', () => {
  const f = fixture();
  const staleHash = structuredClone(f.receipt);
  staleHash.bindings[0].renderDataAuditPayload += ' ';
  expect(() => requireNativeCitadelImport(f.directory, staleHash, f.blueprint)).toThrow(/render buffers/);
  const changedParsed = structuredClone(f.receipt);
  changedParsed.bindings[0].renderDataAudit.lods[0].tangentBasis.axes.x.nonUnit = 1;
  expect(() => requireNativeCitadelImport(f.directory, changedParsed, f.blueprint)).toThrow(/render-buffer audit/);
  const changedRaw = structuredClone(f.receipt), raw = structuredClone(changedRaw.bindings[0].renderDataAudit);
  raw.lods[0].tangentBasis.pairs.xz.nonOrthogonal = 1;
  changedRaw.bindings[0].renderDataAuditPayload = JSON.stringify(raw);
  changedRaw.bindings[0].renderDataAuditSha256 = createHash('sha256').update(changedRaw.bindings[0].renderDataAuditPayload).digest('hex');
  expect(() => requireNativeCitadelImport(f.directory, changedRaw, f.blueprint)).toThrow(/render-buffer audit/);
});
