import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot } from './toolchain';
import { citadelRouteWidthSeed,validateCitadelRouteSurfaceProfiles,validateCitadelSurfaceReport,type CitadelRouteSurfaceProfile } from './citadel-route-surface';
import { validateRoutePlacementOverlaps } from './citadel-placement-evidence';
import { validateCitadelCapsulePolicy,validateCitadelCapsuleKinematics } from './citadel-collision-policy';

type Point = [number, number, number];
interface CitadelGateApproach {
  incomingFlatLengthCm: number; outgoingFlatLengthCm: number;
  maximumLeafHalfThicknessCm: number; pedestrianCapsuleRadiusCm: number;
  requiredCapsuleFloorMarginCm: number; localSweepHalfSpanCm: number;
  actualNativeStartClearanceRequired: boolean; fullWidthRouteTraversalRequired: boolean;
}
export interface CitadelRoute {
  id: string; start: string; end: string; points: Point[]; width: number; bidirectional: boolean;
}
export interface CitadelLedger {
  schemaVersion: number; signature: string; routes: CitadelRoute[];
  recipeVersion?: number;
  teamSpawns?: Point[];
  spawnApproaches?: { index: number; points: Point[]; widthCm: number; joinsRoute?: string; preserveLowerCity?: boolean;
    groundGradient?: [number, number] }[];
  routeSurfaceProfiles?:CitadelRouteSurfaceProfile[];
  objectives: Point[]; optionalObjectives: Point[];
  gates: { id: string; index: number; leaves: { point: Point; width: number; height: number;
    approachClearance?: CitadelGateApproach }[] }[];
  reviewViews?: { id: string; eyeCm: Point; targetCm: Point; focalLengthMm: number; orthographicWidthCm?: number }[];
}
export interface CitadelProofConfig {
  map: string; signature: string; cityRevision: string; mapSha256: string;
  viewSettleSeconds: number; openGatesForTraversal: boolean;
  views: { id: string; eye: Point; target: Point; fieldOfView: number; orthographicWidthCm?: number }[];
  routes: { id: string; points: Point[]; clearWidthCm: number;surfaceProfile?:CitadelRouteSurfaceProfile }[];
  gates: { id: string; index: number; point: Point; width: number; height: number;
    sweepHalfSpanCm: number; approachClearance?: CitadelGateApproach }[];
  anchors: { id: string; point: Point; index: number; optional: boolean }[];
  spawnPads: { index: number; point: Point; widthCm: number; groundGradient?: [number, number] }[];
}

const hash = (file: string) => createHash('sha256').update(readFileSync(file)).digest('hex');
const read = (file: string) => JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const length = (points: Point[]) => points.slice(1).reduce((sum, p, i) =>
  sum + Math.hypot(p[0] - points[i][0], p[1] - points[i][1]), 0);

function spawnGroundGradient(row: { index: number; groundGradient?: [number, number] }, recipeVersion: number) {
  const slope=row.groundGradient ?? [0, 0];
  if ((recipeVersion >= 6 && !row.groundGradient) || !Array.isArray(slope) || slope.length !== 2
    || !slope.every(Number.isFinite) || Math.hypot(...slope) > 1
    || (row.index >= 2 && slope.some(v => v !== 0)))
    throw new Error('Spawn surface requires a finite walkable ground gradient; upper pads stay flat.');
  return slope;
}

function gateSweepHalfSpan(leaf: CitadelLedger['gates'][number]['leaves'][number], routes: CitadelRoute[]): number {
  const approach = leaf.approachClearance;
  if (!approach) return 400;
  const fields = ['incomingFlatLengthCm', 'outgoingFlatLengthCm', 'maximumLeafHalfThicknessCm',
    'pedestrianCapsuleRadiusCm', 'requiredCapsuleFloorMarginCm', 'localSweepHalfSpanCm'] as const;
  if (fields.some(key => !Number.isFinite(approach[key]) || approach[key] <= 0)
    || approach.pedestrianCapsuleRadiusCm < 42 || approach.requiredCapsuleFloorMarginCm < 3
    || approach.actualNativeStartClearanceRequired !== true || approach.fullWidthRouteTraversalRequired !== true)
    throw new Error('Signed gate landing and complete native clearance checks are required.');
  const flat = [0, 0];
  for (const route of routes) for (let index = 0; index < route.points.length; index++) {
    const point = route.points[index];
    if (point.some((coordinate, axis) => Math.abs(coordinate - leaf.point[axis]) > .01)) continue;
    for (const adjacent of [route.points[index - 1], route.points[index + 1]]) {
      if (!adjacent || Math.abs(adjacent[1] - point[1]) > .01 || Math.abs(adjacent[2] - point[2]) > .01) continue;
      const dx = adjacent[0] - point[0];
      if (dx) flat[dx < 0 ? 0 : 1] = Math.max(flat[dx < 0 ? 0 : 1], Math.abs(dx));
    }
  }
  if (Math.abs(flat[0] - approach.incomingFlatLengthCm) > .01
    || Math.abs(flat[1] - approach.outgoingFlatLengthCm) > .01)
    throw new Error('Gate landing lengths disagree with the signed route geometry.');
  const span = Math.min(400, ...flat.map(distance => distance
    - approach.pedestrianCapsuleRadiusCm - approach.requiredCapsuleFloorMarginCm));
  if (Math.abs(span - approach.localSweepHalfSpanCm) > .01
    || span <= approach.maximumLeafHalfThicknessCm + approach.pedestrianCapsuleRadiusCm + 3)
    throw new Error('Gate sweep must fit its landing and start beyond the entire leaf and capsule.');
  return span;
}

/** Width is sampled with the real walking capsule across every signed corridor. */
export function validateCitadelRouteWidth(report: any, routes: CitadelProofConfig['routes']): void {
  if (!routes.length) return;
  const setup = report.routeWidthConfig;
  const finite = (value: any) => typeof value === 'number' && Number.isFinite(value);
  const point = (value: any) => Array.isArray(value) && value.length === 3 && value.every(finite);
  if (report.routeWidthComplete !== true || report.routeWidthPassed !== true || setup?.version !== 4
    || setup.placementOverlapPolicy!=='fresh_live_static_single_body_unit_zero_margin_full_capsule_planes_v1'
    || setup.gateOverlapAdmissionRemainsRaw!==true
    || JSON.stringify(setup.laneFractions) !== '[-1,-0.5,0,0.5,1]' || setup.maxSpacingCm !== 100
    || setup.edgeInsetCm !== 0 || setup.maxFloorDeviationCm !== 120 || setup.groundClearanceCm !== 2.4
    || setup.movementSpacingCm !== 10
    || setup.collisionChannel !== 'ECC_Pawn' || setup.collisionProfile !== 'Custom' || setup.simpleCollision !== true
    || setup.capsulePolicyCheckedEveryTick!==true || setup.capsulePolicyCheckedEveryPlacementQuery!==true
    || setup.movementMethod !== 'ComputeGroundMovementDelta/ramp-resweep/StepUp-floor-handoff/FindFloor/AdjustFloorHeight'
    || !finite(setup.capsuleRadiusCm) || setup.capsuleRadiusCm < 42
    || !finite(setup.capsuleHalfHeightCm) || setup.capsuleHalfHeightCm < 96
    || setup.capsuleRadiusCm !== report.capsuleRadiusCm || setup.capsuleHalfHeightCm * 2 !== report.capsuleHeightCm
    || !finite(setup.maxStepHeightCm) || setup.maxStepHeightCm <= 0 || setup.maxStepHeightCm > 45
    || !finite(setup.walkableFloorZ) || setup.walkableFloorZ < .7 || setup.walkableFloorZ > 1
    || !finite(setup.minFloorDistanceCm) || Math.abs(setup.minFloorDistanceCm - 1.9) > .01
    || !finite(setup.maxFloorDistanceCm) || Math.abs(setup.maxFloorDistanceCm - 2.4) > .01
    || !Array.isArray(report.routeWidthSamples))
    throw new Error('Complete full-width native capsule and floor evidence is required.');
  validateCitadelCapsulePolicy(setup.capsuleCollisionPolicy);
  validateCitadelCapsuleKinematics(setup.capsuleKinematicsPolicy);
  const kinematics=setup.capsuleKinematicsPolicy;
  if (setup.capsuleRadiusCm!==kinematics.scaledRadiusCm || setup.capsuleHalfHeightCm!==kinematics.scaledHalfHeightCm
    || setup.maxStepHeightCm!==kinematics.maxStepHeightCm || setup.walkableFloorZ!==kinematics.walkableFloorZ)
    throw new Error('Full-width setup differs from its native capsule geometry and walking receipt.');
  validateCitadelSurfaceReport(setup,routes);
  const actual = new Map<string, any>();
  for (const row of report.routeWidthSamples) {
    if (!row || typeof row.id !== 'string' || !Number.isInteger(row.segment) || !Number.isInteger(row.sample)
      || !setup.laneFractions.includes(row.lane)) throw new Error('Invalid full-width native sample identity.');
    const key = `${row.id}:${row.segment}:${row.sample}:${row.lane}`;
    if (actual.has(key)) throw new Error('Duplicate full-width native sample.');
    actual.set(key, row);
  }
  let expected = 0;
  for (const route of routes) for (let segment = 0; segment < route.points.length - 1; segment++) {
    const a = route.points[segment], b = route.points[segment + 1];
    const dx = b[0] - a[0], dy = b[1] - a[1], distance = Math.hypot(dx, dy);
    if (distance < 1 || route.clearWidthCm <= 2 * setup.capsuleRadiusCm)
      throw new Error('The full-width route requires a physical walking segment and capsule clearance.');
    const intervals = Math.max(1, Math.ceil(distance / setup.maxSpacingCm));
    for (let sample = 0; sample <= intervals; sample++) for (const lane of setup.laneFractions) {
      expected++;
      const row = actual.get(`${route.id}:${segment}:${sample}:${lane}`);
      const alpha = sample / intervals, offset = lane * (route.clearWidthCm / 2 - setup.capsuleRadiusCm);
      const seed = citadelRouteWidthSeed(route,segment,alpha,lane,setup.capsuleRadiusCm);
      const previous = sample ? actual.get(`${route.id}:${segment}:${sample - 1}:${lane}`)
        : segment ? actual.get(`${route.id}:${segment - 1}:${Math.max(1, Math.ceil(Math.hypot(
          a[0] - route.points[segment - 1][0], a[1] - route.points[segment - 1][1]) / setup.maxSpacingCm))}:${lane}`) : undefined;
      const minimumSteps = previous && point(previous.seed) ? Math.ceil(Math.max(0,
        Math.hypot(seed[0] - previous.seed[0], seed[1] - previous.seed[1]) - .01) / setup.movementSpacingCm) : 0;
      if (!row || !finite(row.alpha) || Math.abs(row.alpha - alpha) > .000001
        || row.clearWidthCm !== route.clearWidthCm || !finite(row.lateralOffsetCm) || Math.abs(row.lateralOffsetCm - offset) > .01
        || !point(row.seed) || row.seed.some((v: number, i: number) => Math.abs(v - seed[i]) > 1)
        || !point(row.center) || Math.hypot(row.center[0] - seed[0], row.center[1] - seed[1]) > 1
        || !point(row.floorImpact) || !finite(row.floorZCm) || Math.abs(row.floorImpact[2] - row.floorZCm) > .01
        || row.center[2] - row.floorZCm < setup.capsuleHalfHeightCm - setup.capsuleRadiusCm - .1
        || row.center[2] - row.floorZCm > setup.capsuleHalfHeightCm + setup.maxStepHeightCm + setup.maxFloorDistanceCm + .1
        || Math.abs(row.floorZCm - seed[2]) > setup.maxFloorDeviationCm
        || !finite(row.floorNormalZ) || row.floorNormalZ < setup.walkableFloorZ || row.floorNormalZ > 1.001
        || !finite(row.floorDistanceCm) || row.floorDistanceCm < setup.minFloorDistanceCm - .1
        || row.floorDistanceCm > setup.maxFloorDistanceCm + .1
        || !Number.isInteger(row.movementSteps) || row.movementSteps < minimumSteps
        || row.floor !== true || row.placementClear !== true || row.transitionClear !== true || row.passed !== true
        || typeof row.stepAttempted !== 'boolean' || typeof row.stepSucceeded !== 'boolean'
        || (row.stepAttempted && !row.stepSucceeded))
        throw new Error(`Blocked, ungrounded or displaced full-width route sample: ${route.id}:${segment}:${sample}:${lane}`);
      validateRoutePlacementOverlaps(row.placementOverlapEvidence,null,setup.capsuleRadiusCm,setup.capsuleHalfHeightCm);
      validateRoutePlacementOverlaps(row.movementOverlapEvidence,row.movementSteps,setup.capsuleRadiusCm,setup.capsuleHalfHeightCm);
    }
  }
  if (actual.size !== expected) throw new Error('Unexpected or missing full-width native samples.');
}

export function citadelProofConfig(ledger: CitadelLedger, map: string, cityRevision: string,
  mapSha256: string, mode: 'all' | 'routes' | 'views' = 'all'): CitadelProofConfig {
  if (ledger.schemaVersion !== 1 || !/^[a-f0-9]{64}$/.test(ledger.signature)
    || !/^\/Game\/WorldRebuild\/AegisCitadel_[a-f0-9]{12}\/[A-Za-z0-9_]+$/.test(map)
    || !/^[a-f0-9]{64}$/.test(cityRevision) || !/^[a-f0-9]{64}$/.test(mapSha256)
    || !ledger.routes.length || new Set(ledger.routes.map(r => r.id)).size !== ledger.routes.length)
    throw new Error('An exact candidate revision and complete route ledger are required.');
  for (const r of ledger.routes) {
    if (!r.id || r.bidirectional !== true || !Number.isFinite(r.width) || r.width < 600
      || r.points.length < 2 || r.points.some(p => p.length !== 3 || !p.every(Number.isFinite))
      || length(r.points) < 1) throw new Error(`Invalid physical route: ${r.id}`);
  }
  const surfaces=validateCitadelRouteSurfaceProfiles(ledger.routeSurfaceProfiles,ledger.routes);
  const approaches=ledger.spawnApproaches ?? [];
  approaches.forEach(row => spawnGroundGradient(row, ledger.recipeVersion ?? 0));
  if ((ledger.recipeVersion ?? 0) >= 5 || approaches.length) {
    if (ledger.teamSpawns?.length !== 6 || approaches.length !== 6
      || new Set(approaches.map(row => row.index)).size !== 6
      || approaches.some(row => !Number.isInteger(row.index) || row.index < 0 || row.index > 5
        || !Number.isFinite(row.widthCm) || row.widthCm < 600 || !row.points.length
        || row.points.some(p => p.length !== 3 || !p.every(Number.isFinite))
        || row.points[0].some((v, axis) => v !== ledger.teamSpawns![row.index][axis])
        || (row.index < 2 ? row.preserveLowerCity !== true || row.points.length !== 1
          : !ledger.routes.some(route => route.id === row.joinsRoute))))
      throw new Error('All six retained spawns require signed full-width pads and route approaches.');
    for (const row of approaches.filter(row => row.index >= 2)) {
      const route=ledger.routes.find(route => route.id === row.joinsRoute)!;
      const end=row.points.at(-1)!;
      const connects=route.points.some(point => point.every((v, axis) => Math.abs(v - end[axis]) < .01))
        || route.points.slice(1).some((b, index) => {
          const a=route.points[index], delta=b.map((v, axis) => v - a[axis]);
          const squared=delta.reduce((sum, v) => sum + v * v, 0);
          const t=squared ? end.reduce((sum, v, axis) => sum + (v - a[axis]) * delta[axis], 0) / squared : -1;
          return t >= 0 && t <= 1 && Math.hypot(...end.map((v, axis) => v - a[axis] - t * delta[axis])) < .01;
        });
      if (!connects || row.widthCm > route.width || row.points.some(point => point[2] !== row.points[0][2]))
        throw new Error('The signed spawn exit must meet its declared ground route without narrowing it.');
    }
  }
  const approachRoutes=approaches.filter(row => row.index >= 2 && row.points.length > 1)
    .map(row => ({ id: `spawn_${row.index}_approach`, points: row.points, width: row.widthCm }));
  if (ledger.gates?.length !== 2 || ledger.gates.some((g, i) => g.index !== i || !g.id
    || g.leaves.length !== (i ? 5 : 3) || g.leaves.some(l => l.point.length !== 3
      || !l.point.every(Number.isFinite) || !Number.isFinite(l.width) || l.width < 600
      || !Number.isFinite(l.height) || l.height < 900)))
    throw new Error('Both complete physical stage cuts are required.');
  if (ledger.objectives?.length !== 8 || ledger.optionalObjectives?.length !== 3
    || [...ledger.objectives, ...ledger.optionalObjectives].some(p => p.length !== 3 || !p.every(Number.isFinite)))
    throw new Error('All eight main and three optional physical anchors are required.');
  const viewIds = ['hero', 'front', 'top_down', 'central_plaza', 'grand_gate',
    'west_balcony', 'east_balcony', 'commander_hall'];
  if (mode !== 'routes' && (!ledger.reviewViews || ledger.reviewViews.length !== viewIds.length
    || new Set(ledger.reviewViews.map(v => v.id)).size !== viewIds.length
    || viewIds.some(id => !ledger.reviewViews!.some(v => v.id === id))
    || ledger.reviewViews.some(v => v.eyeCm.length !== 3 || v.targetCm.length !== 3
      || ![...v.eyeCm, ...v.targetCm].every(Number.isFinite)
      || Math.hypot(...v.eyeCm.map((p, i) => p - v.targetCm[i])) < 1
      || !Number.isFinite(v.focalLengthMm) || v.focalLengthMm < 12 || v.focalLengthMm > 150
      || (v.orthographicWidthCm !== undefined && (!Number.isFinite(v.orthographicWidthCm)
        || v.orthographicWidthCm < 100 || v.orthographicWidthCm > 100_000)))))
    throw new Error('All eight reference-aligned camera views must be recorded in the signed blueprint.');
  return {
    map, signature: ledger.signature, cityRevision, mapSha256, viewSettleSeconds: 12,
    openGatesForTraversal: true,
    gates: ledger.gates.flatMap(g => g.leaves.map((l, i) => ({ id: `${g.id}:${i}`, index: g.index,
      point: l.point, width: l.width, height: l.height, sweepHalfSpanCm: gateSweepHalfSpan(l, ledger.routes),
      ...(l.approachClearance ? { approachClearance: l.approachClearance } : {}) }))),
    anchors: [false, true].flatMap(optional => (optional ? ledger.optionalObjectives : ledger.objectives)
      .map((point, index) => ({ id: `${optional ? 'optional' : 'main'}:${index}`, point, index, optional }))),
    spawnPads: approaches.map(row => ({ index: row.index, point: row.points[0], widthCm: row.widthCm,
      ...(row.groundGradient ? { groundGradient: row.groundGradient } : {}) })),
    routes: mode === 'views' ? [] : [...ledger.routes, ...approachRoutes].flatMap(r => [
      { id: `${r.id}:forward`, points: r.points, clearWidthCm: r.width,...(surfaces.has(r.id) ? {surfaceProfile:surfaces.get(r.id)!} : {}) },
      { id: `${r.id}:reverse`, points: [...r.points].reverse(), clearWidthCm: r.width,...(surfaces.has(r.id) ? {surfaceProfile:surfaces.get(r.id)!} : {}) },
    ]),
    views: mode === 'routes' ? [] : viewIds.map(id => {
      const view = ledger.reviewViews!.find(v => v.id === id)!;
      // Blender uses its 36 mm horizontal sensor; Unreal accepts horizontal FOV.
      return { id, eye: view.eyeCm, target: view.targetCm,
        fieldOfView: 2 * Math.atan(18 / view.focalLengthMm) * 180 / Math.PI,
        ...(view.orthographicWidthCm !== undefined ? { orthographicWidthCm: view.orthographicWidthCm } : {}) };
    }),
  };
}

export function validateCitadelProof(report: any, config: CitadelProofConfig): void {
  if (report?.passed !== true || report.diagnosticOnly===true || report.signature !== config.signature || report.map !== config.map
    || report.cityRevision !== config.cityRevision || report.mapSha256 !== config.mapSha256
    || report.views !== config.views.length || report.routesWalked !== config.routes.length
    || !Array.isArray(report.routeFailures) || report.routeFailures.length
    || !Array.isArray(report.physicalFailures) || report.physicalFailures.length
    || !Array.isArray(report.completedRoutes) || report.completedRoutes.length !== config.routes.length
    || report.visualApproved !== false || report.releaseAcceptance !== false)
    throw new Error('Citadel physical/view proof is failed, incomplete or for another revision.');
  const completed = new Map<string, any>(report.completedRoutes.map((r: any) => [r.id, r]));
  if (completed.size !== config.routes.length) throw new Error('Duplicate physical route evidence.');
  for (const route of config.routes) {
    const evidence = completed.get(route.id);
    if (!evidence || evidence.waypoints !== route.points.length || evidence.collisionEnabled !== true
      || evidence.grounded !== true || !Number.isFinite(evidence.distanceCm)
      || evidence.distanceCm < length(route.points) * .8)
      throw new Error(`Incomplete grounded movement on the intended route: ${route.id}`);
  }
  validateCitadelRouteWidth(report, config.routes);
  if (config.views.length) {
    if (report.architectureUiSuppressed !== true)
      throw new Error('Native architectural views require verified HUD and viewport widget suppression.');
    if (!Array.isArray(report.viewPerformance) || report.viewPerformance.length !== config.views.length
      || new Set(report.viewPerformance.map((v: any) => v.id)).size !== config.views.length)
      throw new Error('Native camera receipts are missing or duplicated.');
    for (const view of config.views) {
      const evidence = report.viewPerformance.find((v: any) => v.id === view.id);
      const direction = view.target.map((p, i) => p - view.eye[i]);
      const magnitude = Math.hypot(...direction);
      if (!evidence || evidence.canvasHudHidden !== true || evidence.viewportWidgetsCollapsed !== true
        || ![evidence.canvasHudCount, evidence.viewportWidgetCount]
          .every(count => Number.isInteger(count) && count >= 0 && count <= 1024))
        throw new Error(`Native architecture UI remains visible or its suppression is unverified: ${view.id}`);
      if (!evidence || !Array.isArray(evidence.eye) || evidence.eye.length !== 3
        || !Array.isArray(evidence.direction) || evidence.direction.length !== 3
        || evidence.eye.some((p: number, i: number) => !Number.isFinite(p) || Math.abs(p - view.eye[i]) > 1)
        || evidence.direction.some((p: number, i: number) => !Number.isFinite(p) || Math.abs(p - direction[i] / magnitude) > .001)
        || !Number.isFinite(evidence.fieldOfView) || Math.abs(evidence.fieldOfView - view.fieldOfView) > .01
        || evidence.projection !== (view.orthographicWidthCm === undefined ? 'perspective' : 'orthographic')
        || (view.orthographicWidthCm !== undefined && (!Number.isFinite(evidence.orthographicWidthCm)
          || Math.abs(evidence.orthographicWidthCm - view.orthographicWidthCm) > 1)))
        throw new Error(`Native view differs from the reference-aligned camera: ${view.id}`);
    }
  }
  if (!Array.isArray(report.gateSweeps) || report.gateSweeps.length !== config.gates.length * 18)
    throw new Error('Physical gate sweep evidence is incomplete.');
  const sweeps = new Map<string, any>(report.gateSweeps.map((s: any) =>
    [`${s.id}:${s.phase}:${s.lane}:${s.direction}`, s]));
  if (sweeps.size !== report.gateSweeps.length) throw new Error('Duplicate gate sweep evidence.');
  for (const gate of config.gates) for (let phase = 0; phase < 3; phase++)
    for (const lane of [-1, 0, 1]) for (const direction of [-1, 1]) {
      const closed = phase === 0 || (phase === 1 && gate.index === 1);
      const sweep = sweeps.get(`${gate.id}:${phase}:${lane}:${direction}`);
      if (!sweep || sweep.passed !== true || sweep.closed !== closed || sweep.blocked !== closed
        || !gateSweepClearance(sweep, gate, report.capsuleRadiusCm))
        throw new Error(`The physical stage cut is leaking or obstructed: ${gate.id}`);
    }
  if (!Array.isArray(report.gateVerticalSweeps) || report.gateVerticalSweeps.length !== config.gates.length * 18)
    throw new Error('Elevated gate bypass sweep evidence is incomplete.');
  const vertical = new Map<string, any>(report.gateVerticalSweeps.map((s: any) =>
    [`${s.id}:${s.phase}:${s.level}:${s.direction}`, s]));
  if (vertical.size !== report.gateVerticalSweeps.length) throw new Error('Duplicate elevated gate sweep evidence.');
  for (const gate of config.gates) for (let phase = 0; phase < 3; phase++)
    for (const level of [1, 2, 3]) for (const direction of [-1, 1]) {
      const closed = phase === 0 || (phase === 1 && gate.index === 1);
      const sweep = vertical.get(`${gate.id}:${phase}:${level}:${direction}`);
      if (!sweep || sweep.passed !== true || sweep.closed !== closed || sweep.blocked !== closed
        || !gateSweepClearance(sweep, gate, report.capsuleRadiusCm)
        || !Number.isFinite(sweep.heightCm) || Math.abs(sweep.heightCm - gate.height) > .01
        || !Number.isFinite(sweep.capsuleHalfHeightCm) || sweep.capsuleHalfHeightCm <= 0
        || gate.height <= 2 * sweep.capsuleHalfHeightCm + 6 || !Number.isFinite(sweep.centerOffsetCm)
        || Math.abs(sweep.centerOffsetCm - (sweep.capsuleHalfHeightCm + 3
          + (gate.height - 2 * sweep.capsuleHalfHeightCm - 6) * level / 4)) > .01)
        throw new Error(`An elevated approach can bypass or obstruct the stage gate: ${gate.id}`);
    }
  if (!Array.isArray(report.objectiveSamples) || report.objectiveSamples.length !== config.anchors.length * 8)
    throw new Error('Objective floor and line-of-sight evidence is incomplete.');
  for (const anchor of config.anchors) {
    const samples = report.objectiveSamples.filter((s: any) => s.id === anchor.id);
    if (samples.length !== 8 || new Set(samples.map((s: any) => s.spoke)).size !== 8
      || samples.some((s: any) => !Number.isInteger(s.spoke) || s.spoke < 0 || s.spoke > 7)
      || samples.filter((s: any) => s.floor === true && s.capsuleClear === true && s.lineOfSight === true).length < 4)
      throw new Error(`Insufficient physically playable capture positions: ${anchor.id}`);
  }
  if (config.spawnPads.length) {
    if (!Array.isArray(report.spawnSamples) || report.spawnSamples.length !== config.spawnPads.length * 25)
      throw new Error('Native spawn pad clearance evidence is incomplete.');
    for (const pad of config.spawnPads) {
      const rows = report.spawnSamples.filter((row: any) => row.index === pad.index);
      if (rows.length !== 25 || new Set(rows.map((row: any) => `${row.x}:${row.y}`)).size !== 25)
        throw new Error(`Native spawn pad samples are missing or duplicated: ${pad.index}`);
      for (const row of rows) {
        const edge=pad.widthCm / 2 - report.capsuleRadiusCm;
        const expected=pad.point.map((v, axis) => v + (axis === 0 ? row.x : axis === 1 ? row.y : 0) * edge / 2);
        const slope=spawnGroundGradient(pad, 0);
        expected[2] += (slope[0] * row.x + slope[1] * row.y) * edge / 2;
        if (!Number.isInteger(row.x) || row.x < -2 || row.x > 2 || !Number.isInteger(row.y) || row.y < -2 || row.y > 2
          || row.clear !== true || !Array.isArray(row.seed) || row.seed.length !== 3
          || row.seed.some((v: number, axis: number) => !Number.isFinite(v) || Math.abs(v - expected[axis]) > .01))
          throw new Error(`Native retained spawn pad is obstructed or differs from its signed footprint: ${pad.index}`);
      }
    }
  }
}

/** A completed diagnostic can contain failures and never grants admission. */
export function validateCitadelWidthDiagnostic(report: any, config: CitadelProofConfig): void {
  const count=config.routes.reduce((total,route)=>total+route.points.slice(1).reduce((sum,b,i)=>
    sum+(Math.max(1,Math.ceil(Math.hypot(b[0]-route.points[i][0],b[1]-route.points[i][1])/100))+1)*5,0),0);
  if (report.diagnosticOnly!==true || report.passed!==false || report.signature!==config.signature
    || report.map!==config.map || report.cityRevision!==config.cityRevision || report.mapSha256!==config.mapSha256
    || report.routesWalked!==0 || report.views!==0 || report.routeWidthComplete!==true
    || ![2,3,4].includes(report.routeWidthConfig?.version) || report.visualApproved!==false || report.releaseAcceptance!==false
    || report.citywideAcceptance!==false || !Array.isArray(report.routeWidthSamples)
    || report.routeWidthSamples.length!==count)
    throw new Error('Native width diagnostic is incomplete, changed or incorrectly claims acceptance.');
  const samples=new Map<string,any>();
  for (const row of report.routeWidthSamples) {
    const key=`${row.id}:${row.segment}:${row.sample}:${row.lane}`;
    if (samples.has(key)) throw new Error('Native width diagnostic contains duplicate samples.');
    samples.set(key,row);
  }
  for (const route of config.routes) for (let segment=0;segment<route.points.length-1;segment++) {
    const a=route.points[segment],b=route.points[segment+1];
    const intervals=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/100));
    for (let sample=0;sample<=intervals;sample++) for (const lane of [-1,-.5,0,.5,1]) {
      const row=samples.get(`${route.id}:${segment}:${sample}:${lane}`);
      const seed=citadelRouteWidthSeed(route,segment,sample/intervals,lane,report.capsuleRadiusCm);
      if (!row || row.clearWidthCm!==route.clearWidthCm || !Array.isArray(row.seed) || row.seed.length!==3
        || row.seed.some((v:number,i:number)=>!Number.isFinite(v) || Math.abs(v-seed[i])>.01)
        || typeof row.passed!=='boolean') throw new Error('Native width diagnostic differs from the signed corridor samples.');
    }
  }
}

function gateSweepClearance(evidence: any, gate: CitadelProofConfig['gates'][number], radius: number): boolean {
  if (evidence.startClear !== true || evidence.endClear !== true
    || !Number.isFinite(radius) || radius < 42 || !Number.isFinite(evidence.sweepHalfSpanCm)
    || Math.abs(evidence.sweepHalfSpanCm - gate.sweepHalfSpanCm) > .01
    || !Number.isFinite(evidence.actualLeafHalfThicknessCm) || evidence.actualLeafHalfThicknessCm <= 0
    || gate.sweepHalfSpanCm <= radius + evidence.actualLeafHalfThicknessCm + 3) return false;
  const approach = gate.approachClearance;
  return !approach || (evidence.actualLeafHalfThicknessCm <= approach.maximumLeafHalfThicknessCm + .01
    && gate.sweepHalfSpanCm + radius + approach.requiredCapsuleFloorMarginCm
      <= Math.min(approach.incomingFlatLengthCm, approach.outgoingFlatLengthCm) + .01);
}

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), ['--routes-only', '--views-only', '--width-diagnostic', '--dry-run'],
      ['--blueprint', '--map', '--city-revision']);
    if (['--routes-only','--views-only','--width-diagnostic'].filter(key=>args.has(key)).length>1)
      throw new Error('Choose one proof or diagnostic mode.');
    const ledgerFile = path.resolve(repoRoot, args.get('--blueprint') ?? '');
    const map = args.get('--map') ?? '';
    const mapFile = path.join(repoRoot, 'unreal/AegisWar/Content', map.replace(/^\/Game\//, '') + '.umap');
    const config = citadelProofConfig(read(ledgerFile), map, args.get('--city-revision') ?? '', hash(mapFile),
      args.has('--routes-only') || args.has('--width-diagnostic') ? 'routes' : args.has('--views-only') ? 'views' : 'all');
    const engine = inspectToolchain(defaultEngineRoot());
    if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
    const id = `${Date.now()}-${process.pid}`;
    const output = path.join(repoRoot, 'artifacts/unreal/citadel-reference/proofs', id);
    const saved = path.join(repoRoot, 'unreal/AegisWar/Saved/CitadelRouteProof', id);
    const configFile = path.join(saved, 'config.json');
    const invocation = [projectPath, map, '-game', '-unattended', '-nop4', '-nosplash', '-nosound',
      '-WarDevelopmentGM', '-WarDutchBastionProof', `-WarCitadelProofConfig=${configFile}`,
      ...(args.has('--width-diagnostic') ? ['-WarCitadelWidthDiagnostic'] : []),
      ...(config.views.length ? ['-RenderOffscreen', '-windowed', '-ForceRes', '-ResX=1920', '-ResY=1080'] : ['-nullrhi']),
      `-abslog=${path.join(output, 'native.log')}`];
    if (args.has('--dry-run')) {
      console.log(JSON.stringify({ command: engine.editorCommand, arguments: invocation, config, executed: false }, null, 2));
    } else {
      mkdirSync(output, { recursive: true }); mkdirSync(saved, { recursive: true });
      writeFileSync(configFile, JSON.stringify(config, null, 2) + '\n');
      const beforeLedger = hash(ledgerFile);
      const run = spawnSync(engine.editorCommand, invocation, { cwd: repoRoot, stdio: 'inherit',
        windowsHide: true, timeout: 3_600_000 });
      if (run.error) throw run.error;
      const reportFile=path.join(output,'report.json');
      copyFileSync(path.join(saved,'report.json'),reportFile);
      const report = read(reportFile);
      if (hash(mapFile) !== config.mapSha256 || hash(ledgerFile) !== beforeLedger)
        throw new Error('Candidate geometry or route plan changed during its proof.');
      for (let i = 0; i < config.views.length; i++) {
        const capture = path.join(saved, `view_${String(i).padStart(2, '0')}.png`);
        if (existsSync(capture)) copyFileSync(capture, path.join(output, config.views[i].id + '.png'));
      }
      if (run.status !== 0) throw new Error(`Native proof failed: ${report.detail}. See ${output}`);
      if (args.has('--width-diagnostic')) {
        validateCitadelWidthDiagnostic(report,config);
        console.log(JSON.stringify({diagnosticOnly:true,output,passed:false,visualApproval:false,fullSiegeApproval:false}));
        process.exit(0);
      }
      validateCitadelProof(report, config);
      for (const view of config.views) if (!existsSync(path.join(output, view.id + '.png')))
        throw new Error(`Native view missing: ${view.id}`);
      console.log(JSON.stringify({ passed: true, output, routes: config.routes.length,
        visualApproval: false, fullSiegeApproval: false }));
    }
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}
