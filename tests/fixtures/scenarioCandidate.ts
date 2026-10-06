import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { citadelCandidateImportFixture } from './citadelCandidateImport';
import { citadelLightingFixture } from './citadelLighting';
import { citadelTerrainFixture } from './citadelTerrain';

/** Synthetic package/source/DLL bytes exercise guards only; they cannot run Unreal or mint native acceptance. */
export function scenarioCandidateFixture(root: string) {
  const revision = '0123456789ab', signature = revision + 'a'.repeat(52);
  const prefix = `/Game/WorldRebuild/AegisCitadel_${revision}`, map = `${prefix}/SiegeCandidate`;
  const directory = path.join(root, 'artifacts/unreal/aegis-citadel', revision);
  mkdirSync(directory, { recursive: true });
  const hash = (bytes: string) => createHash('sha256').update(bytes).digest('hex');
  const save = (file: string, bytes: string) => { mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, bytes); return hash(bytes); };
  const hashes: Record<string, string> = {};
  for (const name of [map, `${prefix}/City`, `${prefix}/Layers/GothicCitadel`, '/Game/OriginalCampaign', '/Game/ModelDependency'])
    hashes[name] = save(path.join(root, 'unreal/AegisWar/Content', name.slice(6)) + '.umap', 'Portable test package only: ' + name);
  const lighting = citadelLightingFixture(root, revision);
  const terrain = citadelTerrainFixture(root, revision, lighting.sourceHashes);
  lighting.outsideMaskPreservation.forEach((row: any) => { row.explicitTerrainCarves = row.source.endsWith('/authored') ? ['occupied_commander_hall'] : []; });
  Object.assign(hashes, lighting.packageHashes);
  const imported = citadelCandidateImportFixture(root, revision, signature);
  const sceneryLevels = [...new Set([`${prefix}/Layers/GothicCitadel`, ...lighting.sceneryLevels])], origin = [0, 0, 0];
  const dependencyHashes = { '/Game/ModelDependency': hashes['/Game/ModelDependency'] };
  const revisionPayload = JSON.stringify({ scenery: Object.fromEntries(sceneryLevels.map(name => [name, hashes[name]])), dependencies: dependencyHashes, origin });
  const cityRevision = hash(revisionPayload);
  const stageRecipeSha256 = save(path.join(root, 'scripts/unreal/stage-aegis-citadel.py'), 'fixture stage recipe');
  const stageDependencySha256 = { 'citadel_stage_contract.py': save(path.join(root, 'scripts/unreal/citadel_stage_contract.py'), 'fixture stage dependency'), ...terrain.stageDependencySha256 };
  const receipt = { schemaVersion: 1, revision, signature, geometrySignature: imported.geometrySignature, published: false, nativeImported: true,
    nativeImportConvention: imported.nativeImportConvention, bindings: imported.bindings, proofStart: imported.proofStart, materialBindings: imported.materialBindings,
    stageRecipeSha256, stageDependencySha256, sharedLightingChanges: lighting.sharedLightingChanges, nativeCloudPlacement: lighting.nativeCloudPlacement,
    terrainCarves: terrain.terrainCarves, outsideMaskPreservation: lighting.outsideMaskPreservation, exposureUsesExtendedEV100: false, exposureUnits: 'native_luminance',
    siegeMap: map, sourceHashes: { '/Game/OriginalCampaign': hashes['/Game/OriginalCampaign'], ...lighting.sourceHashes, ...terrain.sourceHashes },
    packageHashes: { [map]: hashes[map], [`${prefix}/City`]: hashes[`${prefix}/City`], [`${prefix}/Layers/GothicCitadel`]: hashes[`${prefix}/Layers/GothicCitadel`],
      ...imported.packageHashes, ...lighting.packageHashes, ...terrain.packageHashes },
    city: { definition: `${prefix}/City`, revision: cityRevision, revisionPayload, origin, sceneryLevels, dependencyHashes,
      packageHashes: { [`${prefix}/City`]: hashes[`${prefix}/City`], [`${prefix}/Layers/GothicCitadel`]: hashes[`${prefix}/Layers/GothicCitadel`], ...lighting.packageHashes } }, sceneryLevels };
  save(path.join(directory, 'blueprint.json'), JSON.stringify({ revision, signature, teamSpawns: imported.teamSpawns,
    lightingTreatment: lighting.lightingTreatment, terrainCarves: terrain.planTerrainCarves, sourceRecipes: terrain.sourceRecipes, baseline: terrain.baseline }));
  save(path.join(directory, 'candidate.json'), JSON.stringify(receipt));
  for (const name of ['Private/WarScenarioInstance.cpp', 'Private/WarScenarioMenuProof.cpp', 'Public/WarScenarioInstance.h', 'AegisWar.Build.cs'])
    save(path.join(root, 'unreal/AegisWar/Source/AegisWar', name), 'Portable native source fixture only: ' + name);
  const binary = path.join(root, 'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll'); save(binary, 'Portable DLL bytes cannot execute');
  const project = path.join(root, 'unreal/AegisWar/AegisWar.uproject'); save(project, 'Portable project fixture only');
  return { map, directory, cityRevision, engineRoot: lighting.engineRoot, binary, project };
}
