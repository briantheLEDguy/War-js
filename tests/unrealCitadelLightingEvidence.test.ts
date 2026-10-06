import { expect, test } from 'vitest';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import { requireNativeCitadelLighting } from '../scripts/unreal/citadel-lighting-evidence';
import { citadelLightingFixture } from './fixtures/citadelLighting';
import { requireNativePackageHash } from '../scripts/unreal/native-package-evidence';

test('historical five-fixture receipts remain inspectable but cannot satisfy fresh version2 acceptance', () => {
  const root = mkdtempSync(path.join(os.tmpdir(), 'citadel-lighting-'));
  try {
    const revision = '0123456789ab', fixture = citadelLightingFixture(root, revision, 1);
    const receipt: any = { revision, ...fixture }, blueprint: any = { lightingTreatment: fixture.lightingTreatment };
    expect(() => requireNativeCitadelLighting(receipt, blueprint)).toThrow(/version2/);
    expect(() => requireNativeCitadelLighting(receipt, blueprint, { historical: true })).not.toThrow();
    for (const mutate of [
      (r: any) => { r.sharedLightingChanges[0].sourceStateHash = 'f'.repeat(64); },
      (r: any) => { r.sharedLightingChanges[0].requestedProperties.arbitrary_actor_property = true; },
      (r: any) => { r.sharedLightingChanges[0].actualPropertyReadback.intensity = 1; },
      (r: any) => { r.sharedLightingChanges[1].actualPropertyReadback.light_color = [226, 187, 158, 255]; },
      (r: any) => { r.sharedLightingChanges[2].actualPropertyReadback.light_color = [247, 228, 215, 255]; },
      (r: any) => { r.sharedLightingChanges[0].actualPropertyReadback.rotationDegrees[0] = null; },
      (r: any) => { r.sharedLightingChanges.push({ ...r.sharedLightingChanges[0], actor: 'RetainedStreetLight' }); },
      (r: any) => { r.outsideMaskPreservation[0].explicitLightingChanges.push('RetainedStreetLight'); },
      (r: any) => { r.sceneryLevels = []; },
      (r: any) => { r.exposureUsesExtendedEV100 = true; },
      (r: any) => { r.exposureUnits = 'EV100'; },
    ]) { const changed = structuredClone(receipt); mutate(changed);
      expect(() => requireNativeCitadelLighting(changed, blueprint, { historical: true })).toThrow(); }
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test('fresh lighting binds seven package-scoped identities, exact named-channel readbacks and one owned cloud', () => {
  const root = mkdtempSync(path.join(os.tmpdir(), 'citadel-lighting2-'));
  try {
    const fixture = citadelLightingFixture(root, '0123456789ab');
    const receipt: any = { revision: '0123456789ab', ...fixture }, blueprint: any = { lightingTreatment: fixture.lightingTreatment };
    expect(receipt.sharedLightingChanges.filter((c: any) => c.actor === 'DirectionalLight_0')).toHaveLength(2);
    expect(() => requireNativeCitadelLighting(receipt, blueprint)).not.toThrow();
    for (const mutate of [
      (r: any) => { r.sharedLightingChanges[6].sourcePackage = r.sharedLightingChanges[0].sourcePackage; },
      (r: any) => { r.sharedLightingChanges[6].id = 'sun'; },
      (r: any) => { r.sharedLightingChanges[0].actualTags = ['WarCapitalWorkbench']; },
      (r: any) => { r.sharedLightingChanges[0].klass = 'SkyLight'; },
      (r: any) => { r.sharedLightingChanges[0].label = 'Another light'; },
      (r: any) => { r.sharedLightingChanges[0].sourcePackageSha256 = 'f'.repeat(64); },
      (r: any) => { r.sharedLightingChanges[6].actualPropertyReadback.light_color = [218, 192, 173, 255]; },
      (r: any) => { r.sharedLightingChanges[5].actualPropertyReadback.rayleigh_scattering_scale = .175866; },
      (r: any) => { r.sharedLightingChanges[0].actualPropertyReadback.atmosphere_sun_light_index = 0; },
      (r: any) => { r.outsideMaskPreservation[0].explicitLightingChanges[0] = 'DirectionalLight_0'; },
      (r: any) => { r.outsideMaskPreservation[0].explicitLightingChanges.push('RetainedStreetLight'); },
      (r: any) => { r.nativeCloudPlacement.package = r.sharedLightingChanges[0].package; },
      (r: any) => { r.nativeCloudPlacement.actualMaterial = '/Engine/OtherCloud.OtherCloud'; },
      (r: any) => { r.nativeCloudPlacement.actualMaterial = r.nativeCloudPlacement.material.path; },
      (r: any) => { r.nativeCloudPlacement.materialInstance.sha256 = 'f'.repeat(64); },
      (r: any) => { r.nativeCloudPlacement.materialInstance.package = '/Engine/EngineSky/MI_Cloud'; },
      (r: any) => { r.nativeCloudPlacement.materialInstance.parent = '/Engine/Other.Other'; },
      (r: any) => { r.nativeCloudPlacement.materialInstance.actualScalarReadback.Cloud_GlobalDensity = .08; },
      (r: any) => { r.nativeCloudPlacement.materialInstance.actualVectorReadback.Cloud_AlbedoColor = [.78, .7, .65, .5]; },
      (r: any) => { r.nativeCloudPlacement.materialInstance.actualVectorReadback.Storm_LightningColor = [0, 0, 0, null]; },
      (r: any) => { r.nativeCloudPlacement.materialInstance.actualScalarReadback.Coverage = .25; },
      (r: any) => { r.nativeCloudPlacement.materialInstance.registeredScalarParameters = ['Layout_CloudGlobalScale']; },
      (r: any) => { r.nativeCloudPlacement.materialInstance.registeredVectorParameters.push('Cloud_AlbedoColor'); },
      (r: any) => { r.nativeCloudPlacement.materialInstance.setterSucceeded = true; },
      (r: any) => { delete r.nativeCloudPlacement.materialInstance; },
      (r: any) => { r.nativeCloudPlacement.actualPropertyReadback.layer_height = 2; },
      (r: any) => { r.nativeCloudPlacement.actualPropertyReadback.view_sample_count_scale = 1; },
      (r: any) => { delete r.nativeCloudPlacement.actualPropertyReadback.shadow_view_sample_count_scale; },
      (r: any) => { r.nativeCloudPlacement.materialInstance.actualVectorReadback.Layout_CloudTypeMask = [0, 1, 0, 0]; },
      (r: any) => { r.nativeCloudPlacement.actualPropertyReadback.extra_property = true; },
      (r: any) => { r.nativeCloudPlacement.actualPointCm = [1, 0, 0]; },
      (r: any) => { r.nativeCloudPlacement.actualTags = []; },
      (r: any) => { delete r.nativeCloudPlacement; },
      (r: any) => { r.sourceHashes[r.nativeCloudPlacement.material.package] = 'f'.repeat(64); },
    ]) {
      const changed = structuredClone(receipt); mutate(changed);
      expect(() => requireNativeCitadelLighting(changed, blueprint)).toThrow();
    }
    for (const mutate of [
      (b: any) => { b.lightingTreatment.fixtures[5].properties.mie_scattering_scale = 0; },
      (b: any) => { b.lightingTreatment.fixtures[1].properties.intensity = 2500; },
      (b: any) => { b.lightingTreatment.fixtures[4].properties.dynamic_global_illumination_method.value = 'LUMEN'; },
      (b: any) => { b.lightingTreatment.existingAtmospherePreserved = true; },
      (b: any) => { b.lightingTreatment.cloudFixture.material.path = '/Engine/OtherCloud.OtherCloud'; },
      (b: any) => { b.lightingTreatment.cloudFixture.materialInstance.scalarParameters.Cloud_GlobalCoverage = -.2; },
      (b: any) => { b.lightingTreatment.cloudFixture.materialInstance.vectorParameters.Layout_CloudTypeMask = [1, 0, 0, 0]; },
      (b: any) => { b.lightingTreatment.cloudFixture.properties = { layer_bottom_altitude: .35, layer_height: .65 }; },
      (b: any) => { b.lightingTreatment.fixtures[0].rotationDegrees = [-28, 30, 0]; },
      (b: any) => { b.lightingTreatment.fixtures[2].properties.intensity = 1.4; },
    ]) { const changed = structuredClone(blueprint); mutate(changed);
      expect(() => requireNativeCitadelLighting(receipt, changed)).toThrow(); }
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test('engine source packages require explicit configured root, exact bytes and confined unambiguous paths', () => {
  const root = mkdtempSync(path.join(os.tmpdir(), 'citadel-engine-source-'));
  try {
    const engineRoot = path.join(root, 'engine'), content = path.join(engineRoot, 'Engine/Content');
    const file = path.join(content, 'EngineSky/Test.uasset'), bytes = 'PORTABLE ENGINE FILE ONLY';
    mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, bytes);
    const hash = createHash('sha256').update(bytes).digest('hex');
    expect(() => requireNativePackageHash(root, '/Engine/EngineSky/Test', hash, engineRoot)).not.toThrow();
    for (const name of ['/Engine/../Test', '/Engine/EngineSky//Test', '/Engine/EngineSky/Test.Test', '/Engine/EngineSky\\Test'])
      expect(() => requireNativePackageHash(root, name, hash, engineRoot)).toThrow(/identity/);
    expect(() => requireNativePackageHash(root, '/Engine/EngineSky/Test', 'f'.repeat(64), engineRoot)).toThrow(/dependency changed/);
    expect(() => requireNativePackageHash(root, '/Engine/EngineSky/Test', hash, path.join(root, 'missing'))).toThrow();
    writeFileSync(path.join(content, 'EngineSky/Test.umap'), bytes);
    expect(() => requireNativePackageHash(root, '/Engine/EngineSky/Test', hash, engineRoot)).toThrow(/ambiguous/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});
