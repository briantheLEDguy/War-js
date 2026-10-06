import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import type { CandidateSiegeContentEvidence } from './siege-content-evidence';

export const PRESERVED_AEGIS_CITY = {
  path: '/Game/Cities/Shared/aegis_capital/City',
  revision: '6ffd751f94efa5aa261779a6853262a6ca5128376c7a65a369e69943de9f6a2f',
} as const;
type Point = [number, number, number];
export interface CitadelPerformanceCamera { stage: number; eye: Point; target: Point; fieldOfView: number; positions: Point[] }
export interface CitadelPerformanceConfig {
  version: 1;
  settingsPath: string; settingsSha256: string;
  binaryPath: string; binarySha256: string;
  sourceHashes: Record<string, string>;
  configHashes: Record<string, string>;
  blueprintPath: string; blueprintSha256: string;
  cameras: CitadelPerformanceCamera[];
  settleSeconds: 10; minWindowSeconds: 60;
}
const hash = (file: string) => createHash('sha256').update(readFileSync(file)).digest('hex');
const read = (file: string) => JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const point = (v: unknown): v is Point => Array.isArray(v) && v.length === 3 && v.every(finite);
const canonical = (v: any): any => Array.isArray(v) ? v.map(canonical)
  : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k => [k, canonical(v[k])])) : v;
const same = (a: any, b: any) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));

export function citadelPerformanceConfig(repositoryRoot: string, evidence: CandidateSiegeContentEvidence,
  blueprintFile: string, settingsSourceFile: string, settingsDestinationFile: string,
  binaryFile?: string): CitadelPerformanceConfig {
  const blueprintPath = path.resolve(blueprintFile), blueprint = read(blueprintPath);
  if (blueprint.signature !== evidence.signature || blueprint.objectives?.length !== 8
    || blueprint.teamSpawns?.length !== 6 || ![...blueprint.objectives, ...blueprint.teamSpawns].every(point))
    throw new Error('Performance cameras require the exact signed candidate objectives and spawns.');
  if (!Array.isArray(blueprint.performanceFormations) || blueprint.performanceFormations.length !== 3
    || new Set(blueprint.performanceFormations.map((f: any) => f.stage)).size !== 3)
    throw new Error('Performance orders require three explicitly signed formations pending native floor and traversal validation.');
  const cameras = [[0, 1, 2, 3], [4, 5, 6], [7]].map((indices, stage) => {
    const objectives: Point[] = indices.map(i => blueprint.objectives[i]);
    const excluded: Point[] = [...objectives, blueprint.optionalObjectives?.[stage]].filter(point);
    const formation = blueprint.performanceFormations.find((f: any) => f.stage === stage);
    if (!formation || formation.minimumCaptureGapCm !== 50 || formation.positions?.length !== 36
      || !formation.positions.every(point) || formation.positions.some((p: Point, i: number) =>
        formation.positions.slice(i + 1).some((q: Point) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 134)
        || excluded.some(q => Math.hypot(p[0] - q[0], p[1] - q[1]) < 700)))
      throw new Error('Signed benchmark formation overlaps another player or an active capture ring at stage ' + stage);
    const camera = formation.camera;
    if (!camera || !point(camera.eye) || !point(camera.target) || camera.horizontalFovDegrees !== 68
      || Math.hypot(...camera.eye.map((n: number, i: number) => n - camera.target[i])) < 100)
      throw new Error('Each crowd requires a signed functional perspective camera, including an unobstructed indoor hall view.');
    return { stage, target: camera.target, eye: camera.eye, fieldOfView: 68, positions: formation.positions };
  });
  const sourceRoot = path.join(repositoryRoot, 'unreal/AegisWar/Source/AegisWar');
  const files = (directory: string): string[] => readdirSync(directory, { withFileTypes: true })
    .flatMap(entry => entry.isDirectory() ? files(path.join(directory, entry.name))
      : /\.(?:cpp|h|cs)$/.test(entry.name) ? [path.join(directory, entry.name)] : []);
  const settingsPath = path.resolve(settingsDestinationFile), settingsSource = path.resolve(settingsSourceFile);
  const sourceRelative = path.relative(path.join(repositoryRoot, 'unreal/AegisWar/Saved/Config'), settingsSource);
  const destinationRelative = path.relative(path.join(repositoryRoot, 'unreal/AegisWar/Saved/CitadelSiegeProof'), settingsPath);
  if (sourceRelative.startsWith('..') || path.isAbsolute(sourceRelative)
    || destinationRelative.startsWith('..') || path.isAbsolute(destinationRelative))
    throw new Error('Benchmark graphics must be seeded from existing project settings into an isolated proof run.');
  const engineSettings = path.join(repositoryRoot, 'unreal/AegisWar/Config/DefaultEngine.ini');
  const binaryPath = path.resolve(binaryFile ?? path.join(repositoryRoot,
    'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll'));
  return { version: 1, settingsPath, settingsSha256: hash(settingsSource), binaryPath, binarySha256: hash(binaryPath),
    sourceHashes: Object.fromEntries(files(sourceRoot).sort().map(file => [file, hash(file)])),
    configHashes: { [engineSettings]: hash(engineSettings), [settingsSource]: hash(settingsSource) },
    blueprintPath, blueprintSha256: hash(blueprintPath), cameras, settleSeconds: 10, minWindowSeconds: 60 };
}

export function requireSamePerformanceFiles(config: CitadelPerformanceConfig): void {
  for (const [file, expected] of [[config.settingsPath, config.settingsSha256], [config.binaryPath, config.binarySha256],
    [config.blueprintPath, config.blueprintSha256], ...Object.entries(config.sourceHashes), ...Object.entries(config.configHashes)])
    if (hash(file) !== expected) throw new Error('Performance source, settings or native binary changed: ' + file);
}

function validSettings(settings: any): boolean {
  return settings && same(settings.resolution, [1920, 1080]) && settings.screenPercentage === 100
    && settings.maxFps === 0 && settings.vSync === 0 && settings.frameSmoothing === false
    && settings.engineFixedFrameRate === false && settings.fappFixedTimeStep === false
    && settings.worldTimeDilation === 1 && settings.dynamicResolutionMode === 0 && settings.rendered === true
    && settings.quality && ['sg.ViewDistanceQuality', 'sg.AntiAliasingQuality', 'sg.ShadowQuality',
      'sg.GlobalIlluminationQuality', 'sg.ReflectionQuality', 'sg.PostProcessQuality', 'sg.TextureQuality',
      'sg.EffectsQuality', 'sg.FoliageQuality', 'sg.ShadingQuality', 'sg.LandscapeQuality']
      .every(key => Number.isInteger(settings.quality[key]) && settings.quality[key] >= 0 && settings.quality[key] <= 4)
    && typeof settings.rhi === 'string' && settings.rhi.length > 0 && !/null/i.test(settings.rhi);
}
function validHardware(hardware: any): boolean {
  return hardware && ['cpu', 'gpu', 'adapter', 'driverVersion', 'os', 'engineVersion']
    .every(key => typeof hardware[key] === 'string' && hardware[key].length > 0 && hardware[key].length <= 2048)
    && /^5\.8\.2(?:[-+]|$)/.test(hardware.engineVersion)
    && Number.isSafeInteger(hardware.physicalMemoryBytes) && hardware.physicalMemoryBytes > 0;
}
function roster(report: any): any[] {
  if (!Array.isArray(report.roster) || report.roster.length !== 36 || !['normal', 'normalized'].includes(report.statsMode)
    || ['aegis', 'riftbound'].some(realm => report.roster.filter((r: any) => r.realm === realm).length !== 18)
    || report.roster.some((r: any) => !r || typeof r.careerId !== 'string' || !r.careerId
      || typeof r.visualAsset !== 'string' || !r.visualAsset.startsWith('/Game/')
      || !Number.isInteger(r.combatLevel) || r.combatLevel < 1 || r.combatLevel > 40
      || !/^[a-f0-9]{64}$/.test(r.equipmentSignature)))
    throw new Error('Performance exposure requires the actual 18-per-realm model and equipment roster.');
  const members = report.roster.map((r: any) => ({ realm: r.realm, careerId: r.careerId, visualAsset: r.visualAsset,
    combatLevel: r.combatLevel, equipmentSignature: r.equipmentSignature }))
    .sort((a: any, b: any) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  if (typeof report.rosterCanonical !== 'string' || report.rosterCanonical.length > 100_000
    || createHash('sha256').update(report.rosterCanonical).digest('hex') !== report.rosterSha256)
    throw new Error('Actual native roster canonical bytes and digest are required.');
  const parsed = report.rosterCanonical.split('\n').map((line: string) => JSON.parse(line));
  if (!same(parsed.map((r: any) => canonical(r)).sort((a: any, b: any) => JSON.stringify(a).localeCompare(JSON.stringify(b))),
    members.map(canonical).sort((a: any, b: any) => JSON.stringify(a).localeCompare(JSON.stringify(b)))))
    throw new Error('Native roster digest describes different characters or equipment.');
  return members;
}

export interface CitadelPerformanceWindow {
  stage: number; frames: number; seconds: number; fps: number; p95FrameMs: number;
  aliveRange: number[]; deadRange: number[]; respawningRange: number[];
}

/** The preserved-city fixture earns traversal through ordinary rules; it never awards a result. */
export function validateCitadelEarnedProgression(report: any, raw: any, config: any): void {
  const proof = report.baselineProgression, observations = proof?.observations;
  if (config.fixtureMode !== 'earned_progression' || config.isolatedStageWindows !== false
    || report.fixtureMode !== 'earned_progression' || report.isolatedStageWindows !== false
    || report.earnedProgressionObserved !== true || proof?.version !== 1 || proof.startedStage !== 0
    || proof.startedMainClaims !== 0 || proof.startedOptionalClaims !== 0 || proof.settledStage !== 2
    || proof.settledMainClaims !== 127 || proof.commanderVictory !== false
    || !Array.isArray(observations) || observations.length < 10 || observations.length > 4096)
    throw new Error('Baseline requires actual earned progression from an empty ordinary stage-zero round.');
  const bitCount = (mask: number) => mask.toString(2).replace(/0/g, '').length;
  let previous: any, gateIds: string[] | undefined;
  const stageStarts = new Map<number, number>(), transitions = new Map<number, number>();
  for (const row of observations) {
    if (!validProgressState(row) || row.siegeElapsedSeconds !== row.elapsedSeconds || row.resultCount !== 0
      || row.commanderVictory !== false || previous && (row.elapsedSeconds < previous.elapsedSeconds
      || row.stage < previous.stage || row.stage > previous.stage + 1
      || (row.mainClaims & previous.mainClaims) !== previous.mainClaims
      || (row.optionalClaims & previous.optionalClaims) !== previous.optionalClaims
      || !same(row.milestoneSeconds.slice(0, previous.milestoneSeconds.length), previous.milestoneSeconds)))
      throw new Error('Earned baseline claims, clocks or milestone history were reset or substituted.');
    if (row.milestoneSeconds.length !== bitCount(row.mainClaims))
      throw new Error('Every earned main capture requires its actual milestone time.');
    if (!Array.isArray(row.gates) || row.gates.length !== 2 || new Set(row.gates.map((g: any) => g.stageIndex)).size !== 2)
      throw new Error('Both actual preserved gate assemblies need observed state.');
    const ids: string[] = [];
    for (const index of [0, 1]) {
      const gate = row.gates.find((g: any) => g.stageIndex === index), expected = !!(row.mainClaims & (index === 0 ? 8 : 64));
      if (!gate || typeof gate.id !== 'string' || !gate.id.startsWith(config.map + '.')
        || gate.open !== expected || gate.hidden !== expected || gate.collisionEnabled !== !expected
        || !Array.isArray(gate.components) || !gate.components.length || gate.components.length > 256
        || new Set(gate.components.map((c: any) => c.id)).size !== gate.components.length
        || gate.components.some((c: any) => typeof c.id !== 'string' || !c.id.startsWith(gate.id + '.')
          || typeof c.collisionEnabled !== 'boolean' || typeof c.hiddenInGame !== 'boolean' || typeof c.visible !== 'boolean'))
        throw new Error('Actual baseline gates differ from earned breach/center claims.');
      ids.push(gate.id);
    }
    if (new Set(ids).size !== 2 || gateIds && !same(ids, gateIds)) throw new Error('Baseline gate identities changed during progression.');
    gateIds = ids;
    if (row.phase === 'transition' && !transitions.has(row.stage)) transitions.set(row.stage, row.elapsedSeconds);
    if (row.phase === 'active' && !stageStarts.has(row.stage)) {
      if (row.stage > 0 && (!transitions.has(row.stage - 1)
        || row.elapsedSeconds - transitions.get(row.stage - 1)! < 59.9
        || row.mainClaims !== (row.stage === 1 ? 15 : 127)))
        throw new Error('Baseline stages must follow earned captures and ordinary sixty-second transitions.');
      stageStarts.set(row.stage, row.elapsedSeconds);
    }
    previous = row;
  }
  const initial = observations[0];
  if (initial.stage !== 0 || initial.phase !== 'active' || initial.mainClaims !== 0 || initial.optionalClaims !== 0
    || initial.elapsedSeconds > .001 || Math.abs(initial.stageRemainingSeconds - 840) > .001
    || previous.stage !== 2 || previous.phase !== 'active' || previous.mainClaims !== 127
    || stageStarts.size !== 3 || transitions.size !== 2
    || [1, 3, 7, 15, 63, 127].some(mask => !observations.some((r: any) => r.mainClaims === mask)))
    throw new Error('Baseline did not observe all ordinary stages and earned milestone boundaries.');
  const reversedObservations = observations.slice().reverse();
  for (const row of raw.frames) {
    const state = { ...row, elapsedSeconds: row.siegeElapsedSeconds };
    if (!validProgressState(state) || row.milestoneSeconds.length !== bitCount(row.mainClaims))
      throw new Error('Raw baseline frames require the actual siege claims, clocks and capture times.');
    const observed = reversedObservations.find((r: any) => r.elapsedSeconds <= row.siegeElapsedSeconds + .001);
    if (!observed || row.stage !== observed.stage || row.phase !== observed.phase || row.mainClaims !== observed.mainClaims
      || row.optionalClaims !== observed.optionalClaims || !same(row.milestoneSeconds, observed.milestoneSeconds)
      || row.stage === 2 && row.mainClaims !== 127)
      throw new Error('Raw baseline exposure differs from the observed earned progression.');
  }
}

function validProgressState(row: any): boolean {
  const allowed = row?.stage === 0 ? [0, 1, 3, 7, 15] : row?.stage === 1 ? [15, 31, 47, 63, 127] : [127];
  return [0, 1, 2].includes(row?.stage) && ['active', 'transition'].includes(row.phase)
    && Number.isSafeInteger(row.mainClaims) && allowed.includes(row.mainClaims)
    && Number.isSafeInteger(row.optionalClaims) && row.optionalClaims >= 0 && row.optionalClaims < 8
    && (row.optionalClaims & ~((1 << (row.stage + 1)) - 1)) === 0
    && finite(row.elapsedSeconds) && row.elapsedSeconds >= 0 && row.elapsedSeconds <= 3001
    && ['stageRemainingSeconds', 'transitionRemainingSeconds', 'overtimeRemainingSeconds'].every(k => finite(row[k]) && row[k] >= 0)
    && row.stageRemainingSeconds <= 840 && row.transitionRemainingSeconds <= 60 && row.overtimeRemainingSeconds <= 120
    && (row.phase === 'transition' ? row.stage < 2 && row.mainClaims === (row.stage === 0 ? 15 : 127)
      && row.stageRemainingSeconds === 0 && row.overtimeRemainingSeconds === 0
      : row.transitionRemainingSeconds === 0 && (row.stageRemainingSeconds > 0 || row.overtimeRemainingSeconds > 0))
    && Array.isArray(row.milestoneSeconds) && row.milestoneSeconds.length <= 7
    && row.milestoneSeconds.every((t: any, i: number) => finite(t) && t > 0 && t <= row.elapsedSeconds
      && (i === 0 || t >= row.milestoneSeconds[i - 1]));
}

export function validateCitadelPerformance(report: any, raw: any,
  config: CandidateSiegeContentEvidence & { performance?: CitadelPerformanceConfig; performanceBaseline?: true;
    isolatedStageWindows?: false; fixtureMode?: 'earned_progression' },
  enforceBudget = true): CitadelPerformanceWindow[] {
  const performance = config.performance;
  if (!performance || performance.version !== 1 || performance.settleSeconds !== 10 || performance.minWindowSeconds !== 60
    || performance.cameras.length !== 3 || new Set(performance.cameras.map(c => c.stage)).size !== 3
    || performance.cameras.some(c => ![0, 1, 2].includes(c.stage) || !point(c.eye) || !point(c.target)
      || Math.hypot(...c.eye.map((v, i) => v - c.target[i])) < 100 || c.fieldOfView !== 68 || c.positions?.length !== 36 || !c.positions.every(point))
    || !report || report.schemaVersion !== 1 || report.passed !== true || report.performanceOnly !== true || report.proofOnly !== true
    || report.map !== config.map || report.signature !== config.signature || report.cityRevision !== config.cityRevision
    || report.mapSha256 !== config.mapSha256 || !/^[a-f0-9]{64}$/.test(report.configSha256)
    || report.productionAdmission !== false || report.steamAdmission !== false || report.humanPlaytest !== false
    || report.visualApproval !== false || report.releaseAcceptance !== false || !same(report.bindings, performance)
    || report.referenceHardwareCertified !== false
    || !validSettings(report.settings) || !validHardware(report.hardware)
    || path.resolve(report.settings?.gameUserSettingsIni ?? '') !== path.resolve(performance.settingsPath)
    || raw?.schemaVersion !== 1 || raw.complete !== true || !Array.isArray(raw.frames) || !raw.frames.length || raw.frames.length > 1_000_000
    || report.frames?.count !== raw.frames.length || !/^[a-f0-9]{64}$/.test(report.frames?.sha256)
    || !Array.isArray(report.windows) || report.windows.length !== 3)
    throw new Error('Rendered performance proof is incomplete, differently bound, capped, or lacks actual raw frames.');
  if (config.performanceBaseline && (report.performanceBaseline !== true || report.isolatedStageWindows !== false
    || report.statsMode !== 'normalized' || report.sourceCity?.path !== PRESERVED_AEGIS_CITY.path
    || report.sourceCity?.revision !== PRESERVED_AEGIS_CITY.revision
    || ['progressionAcceptance', 'victoryAcceptance', 'conquestAcceptance', 'routeAcceptance', 'fullSiegeAdmission']
      .some(key => report[key] !== false)))
    throw new Error('Preserved-city baseline is exposure only and cannot claim full siege progression or admission.');
  if (config.performanceBaseline) validateCitadelEarnedProgression(report, raw, config);
  roster(report);
  raw.frames.forEach((row: any, index: number) => {
    const previous = raw.frames[index - 1];
    if (row.index !== index || previous && (row.stage < previous.stage || row.elapsedSeconds <= previous.elapsedSeconds
      || Math.abs(row.frameMs - (row.elapsedSeconds - previous.elapsedSeconds) * 1000) > 1))
      throw new Error('Raw frame sequence omits wall time or substitutes stage exposure.');
  });
  if (!Array.isArray(report.formationPositions) || report.formationPositions.length !== 108)
    throw new Error('All 108 signed crowd positions need actual native floor, capsule, navigation and capture-exclusion witnesses.');
  const positions = new Map<string, any>(report.formationPositions.map((p: any) => [`${p.stage}:${p.index}`, p]));
  if (positions.size !== 108) throw new Error('Duplicate benchmark formation position witnesses.');
  for (const camera of performance.cameras) camera.positions.forEach((p, index) => {
    const witness = positions.get(`${camera.stage}:${index}`);
    if (!witness || !same(witness.point, p) || !point(witness.actualFloor) || Math.abs(witness.actualFloor[2] - p[2]) > 25
      || !finite(witness.floorNormalZ) || witness.floorNormalZ < Math.SQRT1_2 || witness.floorNormalZ > 1.001
      || witness.capsuleRadiusCm !== 42 || witness.capsuleHalfHeightCm !== 96
      || witness.captureRadiusCm !== 650
      || ['floorClear', 'capsuleClear', 'navigation', 'captureExclusion'].some(k => witness[k] !== true)
      || !finite(witness.minimumCaptureDistanceCm) || witness.minimumCaptureDistanceCm < 700)
      throw new Error('Benchmark formation is ungrounded, obstructed or inside an active capture ring.');
  });
  const windows: CitadelPerformanceWindow[] = [];
  for (const camera of performance.cameras) {
    const rows = raw.frames.filter((f: any) => f.stage === camera.stage);
    let previousElapsed = -1, previousIndex = -1, sequence: any[] = [], longest: any[] = [];
    const direction = camera.target.map((p, i) => p - camera.eye[i]), magnitude = Math.hypot(...direction);
    for (const row of rows) {
      if (!finite(row.elapsedSeconds) || row.elapsedSeconds <= previousElapsed || !finite(row.stageElapsedSeconds)
        || row.stageElapsedSeconds < 0 || !Number.isSafeInteger(row.index)
        || row.index <= previousIndex || !finite(row.frameMs) || row.frameMs <= 0
        || ['gameThreadMs', 'renderThreadMs', 'rhiThreadMs', 'gpuMs', 'physicalMiB'].some(key => !finite(row[key]) || row[key] < 0)
        || ['drawCalls', 'primitives', 'aegisEnrolled', 'riftboundEnrolled', 'alive', 'dead', 'respawning', 'avatars', 'modelReady', 'visible', 'projected', 'recentlyRendered', 'unoccluded', 'streamingRequests']
          .some(key => !Number.isSafeInteger(row[key]) || row[key] < 0)
        || typeof row.eligible !== 'boolean' || !validSettings(row.settings) || !same(row.settings, report.settings)
        || !point(row.cameraEye) || !point(row.cameraDirection) || !finite(row.cameraFov)
        || typeof row.cameraMatches !== 'boolean' || typeof row.encounterActive !== 'boolean'
        || typeof row.leasePaused !== 'boolean' || typeof row.preparing !== 'boolean'
        || !['active', 'transition', 'finished', 'waiting'].includes(row.phase))
        throw new Error('Malformed, substituted or unordered rendered frame evidence at stage ' + camera.stage);
      if (previousElapsed >= 0 && Math.abs(row.frameMs - (row.elapsedSeconds - previousElapsed) * 1000) > 1)
        throw new Error('Performance frame time differs from actual elapsed wall time.');
      previousElapsed = row.elapsedSeconds; previousIndex = row.index;
      if (!/^[a-f0-9]{64}$/.test(row.rosterSha256) || typeof row.statsMode !== 'string'
        || typeof row.benchmarkOrders !== 'boolean' || typeof row.settled !== 'boolean')
        throw new Error('Native population, orders and settling witnesses are missing.');
      if (['aegisEnrolled', 'riftboundEnrolled'].some(k => row[k] > 18)
        || ['alive', 'dead', 'respawning', 'avatars', 'modelReady', 'visible', 'projected', 'recentlyRendered', 'unoccluded'].some(k => row[k] > 36)
        || row.visible > Math.min(row.projected, row.recentlyRendered, row.unoccluded, row.modelReady, row.avatars))
        throw new Error('Impossible native crowd counts.');
      const cameraMatches = row.cameraEye.every((p: number, i: number) => Math.abs(p - camera.eye[i]) <= 1)
        && row.cameraDirection.every((p: number, i: number) => Math.abs(p - direction[i] / magnitude) <= .0001)
        && Math.abs(row.cameraFov - camera.fieldOfView) <= .01;
      const active = row.phase === 'active' && !row.leasePaused && !row.preparing;
      if (row.cameraMatches && !cameraMatches || row.encounterActive !== active)
        throw new Error('Actual camera or encounter activity differs from its native witness.');
      const eligible = active && row.cameraMatches && cameraMatches && row.stageElapsedSeconds >= performance.settleSeconds && row.aegisEnrolled === 18 && row.riftboundEnrolled === 18
        && row.alive + row.dead === 36 && row.alive <= 36 && row.dead <= 36 && row.respawning <= 36 && row.avatars === 36
        && row.modelReady === 36 && row.visible === 36 && row.projected === 36 && row.recentlyRendered === 36
        && row.unoccluded === 36 && row.streamingRequests === 0
        && row.rosterSha256 === report.rosterSha256 && row.statsMode === report.statsMode
        && row.gameThreadMs > 0 && row.renderThreadMs > 0 && row.gpuMs > 0;
      if (row.settled !== (row.stageElapsedSeconds >= performance.settleSeconds))
        throw new Error('Performance stage settling differs from actual stage wall time.');
      if (row.eligible !== eligible) throw new Error('The native crowded population witness disagrees with actual frame counts.');
      if (eligible) sequence.push(row); else sequence = [];
      if (sequence.length && (!longest.length || sequence.at(-1).elapsedSeconds - sequence[0].elapsedSeconds
        > longest.at(-1).elapsedSeconds - longest[0].elapsedSeconds)) longest = sequence;
    }
    const seconds = longest.length > 1 ? longest.at(-1).elapsedSeconds - longest[0].elapsedSeconds : 0;
    if (seconds + .000001 < performance.minWindowSeconds) throw new Error('No continuous settled 36-visible-player 60-second exposure at stage ' + camera.stage);
    const claimed = report.windows.find((w: any) => w.stage === camera.stage);
    if (!claimed || claimed.startElapsedSeconds !== longest[0].elapsedSeconds
      || claimed.endElapsedSeconds !== longest.at(-1).elapsedSeconds || claimed.frameCount !== longest.length
      || claimed.settleSeconds !== performance.settleSeconds)
      throw new Error('Performance window receipt differs from its raw frames.');
    const times: number[] = longest.map(f => f.frameMs).sort((a, b) => a - b);
    const fps = (longest.length - 1) / seconds, p95FrameMs = times[Math.min(times.length - 1, Math.floor(times.length * .95))];
    if (enforceBudget && (fps + .000001 < 60 || p95FrameMs > 16.7 + .000001))
      throw new Error(`Crowded stage ${camera.stage} misses the absolute 60 FPS / 16.7 ms p95 budget.`);
    const range = (key: string) => longest.reduce((values, r) =>
      [Math.min(values[0], r[key]), Math.max(values[1], r[key])], [Infinity, -Infinity]);
    windows.push({ stage: camera.stage, frames: longest.length, seconds, fps, p95FrameMs,
      aliveRange: range('alive'), deadRange: range('dead'), respawningRange: range('respawning') });
  }
  if (raw.frames.some((f: any) => ![0, 1, 2].includes(f.stage))) throw new Error('Unexpected performance stage frames.');
  return windows;
}

export function validateCitadelPerformanceBaseline(candidate: any, baseline: any, comparison: any): void {
  const comparableSettings = (settings: any) => { const result = { ...settings }; delete result.gameUserSettingsIni; return result; };
  if (!same(comparison?.sourceCity, PRESERVED_AEGIS_CITY) || baseline.cityRevision !== PRESERVED_AEGIS_CITY.revision
    || baseline.sourceCity?.path !== PRESERVED_AEGIS_CITY.path || baseline.sourceCity?.revision !== PRESERVED_AEGIS_CITY.revision
    || !same(candidate.hardware, baseline.hardware)
    || !same(comparableSettings(candidate.settings), comparableSettings(baseline.settings)) || candidate.statsMode !== baseline.statsMode
    || !same(roster(candidate), roster(baseline)) || comparison.schemaVersion !== 1
    || comparison.candidateCityRevision !== candidate.cityRevision || comparison.candidateSignature !== candidate.signature
    || comparison.baselineMap !== baseline.map || comparison.baselineMapSha256 !== baseline.mapSha256
    || !Array.isArray(comparison.stages) || comparison.stages.length !== 3
    || new Set(comparison.stages.map((s: any) => s.stage)).size !== 3)
    throw new Error('A fresh comparable rendered baseline for the preserved published Aegis city is required.');
  for (const key of ['settingsSha256', 'binarySha256', 'sourceHashes', 'configHashes'])
    if (!same(candidate.bindings?.[key], baseline.bindings?.[key]))
      throw new Error('Baseline and candidate use different native code or normal settings.');
  for (const stage of comparison.stages) {
    if (![0, 1, 2].includes(stage.stage) || !same(stage.candidateCamera, candidate.bindings.cameras.find((c: any) => c.stage === stage.stage))
      || !same(stage.baselineCamera, baseline.bindings.cameras.find((c: any) => c.stage === stage.stage))
      || typeof stage.floorAndAnchorMapping !== 'string' || !stage.floorAndAnchorMapping.trim()
      || typeof stage.architectureDifference !== 'string' || !stage.architectureDifference.trim())
      throw new Error('Baseline functional camera, floor and anchor mapping is missing or undisclosed.');
  }
}
