import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { expect, test } from 'vitest';
import { requireNativeCitadelTerrain } from '../scripts/unreal/citadel-terrain-evidence';
import { citadelLightingFixture } from './fixtures/citadelLighting';
import { citadelTerrainFixture } from './fixtures/citadelTerrain';

test('terrain evidence reproduces every clipped face and preserves only the exact named component exception', () => {
  const repository = mkdtempSync(path.join(os.tmpdir(), 'citadel-terrain-evidence-'));
  try {
    const revision = '0123456789ab', lighting = citadelLightingFixture(repository, revision);
    const terrain = citadelTerrainFixture(repository, revision, lighting.sourceHashes);
    lighting.outsideMaskPreservation.forEach((row: any) => { row.explicitTerrainCarves = row.source.endsWith('/authored') ? ['occupied_commander_hall'] : []; });
    const run = path.join(repository, 'artifacts/unreal/aegis-citadel', revision);
    expect(readFileSync(path.join(run, 'terrain-carves/mountain-source.json'), 'utf8')).toContain('\r\n');
    const plan = { terrainCarves: terrain.planTerrainCarves, sourceRecipes: terrain.sourceRecipes, baseline: terrain.baseline };
    const city: any = { revision, ...lighting, terrainCarves: terrain.terrainCarves,
      stageDependencySha256: terrain.stageDependencySha256,
      sourceHashes: { ...lighting.sourceHashes, ...terrain.sourceHashes },
      packageHashes: { ...lighting.packageHashes, ...terrain.packageHashes } };
    function write(p = plan, c = city) {
      writeFileSync(path.join(run, 'blueprint.json'), JSON.stringify(p));
      writeFileSync(path.join(run, 'candidate.json'), JSON.stringify(c));
    }
    write(); expect(() => requireNativeCitadelTerrain(repository, run)).not.toThrow();
    for (const mutate of [
      (p: any) => { delete p.terrainCarves[0].sourceNativePolicy; },
      (p: any) => { delete p.terrainCarves[0].sourcePolicySurvey; },
      (p: any) => { p.terrainCarves[0].sourcePolicySurvey.path = p.baseline.file; },
      (p: any) => { p.terrainCarves[0].sourcePolicySurvey.sha256 = 'f'.repeat(64); },
      (p: any) => { p.baseline.terrainSourcePolicies[city.terrainCarves[0].sourceMesh].sourceMeshSha256 = 'f'.repeat(64); },
    ]) {
      const changed = structuredClone(plan); mutate(changed); write(changed);
      expect(() => requireNativeCitadelTerrain(repository, run)).toThrow();
    }
    write();
    for (const mutate of [
      (c: any) => { c.terrainCarves = []; },
      (c: any) => { c.terrainCarves[0].nativeSourcePrefixPreserved = false; },
      (c: any) => { delete c.terrainCarves[0].nativeReadback; },
      (c: any) => { c.terrainCarves[0].nativeReadback.comparison.unusedStoredCorners++; },
      (c: any) => { c.terrainCarves[0].nativeReadback.actualPolicy.sourceLods++; },
      (c: any) => { c.terrainCarves[0].nativeReadback.sourcePolicy.mesh.changedCollision = true; c.terrainCarves[0].nativeReadback.actualPolicy.mesh.changedCollision = true; },
      (c: any) => { c.terrainCarves[0].nativeReadback.storedCorners.sha256 = 'f'.repeat(64); },
      (c: any) => { delete c.terrainCarves[0].nativeReadback.originalStoredCorners; },
      (c: any) => { delete c.terrainCarves[0].nativeReadback.originalRenderedFaces; },
      (c: any) => { c.terrainCarves[0].nativeReadback.renderedComparison.computedBasisExcludedSourceTriangleIds.push(0); },
      (c: any) => { c.stageDependencySha256 = {}; },
      (c: any) => { c.terrainCarves[0].worldVolumes[0].bounds[1][0] += 100; },
      (c: any) => { c.terrainCarves[0].actorTransform.translationCm[0] += 1; },
      (c: any) => { c.terrainCarves[0].actualActorState.transform[0] += 1; },
      (c: any) => { c.terrainCarves[0].actualActorState.components[0].visible = false; },
      (c: any) => { c.terrainCarves[0].sourceExport.path = '../mountain-source.json'; },
      (c: any) => { c.terrainCarves[0].clippedDocument.sha256 = 'f'.repeat(64); },
      (c: any) => { c.terrainCarves[0].mesh = '/Game/Other.Other'; },
      (c: any) => { c.terrainCarves[0].mesh = `/Game/WorldRebuild/AegisCitadel_${revision}/SM_HallCarvedMountain.SM_HallCarvedMountain`; },
      (c: any) => { c.outsideMaskPreservation[1].explicitTerrainCarves = ['occupied_commander_hall']; },
    ]) {
      const changed = structuredClone(city); mutate(changed); write(plan, changed);
      expect(() => requireNativeCitadelTerrain(repository, run)).toThrow();
    }
    const clipPath = path.join(run, 'terrain-carves/hall-carve.json'), original = readFileSync(clipPath, 'utf8');
    for (const mutate of [
      (d: any) => { d.data.positions[0][0] += 1; },
      (d: any) => { d.data.normals[0] = [0, 1, 0]; },
      (d: any) => { d.data.uvs[0][0] += .1; },
      (d: any) => { d.data.indices.push(0, 1, 2); d.data.triangleMaterials.push(0); },
      (d: any) => { d.carveReceipt.touchedSourceTriangles = []; },
      (d: any) => { d.carveReceipt.outsidePreservation.sourceTriangleIds = []; },
      (d: any) => { d.sourceExportPayload = '{}'; },
    ]) {
      const d = JSON.parse(original); mutate(d); const text = JSON.stringify(d), changed = structuredClone(city);
      writeFileSync(clipPath, text);
      changed.terrainCarves[0].clippedDocument.sha256 = createHash('sha256').update(text).digest('hex');
      changed.terrainCarves[0].outsidePreservation = d.carveReceipt.outsidePreservation;
      write(plan, changed);
      expect(() => requireNativeCitadelTerrain(repository, run)).toThrow(/topology\/attributes/);
    }
    writeFileSync(clipPath, original); write();
    expect(() => requireNativeCitadelTerrain(repository, run)).not.toThrow();
    for (const [key, mutate] of [
      ['storedCorners', (data: any) => { data.data.positions[0][0] += 1; }],
      ['storedCorners', (data: any) => { data.data.normals.at(-1)[0] += .1; }],
      ['referencedSource', (data: any) => { data.cornerVertexInstanceIds[0]++; }],
      ['renderDataAudit', (data: any) => { data.lods[0].invalidUVs = 1; }],
      ['renderDataAudit', (data: any) => { data.lods[0].indices -= 3; }],
      ['originalStoredCorners', (data: any) => { data.topology.vertices[0].position[0]++; }],
      ['originalRenderedFaces', (data: any) => { data.triangles[0].positions[0][0]++; }],
      ['renderedFaces', (data: any) => { data.triangles[0].uvChannels[0][0][0] += .2; }],
      ['renderedFaces', (data: any) => { data.triangles[0].uvChannels[1][0][0] = 2; }],
      ['renderedFaces', (data: any) => { data.triangles[0].normals = [[0, 1, 0], [0, 1, 0], [0, 1, 0]];
        data.triangles[0].binormals = [[0, 0, -1], [0, 0, -1], [0, 0, -1]]; }],
      ['renderedFaces', (data: any) => { data.triangles.at(-1).positions[0][0]++; }],
    ] as const) {
      const binding = city.terrainCarves[0].nativeReadback[key], file = path.join(run, binding.path), before = readFileSync(file, 'utf8');
      const data = JSON.parse(before); mutate(data); const text = JSON.stringify(data), changed = structuredClone(city);
      writeFileSync(file, text); changed.terrainCarves[0].nativeReadback[key].sha256 = createHash('sha256').update(text).digest('hex');
      write(plan, changed); expect(() => requireNativeCitadelTerrain(repository, run)).toThrow();
      writeFileSync(file, before);
    }
    write(); expect(() => requireNativeCitadelTerrain(repository, run)).not.toThrow();
  } finally { rmSync(repository, { recursive: true, force: true }); }
}, 15_000);
