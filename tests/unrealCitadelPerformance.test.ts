import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';
import { PRESERVED_AEGIS_CITY, validateCitadelPerformance, validateCitadelPerformanceBaseline } from '../scripts/unreal/citadel-performance';

const sha = (s: string) => createHash('sha256').update(s).digest('hex');
test('portable publication performance checks run with the normal Unreal tooling suite', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealCitadelPerformance.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
function fixture(frameMs = 1000 / 60) {
  const cameras = Array.from({ length: 3 }, (_, stage) => ({ stage, eye: [0, 0, 3000], target: [0, 0, 0], fieldOfView: 68,
    positions: Array.from({ length: 36 }, (_, i) => [i * 300, 3000, 0]) }));
  const performance: any = { version: 1, cameras, settleSeconds: 10, minWindowSeconds: 60, settingsPath: 'C:/private/benchmark.ini',
    settingsSha256: sha('settings'), binaryPath: 'C:/private/native.dll', binarySha256: sha('binary'), sourceHashes: { 'C:/source.cpp': sha('source') },
    configHashes: { 'C:/normal.ini': sha('normal') }, blueprintPath: 'C:/blueprint.json', blueprintSha256: sha('blueprint') };
  const config: any = { map: '/Game/Private/SiegeCandidate', cityRevision: sha('city'), signature: sha('signature'), mapSha256: sha('map'), performance };
  const settings = { resolution: [1920, 1080], screenPercentage: 100, maxFps: 0, vSync: 0, frameSmoothing: false,
    engineFixedFrameRate: false, fappFixedTimeStep: false, worldTimeDilation: 1, dynamicResolutionMode: 0, rendered: true,
    rhi: 'D3D12', gameUserSettingsIni: performance.settingsPath, quality: Object.fromEntries(['ViewDistance', 'AntiAliasing', 'Shadow',
      'GlobalIllumination', 'Reflection', 'PostProcess', 'Texture', 'Effects', 'Foliage', 'Shading', 'Landscape'].map(k => [`sg.${k}Quality`, 3])) };
  const roster = Array.from({ length: 36 }, (_, i) => ({ realm: i < 18 ? 'aegis' : 'riftbound', careerId: 'sunfire_templar',
    combatLevel: 20, visualAsset: '/Game/Visuals/Fixture', equipmentSignature: sha('equipment') }));
  const rosterCanonical = roster.map(r => JSON.stringify(r)).sort().join('\n'), rosterSha256 = sha(rosterCanonical);
  const frames: any[] = [], windows: any[] = [];
  for (let stage = 0; stage < 3; stage++) {
    const count = Math.ceil(60_000 / frameMs) + 1;
    for (let i = 0; i < count; i++) frames.push({ stage, index: frames.length, elapsedSeconds: stage * 200 + 10 + i * frameMs / 1000,
      stageElapsedSeconds: 10 + i * frameMs / 1000, frameMs: i === 0 && stage > 0 ? 140_000 : frameMs, gameThreadMs: 3, renderThreadMs: 4, rhiThreadMs: 1, gpuMs: 5,
      drawCalls: 100, primitives: 1_000_000, physicalMiB: 1000, aegisEnrolled: 18, riftboundEnrolled: 18,
      alive: 35, dead: 1, respawning: 0, avatars: 36, modelReady: 36, visible: 36, projected: 36, recentlyRendered: 36, unoccluded: 36,
      streamingRequests: 0, rosterSha256, statsMode: 'normalized', benchmarkOrders: true, settled: true, eligible: true,
      settings, cameraEye: [0, 0, 3000], cameraDirection: [0, 0, -1], cameraFov: 68, cameraMatches: true,
      phase: 'active', encounterActive: true, leasePaused: false, preparing: false });
    const rows = frames.filter(f => f.stage === stage);
    windows.push({ stage, startElapsedSeconds: rows[0].elapsedSeconds, endElapsedSeconds: rows.at(-1).elapsedSeconds,
      frameCount: rows.length, settleSeconds: 10 });
  }
  const report: any = { schemaVersion: 1, passed: true, performanceOnly: true, proofOnly: true, ...config, configSha256: sha('config'),
    productionAdmission: false, steamAdmission: false, humanPlaytest: false, visualApproval: false, releaseAcceptance: false,
    referenceHardwareCertified: false, bindings: performance, settings, roster, rosterCanonical, rosterSha256, statsMode: 'normalized',
    hardware: { cpu: 'actual cpu', gpu: 'actual gpu', adapter: 'actual adapter', driverVersion: 'driver', os: 'Windows',
      engineVersion: '5.8.2-123+++UE5', physicalMemoryBytes: 32e9 }, windows, frames: { count: frames.length, sha256: sha('raw') },
    formationPositions: cameras.flatMap(c => c.positions.map((point, index) => ({ stage: c.stage, index, point, actualFloor: point,
      floorNormalZ: 1, capsuleRadiusCm: 42, capsuleHalfHeightCm: 96, floorClear: true, capsuleClear: true, navigation: true,
      captureExclusion: true, captureRadiusCm: 650, minimumCaptureDistanceCm: 1000 })) ) };
  return { config, report, raw: { schemaVersion: 1, complete: true, frames } };
}

function earnedFixture() {
  const f = fixture(), times = [110, 180, 250, 290, 460, 460, 500];
  Object.assign(f.config, { performanceBaseline: true, isolatedStageWindows: false, fixtureMode: 'earned_progression',
    cityRevision: PRESERVED_AEGIS_CITY.revision });
  Object.assign(f.report, f.config, { sourceCity: { ...PRESERVED_AEGIS_CITY }, earnedProgressionObserved: true,
    progressionAcceptance: false, victoryAcceptance: false, conquestAcceptance: false, routeAcceptance: false, fullSiegeAdmission: false });
  const observation = (stage: number, phase: string, mainClaims: number, elapsedSeconds: number, count: number) => ({
    stage, phase, mainClaims, optionalClaims: 0, elapsedSeconds, siegeElapsedSeconds: elapsedSeconds,
    resultCount: 0, commanderVictory: false, milestoneSeconds: times.slice(0, count),
    stageRemainingSeconds: phase === 'active' ? 840 - elapsedSeconds + [0, 350, 560][stage] : 0,
    transitionRemainingSeconds: phase === 'transition' ? 60 : 0, overtimeRemainingSeconds: 0,
    gates: [0, 1].map(stageIndex => { const open = !!(mainClaims & (stageIndex === 0 ? 8 : 64));
      const id = f.config.map + `.PersistentLevel.Gate${stageIndex}`;
      return { id, stageIndex, open, hidden: open, collisionEnabled: !open,
        components: [{ id: id + '.Leaf', collisionEnabled: true, hiddenInGame: false, visible: true }] }; }),
  });
  const observations = [observation(0, 'active', 0, 0, 0), observation(0, 'active', 1, 110, 1),
    observation(0, 'active', 3, 180, 2), observation(0, 'active', 7, 250, 3), observation(0, 'transition', 15, 290, 4),
    observation(1, 'active', 15, 350, 4), observation(1, 'active', 31, 460, 5), observation(1, 'active', 63, 460, 6),
    observation(1, 'transition', 127, 500, 7), observation(2, 'active', 127, 560, 7), observation(2, 'active', 127, 630, 7)];
  f.report.baselineProgression = { version: 1, startedStage: 0, startedMainClaims: 0, startedOptionalClaims: 0,
    observations, settledStage: 2, settledMainClaims: 127, commanderVictory: false };
  for (const row of f.raw.frames) {
    row.elapsedSeconds += [0, 150, 160][row.stage]; row.siegeElapsedSeconds = row.elapsedSeconds;
    Object.assign(row, observation(row.stage, 'active', [0, 15, 127][row.stage], row.siegeElapsedSeconds, [0, 4, 7][row.stage]));
  }
  f.raw.frames.forEach((row, i) => { if (i) row.frameMs = (row.elapsedSeconds - f.raw.frames[i - 1].elapsedSeconds) * 1000; });
  f.report.windows = [0, 1, 2].map(stage => { const rows = f.raw.frames.filter(r => r.stage === stage);
    return { stage, startElapsedSeconds: rows[0].elapsedSeconds, endElapsedSeconds: rows.at(-1).elapsedSeconds,
      frameCount: rows.length, settleSeconds: 10 }; });
  return f;
}

test('preserved-city benchmark requires actual zero-state earned captures, durable gate states and an uncompleted commander', () => {
  const f = earnedFixture(); expect(() => validateCitadelPerformance(f.report, f.raw, f.config, false)).not.toThrow();
  for (const change of [
    (v: ReturnType<typeof earnedFixture>) => { v.config.isolatedStageWindows = true; },
    (v: ReturnType<typeof earnedFixture>) => { v.report.baselineProgression.startedStage = 2; },
    (v: ReturnType<typeof earnedFixture>) => { v.report.baselineProgression.observations[6].milestoneSeconds[0]++; },
    (v: ReturnType<typeof earnedFixture>) => { v.report.baselineProgression.observations[0].gates[0].open = true; },
    (v: ReturnType<typeof earnedFixture>) => { v.report.baselineProgression.observations[9].elapsedSeconds = 550; },
    (v: ReturnType<typeof earnedFixture>) => { v.report.baselineProgression.commanderVictory = true; },
    (v: ReturnType<typeof earnedFixture>) => { v.raw.frames.at(-1).mainClaims = 255; },
    (v: ReturnType<typeof earnedFixture>) => { v.report.fullSiegeAdmission = true; },
  ]) { const v = earnedFixture(); change(v); expect(() => validateCitadelPerformance(v.report, v.raw, v.config, false)).toThrow(); }
});

test('actual continuous rendered crowd windows derive the budget and retain normal defeated avatars', () => {
  const f = fixture(); const before = JSON.stringify(f.report);
  const result = validateCitadelPerformance(f.report, f.raw, f.config);
  expect(result).toHaveLength(3); expect(result[0].fps).toBeCloseTo(60); expect(result[0].deadRange).toEqual([1, 1]);
  expect(JSON.stringify(f.report)).toBe(before);
});
test('a native passed boolean cannot replace budget, raw timing, actual camera LOS, capacity or normal settings', () => {
  const slow = fixture(20); expect(() => validateCitadelPerformance(slow.report, slow.raw, slow.config)).toThrow(/budget/);
  expect(() => validateCitadelPerformance(slow.report, slow.raw, slow.config, false)).not.toThrow();
  for (const change of [
    (f: ReturnType<typeof fixture>) => { f.report.settings.maxFps = 60; },
    (f: ReturnType<typeof fixture>) => { f.report.settings.gameUserSettingsIni = 'C:/different.ini'; },
    (f: ReturnType<typeof fixture>) => { f.raw.frames[1800].unoccluded = 35; },
    (f: ReturnType<typeof fixture>) => { f.raw.frames[1800].visible = 35; f.raw.frames[1800].eligible = false; },
    (f: ReturnType<typeof fixture>) => { f.raw.frames[1800].aegisEnrolled = 17; f.raw.frames[1800].eligible = false; },
    (f: ReturnType<typeof fixture>) => { f.raw.frames[1800].elapsedSeconds += 3; },
    (f: ReturnType<typeof fixture>) => { f.raw.frames[1800].cameraEye[2] += 100; },
    (f: ReturnType<typeof fixture>) => { f.report.roster[0].combatLevel = 1; },
    (f: ReturnType<typeof fixture>) => { f.report.formationPositions[0].capsuleClear = false; },
  ]) { const f = fixture(); change(f); expect(() => validateCitadelPerformance(f.report, f.raw, f.config)).toThrow(); }
});
test('actual transition and paused frames break exposure instead of hiding wall time or resetting gameplay clocks', () => {
  const f = fixture(), row = f.raw.frames[1800];
  Object.assign(row, { phase: 'transition', encounterActive: false, cameraMatches: false, eligible: false, cameraEye: [0, 0, 4000] });
  expect(() => validateCitadelPerformance(f.report, f.raw, f.config)).toThrow(/continuous/);
  Object.assign(row, { phase: 'active', leasePaused: true });
  expect(() => validateCitadelPerformance(f.report, f.raw, f.config)).toThrow(/continuous/);
});
test('baseline compares real preserved-city exposure and disclosures, allowing separately bound private INI paths', () => {
  const f = fixture(), baseline = structuredClone(f.report);
  baseline.cityRevision = PRESERVED_AEGIS_CITY.revision; baseline.sourceCity = { ...PRESERVED_AEGIS_CITY };
  baseline.map = '/Game/Private/PerformanceBaseline'; baseline.settings.gameUserSettingsIni = 'C:/baseline/benchmark.ini';
  baseline.bindings.settingsPath = baseline.settings.gameUserSettingsIni;
  const comparison: any = { schemaVersion: 1, sourceCity: { ...PRESERVED_AEGIS_CITY }, candidateCityRevision: f.report.cityRevision,
    candidateSignature: f.report.signature, baselineMap: baseline.map, baselineMapSha256: baseline.mapSha256,
    stages: [0, 1, 2].map(stage => ({ stage, candidateCamera: f.report.bindings.cameras[stage], baselineCamera: baseline.bindings.cameras[stage],
      floorAndAnchorMapping: 'Actual functional floors mapped from original anchors.', architectureDifference: 'Distinct actual floor elevations disclosed.' })) };
  expect(() => validateCitadelPerformanceBaseline(f.report, baseline, comparison)).not.toThrow();
  baseline.roster[0].combatLevel = 1;
  expect(() => validateCitadelPerformanceBaseline(f.report, baseline, comparison)).toThrow();
});
