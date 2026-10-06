import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { CITADEL_CLOUD_SCALARS, CITADEL_CLOUD_VECTORS } from '../../scripts/unreal/citadel-lighting-evidence';

/** Pure recipe data and explicitly unusable package bytes; no Editor observation is represented. */
export function citadelLightingFixture(repository: string, revision: string, version: 1 | 2 = 2) {
  const hash = (bytes: string) => createHash('sha256').update(bytes).digest('hex');
  const run = spawnSync('python', ['-B', '-c',
    'import sys,json;sys.path.insert(0,"scripts/unreal");from aegis_citadel_blueprint import LIGHTING_FIXTURES_V1;from aegis_citadel_lighting import reference_fixture_requests,FIXTURES;print(json.dumps(dict(legacy=LIGHTING_FIXTURES_V1,requests=reference_fixture_requests(LIGHTING_FIXTURES_V1),identities=FIXTURES)))'],
  { encoding: 'utf8', windowsHide: true });
  if (run.error || run.status !== 0) throw new Error(run.error?.message ?? run.stderr);
  const parsed = JSON.parse(run.stdout);
  const original = '/Game/PortableLightingSource', copied = `/Game/WorldRebuild/AegisCitadel_${revision}/Layers/RetainedCity_99`;
  const packageHashes: Record<string, string> = {}, sourceHashes: Record<string, string> = {};
  for (const [name, bytes, hashes] of [[original, 'PORTABLE ORIGINAL LIGHTING ONLY', sourceHashes],
    [copied, 'PORTABLE COPIED LIGHTING ONLY', packageHashes]] as const) {
    const file = path.join(repository, 'unreal/AegisWar/Content', name.slice(6)) + '.umap';
    mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, bytes); hashes[name] = hash(bytes);
  }
  const specs: any[] = parsed.legacy.map((s: any) => ({ ...s, package: original, sourceStateHash: hash('portable source ' + s.actor) }));
  const sharedLightingChanges = specs.map(s => ({ actor: s.actor, package: copied, sourcePackage: original,
    sourceStateHash: s.sourceStateHash, actualStateHash: hash('portable changed ' + s.actor), requestedProperties: s.properties,
    actualPropertyReadback: { ...Object.fromEntries(Object.entries(s.properties).map(([key, value]: [string, any]) =>
      [key, typeof value === 'object' ? value.kind === 'enum' ? value.type + '.' + value.value : value.value : value])),
    ...(s.rotationDegrees ? { rotationDegrees: s.rotationDegrees } : {}) } }));
  const legacy = { lightingTreatment: { schemaVersion: 1, fixtures: specs, exposureUnits: 'native_luminance', expectedExtendedEV100: false },
    sharedLightingChanges, exposureUsesExtendedEV100: false, exposureUnits: 'native_luminance',
    outsideMaskPreservation: [{ source: original, candidate: copied, matchesExpected: true, preservedActorCount: 5,
      preservedStateSha256: hash('portable preservation'), explicitLightingChanges: specs.map(s => s.actor) }],
    sourceHashes, packageHashes, sceneryLevels: [copied] };
  if (version === 1) return { ...legacy, nativeCloudPlacement: undefined, engineRoot: undefined };
  const sourcePrefix = '/Game/WorldRebuild/DutchBastion_d105951f4aab/Layers/';
  const candidatePrefix = `/Game/WorldRebuild/AegisCitadel_${revision}/Layers/`;
  const source2: Record<string, string> = {}, owned2: Record<string, string> = {};
  const engineRoot = path.join(repository, '.portable-engine');
  const materialPackage = '/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst';
  function fixturePackage(name: string, hashes: Record<string, string>) {
    const file = name.startsWith('/Engine/') ? path.join(engineRoot, 'Engine/Content', name.slice(8)) + '.uasset'
      : path.join(repository, 'unreal/AegisWar/Content', name.slice(6)) + (name.includes('/Materials/') ? '.uasset' : '.umap');
    const bytes = 'PORTABLE LIGHTING UNIT FIXTURE ONLY: ' + name;
    mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, bytes); hashes[name] = hash(bytes);
  }
  for (const name of [sourcePrefix + 'authored', sourcePrefix + 'Bastion_Dutch_Geometry', materialPackage]) fixturePackage(name, source2);
  for (const name of [candidatePrefix + 'RetainedCity_0', candidatePrefix + 'RetainedCity_1', candidatePrefix + 'GothicCitadel']) fixturePackage(name, owned2);
  const byId = Object.fromEntries(parsed.requests.map((r: any) => [r.id, r]));
  byId.sun.rotationDegrees = [-20, 30, 0];
  byId.ambient_sky.properties.intensity = .35;
  const specs2: any[] = parsed.identities.map(([id, actor, klass, label, component, layer, requiredTag]: any[]) => ({
    id, actor, klass, label, component, requiredTag, package: sourcePrefix + layer,
    sourceStateHash: hash('portable source state ' + id), sourcePackageSha256: source2[sourcePrefix + layer],
    ...byId[id],
  }));
  const changes2 = specs2.map(s => ({ id: s.id, actor: s.actor, klass: s.klass, label: s.label,
    component: s.component, requiredTag: s.requiredTag, sourcePackage: s.package,
    package: candidatePrefix + (s.id === 'dutch_street_fill' ? 'RetainedCity_1' : 'RetainedCity_0'),
    sourceStateHash: s.sourceStateHash, sourcePackageSha256: s.sourcePackageSha256,
    actualStateHash: hash('portable changed state ' + s.id),
    actualTags: [s.requiredTag, ...(['sun', 'ambient_sky', 'exposure', 'atmosphere'].includes(s.id) ? ['WarCapitalWorkbench']
      : s.id === 'dutch_street_fill' ? ['WarDutchBastion'] : [])], requestedProperties: s.properties,
    actualPropertyReadback: { ...Object.fromEntries(Object.entries(s.properties).map(([key, value]: [string, any]) =>
      [key, typeof value === 'object' ? value.kind === 'enum' ? value.type + '.' + value.value : value.value : value])),
      ...(s.rotationDegrees ? { rotationDegrees: s.rotationDegrees } : {}) },
  }));
  const cloud = { id: 'citadel_cloud', actor: 'VolumetricCloud_0', klass: 'VolumetricCloud',
    label: 'Bastion mountain cloud canopy', component: 'VolumetricCloudComponent',
    requiredTag: 'WarWorldObject_aegis_citadel_cloud', pointCm: [0, 0, 0],
    material: { package: materialPackage, path: materialPackage + '.m_SimpleVolumetricCloud_Inst', sha256: source2[materialPackage] },
    properties: { layer_bottom_altitude: .5, layer_height: 1.2,
      view_sample_count_scale: 2, shadow_view_sample_count_scale: 2 },
    materialInstance: { name: 'MI_Cloud', parent: materialPackage + '.m_SimpleVolumetricCloud_Inst',
      scalarParameters: structuredClone(CITADEL_CLOUD_SCALARS), vectorParameters: structuredClone(CITADEL_CLOUD_VECTORS) } };
  const instancePackage = `/Game/WorldRebuild/AegisCitadel_${revision}/Materials/MI_Cloud`;
  fixturePackage(instancePackage, owned2);
  const instance = { package: instancePackage, path: instancePackage + '.MI_Cloud', sha256: owned2[instancePackage],
    parent: cloud.material.path, requestedScalarParameters: structuredClone(CITADEL_CLOUD_SCALARS),
    actualScalarReadback: structuredClone(CITADEL_CLOUD_SCALARS), requestedVectorParameters: structuredClone(CITADEL_CLOUD_VECTORS),
    actualVectorReadback: structuredClone(CITADEL_CLOUD_VECTORS), registeredScalarParameters: Object.keys(CITADEL_CLOUD_SCALARS),
    registeredVectorParameters: Object.keys(CITADEL_CLOUD_VECTORS) };
  const nativeCloudPlacement = { ...cloud, package: candidatePrefix + 'GothicCitadel', actualTags: ['WarAegisCitadel', cloud.requiredTag],
    actualPointCm: cloud.pointCm, actualMaterial: instance.path, requestedProperties: cloud.properties,
    actualPropertyReadback: cloud.properties, stateHash: hash('portable owned cloud state'), materialInstance: instance };
  return { lightingTreatment: { schemaVersion: 2, fixtures: specs2, cloudFixture: cloud,
    exposureUnits: 'native_luminance', expectedExtendedEV100: false, existingAtmospherePreserved: false },
    sharedLightingChanges: changes2, nativeCloudPlacement, engineRoot,
    exposureUsesExtendedEV100: false, exposureUnits: 'native_luminance', sourceHashes: source2, packageHashes: owned2,
    sceneryLevels: Object.keys(owned2).filter(name => name.includes('/Layers/')), outsideMaskPreservation: [
      { source: sourcePrefix + 'authored', candidate: candidatePrefix + 'RetainedCity_0', matchesExpected: true,
        preservedActorCount: 6, preservedStateSha256: hash('portable authored preservation'),
        explicitLightingChanges: changes2.filter(c => c.id !== 'dutch_street_fill').map(c => c.id) },
      { source: sourcePrefix + 'Bastion_Dutch_Geometry', candidate: candidatePrefix + 'RetainedCity_1', matchesExpected: true,
        preservedActorCount: 1, preservedStateSha256: hash('portable dutch preservation'), explicitLightingChanges: ['dutch_street_fill'] },
    ] };
}
