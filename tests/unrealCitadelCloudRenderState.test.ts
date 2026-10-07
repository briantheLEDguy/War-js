import { expect, test } from 'vitest';
import { citadelCloudRenderState } from '../scripts/unreal/citadel-cloud-render-state';

const map = '/Game/WorldRebuild/AegisCitadel_0123456789ab/LightingStudy';
const report = () => ({ viewPerformance: [{ id: 'hero', lightingWitness: {
  schemaVersion: 1, available: true, map, viewportAvailable: true, showCloud: true,
  clouds: [{ visible: true, hiddenInGame: false, actorHidden: false, registered: true,
    renderStateCreated: true, renderInMainPass: true, holdout: false, volumeDomain: true,
    renderMaterial: { usedFallback: false, volumeDomain: true, shaderMapPresent: true,
      shaderMapValidForRendering: true } }],
} }] });

test('a captured frame and UObject volume domain cannot conceal the actual fallback render material', () => {
  const value = report();
  value.viewPerformance[0].lightingWitness.clouds[0].renderMaterial = {
    usedFallback: true, volumeDomain: false, shaderMapPresent: true, shaderMapValidForRendering: true,
  };
  const result = citadelCloudRenderState(value, map, ['hero']);
  expect(result.available).toBe(false);
  expect(result.failures).toHaveLength(1);
});

test('valid native resources confer no visible-cloud, lighting or visual approval', () => {
  expect(citadelCloudRenderState(report(), map, ['hero'])).toMatchObject({ available: true,
    diagnosticOnly: true, visibleCloudPixelsVerified: false, lightingApproved: false, visualApproved: false });
});

test('missing, duplicate, foreign-map and hidden-component witnesses remain unavailable', () => {
  for (const mutate of [
    (r: any) => { delete r.viewPerformance[0].lightingWitness; },
    (r: any) => { r.viewPerformance.push(structuredClone(r.viewPerformance[0])); },
    (r: any) => { r.viewPerformance[0].lightingWitness.map = '/Game/AnotherMap'; },
    (r: any) => { r.viewPerformance[0].lightingWitness.clouds = []; },
    (r: any) => { r.viewPerformance[0].lightingWitness.clouds[0].actorHidden = true; },
    (r: any) => { r.viewPerformance[0].lightingWitness.clouds[0].renderMaterial.shaderMapValidForRendering = false; },
  ]) {
    const value = report(); mutate(value);
    expect(citadelCloudRenderState(value, map, ['hero']).available).toBe(false);
  }
  expect(citadelCloudRenderState(report(), map, ['hero', 'front']).available).toBe(false);
  expect(citadelCloudRenderState({}, map, []).available).toBe(false);
});
