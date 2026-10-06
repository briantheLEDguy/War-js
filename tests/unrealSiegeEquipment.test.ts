import { describe, expect, it } from 'vitest';
import { validateSiegeEquipment } from '../scripts/unreal/siege-equipment-proof';
import { candidateSiegeContentEvidence, requireSameSiegeContent } from '../scripts/unreal/siege-content-evidence';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { citadelCandidateImportFixture } from './fixtures/citadelCandidateImport';
import { citadelLightingFixture } from './fixtures/citadelLighting';
import { citadelTerrainFixture } from './fixtures/citadelTerrain';

const proof = () => ({ passed: true, checkpoints: 3, stoppedWithoutEscort: true, stoppedWithoutCrew: true, ramStrikeAdvanced: true,
  overlapRecoveredWithoutDamage: true, gateCollisionVerified: true,
  vehicles: [{ travelCm: 25000 }, { travelCm: 24300 }] });
describe('native siege equipment evidence', () => {
  it('binds isolated candidate proofs to native source and scenery dependencies', () => {
    const repository = mkdtempSync(path.join(os.tmpdir(), 'citadel-equipment-'));
    try {
      const revision = 'abcdef123456';
      const map = `/Game/WorldRebuild/AegisCitadel_${revision}/SiegeCandidate`;
      const directory = path.join(repository, 'artifacts/unreal/aegis-citadel', revision);
      const native = path.join(repository, 'unreal/AegisWar/Content/WorldRebuild', `AegisCitadel_${revision}`);
      mkdirSync(directory, { recursive: true }); mkdirSync(native, { recursive: true });
      const scripts = path.join(repository, 'scripts/unreal'); mkdirSync(scripts, { recursive: true });
      writeFileSync(path.join(scripts, 'stage-aegis-citadel.py'), 'fixture stage recipe');
      writeFileSync(path.join(scripts, 'citadel_stage_contract.py'), 'fixture stage dependency');
      const hash = (value: string) => createHash('sha256').update(value).digest('hex');
      writeFileSync(path.join(native, 'SiegeCandidate.umap'), 'candidate');
      writeFileSync(path.join(native, 'Source.umap'), 'source');
      writeFileSync(path.join(native, 'City.uasset'), 'definition');
      writeFileSync(path.join(native, 'Model.uasset'), 'model');
      const source = `/Game/WorldRebuild/AegisCitadel_${revision}/Source`;
      const definition = `/Game/WorldRebuild/AegisCitadel_${revision}/City`;
      const dependencies = { [`/Game/WorldRebuild/AegisCitadel_${revision}/Model`]: hash('model') };
      const lighting = citadelLightingFixture(repository, revision), sceneryLevels = [source, ...lighting.sceneryLevels];
      const terrain = citadelTerrainFixture(repository, revision, lighting.sourceHashes);
      lighting.outsideMaskPreservation.forEach((row: any) => { row.explicitTerrainCarves = row.source.endsWith('/authored') ? ['occupied_commander_hall'] : []; });
      const sceneryHashes = { [source]: hash('source'), ...lighting.packageHashes };
      const revisionPayload = JSON.stringify({ scenery: Object.fromEntries(sceneryLevels.map(name =>
        [name, sceneryHashes[name as keyof typeof sceneryHashes]])), dependencies, origin: [0, 0, 0] });
      const imported = citadelCandidateImportFixture(repository, revision, 'a'.repeat(64));
      const receipt = { schemaVersion: 1, published: false, siegeMap: map, revision, signature: 'a'.repeat(64),
        nativeImported: true, geometrySignature: imported.geometrySignature, sceneryLevels,
        sharedLightingChanges: lighting.sharedLightingChanges, nativeCloudPlacement: lighting.nativeCloudPlacement, terrainCarves: terrain.terrainCarves,
        outsideMaskPreservation: lighting.outsideMaskPreservation,
        exposureUsesExtendedEV100: false, exposureUnits: 'native_luminance',
        nativeImportConvention: imported.nativeImportConvention, bindings: imported.bindings, proofStart: imported.proofStart,
        materialBindings:imported.materialBindings,
        stageRecipeSha256: hash('fixture stage recipe'), stageDependencySha256: { 'citadel_stage_contract.py': hash('fixture stage dependency'), ...terrain.stageDependencySha256 },
        city: { revision: hash(revisionPayload), revisionPayload, definition, sceneryLevels, origin: [0, 0, 0],
          packageHashes: { [definition]: hash('definition'), [source]: hash('source'), ...lighting.packageHashes }, dependencyHashes: dependencies },
        packageHashes: { [map]: hash('candidate'), [definition]: hash('definition'), ...imported.packageHashes, ...lighting.packageHashes, ...terrain.packageHashes },
        sourceHashes: { [source]: hash('source'), ...lighting.sourceHashes, ...terrain.sourceHashes } };
      writeFileSync(path.join(directory, 'candidate.json'), JSON.stringify(receipt));
      writeFileSync(path.join(directory, 'blueprint.json'), JSON.stringify({ revision, signature: receipt.signature,
        teamSpawns: imported.teamSpawns, lightingTreatment: lighting.lightingTreatment, terrainCarves: terrain.planTerrainCarves,
        sourceRecipes: terrain.sourceRecipes, baseline: terrain.baseline }));
      const evidence = () => candidateSiegeContentEvidence(repository, map, lighting.engineRoot);
      expect(evidence().mapSha256).toBe(hash('candidate'));
      const stale = structuredClone(receipt); stale.city.packageHashes[source] = hash('earlier scenery');
      writeFileSync(path.join(directory, 'candidate.json'), JSON.stringify(stale));
      expect(evidence).toThrow(/inconsistent/);
      const swapped = structuredClone(receipt);
      swapped.city.revisionPayload = JSON.stringify({ scenery: { [source]: hash('earlier scenery') }, dependencies, origin: [0, 0, 0] });
      swapped.city.revision = hash(swapped.city.revisionPayload);
      writeFileSync(path.join(directory, 'candidate.json'), JSON.stringify(swapped));
      expect(evidence).toThrow(/payload differs/);
      const conflicting = structuredClone(receipt); (conflicting.packageHashes as Record<string, string>)[source] = hash('earlier scenery');
      writeFileSync(path.join(directory, 'candidate.json'), JSON.stringify(conflicting));
      expect(evidence).toThrow(/Conflicting/);
      writeFileSync(path.join(directory, 'candidate.json'), JSON.stringify(receipt));
      writeFileSync(path.join(scripts, 'citadel_stage_contract.py'), 'independently changed staging dependency');
      expect(evidence).toThrow(/staging recipe or dependency/);
      writeFileSync(path.join(scripts, 'citadel_stage_contract.py'), 'fixture stage dependency');
      writeFileSync(path.join(native, 'Source.umap'), 'independent saved edit');
      expect(evidence).toThrow(/dependency changed/);
      expect(() => candidateSiegeContentEvidence(repository, '/Game/WorldRebuild/AegisCitadel_abcdef123456/Other')).toThrow(/exact isolated/);
    } finally { rmSync(repository, { recursive: true, force: true }); }
  });
  it('rejects a city activation or siege overlay change during a proof', () => {
    const content = { cityRevision: 'a'.repeat(64), mapSha256: 'b'.repeat(64) };
    expect(() => requireSameSiegeContent(content, { ...content })).not.toThrow();
    expect(() => requireSameSiegeContent(content, { ...content, cityRevision: 'c'.repeat(64) })).toThrow();
    expect(() => requireSameSiegeContent(content, { ...content, mapSha256: 'c'.repeat(64) })).toThrow();
    expect(() => requireSameSiegeContent({ ...content, mapSha256: '' }, { ...content, mapSha256: '' })).toThrow();
  });
  it('requires both engines to complete the route and stop when unsupported', () => {
    expect(() => validateSiegeEquipment(proof())).not.toThrow();
    for (const mutation of [{ checkpoints: 2 }, { stoppedWithoutEscort: false }, { stoppedWithoutCrew: false }, { ramStrikeAdvanced: false },
      { overlapRecoveredWithoutDamage: false }, { overlapRecoveredWithoutDamage: undefined }, { gateCollisionVerified: false }, { gateCollisionVerified: undefined },
      { vehicles: [{ travelCm: 25000 }] }, { vehicles: [{ travelCm: 25000 }, { travelCm: 50 }] }]) {
      expect(() => validateSiegeEquipment({ ...proof(), ...mutation })).toThrow();
    }
  });
  it('rejects absent and non-finite evidence', () => {
    expect(() => validateSiegeEquipment(null)).toThrow();
    expect(() => validateSiegeEquipment({ ...proof(), vehicles: [{ travelCm: NaN }, { travelCm: 25000 }] })).toThrow();
  });
});
