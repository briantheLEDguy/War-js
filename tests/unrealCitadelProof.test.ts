import {citadelCapsuleCollisionPolicy,citadelCapsuleKinematicsPolicy} from './fixtures/citadelCapsulePolicy';
import { expect, test } from 'vitest';
import { citadelProofConfig, validateCitadelProof, validateCitadelRouteWidth, validateCitadelWidthDiagnostic, type CitadelLedger } from '../scripts/unreal/citadel-proof';

const ledger = { schemaVersion: 1, signature: 'a'.repeat(64), routes: [
  { id: 'west_stair', start: 'court', end: 'balcony', width: 600, bidirectional: true,
    points: [[0, 0, 0], [1200, 0, 600], [1200, 600, 600]] as [number, number, number][] },
], objectives: Array.from({ length: 8 }, (_, i) => [i * 1000, 0, 0] as [number, number, number]),
optionalObjectives: Array.from({ length: 3 }, (_, i) => [i * 1000, 1000, 0] as [number, number, number]),
gates: [0, 1].map(index => ({ index, id: index ? 'inner' : 'outer',
  leaves: Array.from({ length: index ? 5 : 3 }, (_, i) => ({
    point: [1000 * index, 1000 * i, 0] as [number, number, number], width: 600, height: 1000,
  })),
})) };
const config = () => citadelProofConfig(ledger, '/Game/WorldRebuild/AegisCitadel_abcdef123456/SiegeCandidate',
  'b'.repeat(64), 'c'.repeat(64), 'routes');

test('new recipes require exact retained spawn pads and bidirectional ground exits', () => {
  const modern: CitadelLedger=structuredClone(ledger);
  modern.recipeVersion=5;
  modern.teamSpawns=Array.from({length:6},(_,i)=>[i*100,0,0]);
  modern.spawnApproaches=modern.teamSpawns.map((point,index)=>({index,widthCm:600,
    points:index<2 ? [point] : [point,[0,0,0]],
    ...(index<2 ? {preserveLowerCity:true} : {joinsRoute:'west_stair'})}));
  const make=()=>citadelProofConfig(modern,config().map,'b'.repeat(64),'c'.repeat(64),'routes');
  expect(make().spawnPads).toHaveLength(6);
  expect(make().spawnPads[0].groundGradient).toBeUndefined();
  expect(make().routes.filter(route=>route.id.startsWith('spawn_'))).toHaveLength(8);
  modern.recipeVersion=6;
  expect(make).toThrow(/ground gradient/);
  modern.spawnApproaches.forEach(row => { row.groundGradient=row.index === 0 ? [.5,0] : [0,0]; });
  expect(make().spawnPads[0].groundGradient).toEqual([.5,0]);
  modern.spawnApproaches[0].groundGradient=[2,0];
  expect(make).toThrow(/ground gradient/);
  modern.spawnApproaches[0].groundGradient=[.5,0];
  modern.spawnApproaches[2].groundGradient=[.5,0];
  expect(make).toThrow(/upper pads stay flat/);
  modern.spawnApproaches[2].groundGradient=[0,0];
  modern.spawnApproaches[2].points[0]=[999,0,0];
  expect(make).toThrow(/six retained spawns/);
  modern.spawnApproaches[2].points[0]=modern.teamSpawns[2];
  modern.spawnApproaches[2].points[1]=[0,100,0];
  expect(make).toThrow(/declared ground route/);
  modern.spawnApproaches=[];
  expect(make).toThrow(/six retained spawns/);
});
const widthEvidence = (routes = config().routes) => {
  const clearOverlaps=(queries:number)=>({queries,rawClear:queries,separated:0,blocked:0,unresolved:0,
    rawBlockingHits:0,lastDisposition:queries ? 'raw_clear' : 'unused',contacts:[]});
  const routeWidthConfig = { version: 4, laneFractions: [-1, -.5, 0, .5, 1], maxSpacingCm: 100,
    placementOverlapPolicy:'fresh_live_static_single_body_unit_zero_margin_full_capsule_planes_v1',gateOverlapAdmissionRemainsRaw:true,
    capsulePolicyCheckedEveryTick:true,capsulePolicyCheckedEveryPlacementQuery:true,capsuleCollisionPolicy:citadelCapsuleCollisionPolicy(),capsuleKinematicsPolicy:citadelCapsuleKinematicsPolicy(),
    movementSpacingCm: 10, edgeInsetCm: 0, maxFloorDeviationCm: 120, groundClearanceCm: 2.4,
    minFloorDistanceCm: 1.9, maxFloorDistanceCm: 2.4, capsuleRadiusCm: 42, capsuleHalfHeightCm: 96,
    maxStepHeightCm: 45, walkableFloorZ: 0.7100000381469727, collisionChannel: 'ECC_Pawn', collisionProfile: 'Custom',
    simpleCollision: true, movementMethod: 'ComputeGroundMovementDelta/ramp-resweep/StepUp-floor-handoff/FindFloor/AdjustFloorHeight' };
  const routeWidthSamples = routes.flatMap(route => {
    const previous = new Map<number, number[]>();
    return route.points.slice(1).flatMap((b, segment) => {
      const a = route.points[segment], dx = b[0] - a[0], dy = b[1] - a[1], length = Math.hypot(dx, dy);
      const intervals = Math.ceil(length / 100);
      return Array.from({ length: intervals + 1 }, (_, sample) => routeWidthConfig.laneFractions.map(lane => {
        const alpha = sample / intervals, offset = lane * (route.clearWidthCm / 2 - 42);
        const seed = [a[0] + dx * alpha - dy / length * offset, a[1] + dy * alpha + dx / length * offset,
          a[2] + (b[2] - a[2]) * alpha];
        const before = previous.get(lane); previous.set(lane, seed);
        const movementSteps=before ? Math.ceil(Math.hypot(seed[0] - before[0], seed[1] - before[1]) / 10) : 0;
        return { id: route.id, segment, sample, lane, alpha, clearWidthCm: route.clearWidthCm,
          lateralOffsetCm: offset, seed, center: [seed[0], seed[1], seed[2] + 98.4], floorImpact: [...seed],
          floorZCm: seed[2], floorNormalZ: 1, floorDistanceCm: 2.4, floor: true, placementClear: true,
          transitionClear: true, passed: true, stepAttempted: false, stepSucceeded: false,
          movementSteps,placementOverlapEvidence:clearOverlaps(2),
          movementOverlapEvidence:clearOverlaps(movementSteps ? 2+3*movementSteps : 0) };
      })).flat();
    });
  });
  return { capsuleRadiusCm: 42, capsuleHeightCm: 192, routeWidthConfig, routeWidthSamples,
    routeWidthComplete: true, routeWidthPassed: true };
};
const report = () => {
  const setup = config();
  return { passed: true, signature: setup.signature, map: setup.map, cityRevision: setup.cityRevision,
    mapSha256: setup.mapSha256, views: 0, routesWalked: 2, routeFailures: [], physicalFailures: [], visualApproved: false,
    releaseAcceptance: false, gateSweeps: setup.gates.flatMap(g => [0, 1, 2].flatMap(phase =>
      [-1, 0, 1].flatMap(lane => [-1, 1].map(direction => ({ id: g.id, phase, lane, direction,
        passed: true, startClear: true, endClear: true, sweepHalfSpanCm: g.sweepHalfSpanCm, actualLeafHalfThicknessCm: 55,
        closed: phase === 0 || (phase === 1 && g.index === 1),
        blocked: phase === 0 || (phase === 1 && g.index === 1) }))))),
    gateVerticalSweeps: setup.gates.flatMap(g => [0, 1, 2].flatMap(phase =>
      [1, 2, 3].flatMap(level => [-1, 1].map(direction => ({ id: g.id, phase, level, direction,
        heightCm: g.height, capsuleHalfHeightCm: 96, centerOffsetCm: 99 + (g.height - 198) * level / 4,
        passed: true, startClear: true, endClear: true, sweepHalfSpanCm: g.sweepHalfSpanCm, actualLeafHalfThicknessCm: 55,
        closed: phase === 0 || (phase === 1 && g.index === 1),
        blocked: phase === 0 || (phase === 1 && g.index === 1) }))))),
    objectiveSamples: setup.anchors.flatMap(a => Array.from({ length: 8 }, (_, spoke) =>
      ({ id: a.id, spoke, floor: true, capsuleClear: true, lineOfSight: true }))),
    ...widthEvidence(setup.routes), completedRoutes: setup.routes.map(r => ({ id: r.id, waypoints: 3,
      collisionEnabled: true, grounded: true, distanceCm: 1800 })) };
};

test('full-width admission requires fresh complete native capsule policy and continuous checks',()=>{
  for (const edit of [
    (r:any)=>{r.routeWidthConfig.version=3;},
    (r:any)=>{delete r.routeWidthConfig.capsuleCollisionPolicy;},
    (r:any)=>{delete r.routeWidthConfig.capsuleKinematicsPolicy;},
    (r:any)=>{r.routeWidthConfig.capsuleKinematicsPolicy.scaledRadiusCm=21;},
    (r:any)=>{r.routeWidthConfig.capsulePolicyCheckedEveryTick=false;},
    (r:any)=>{r.routeWidthConfig.capsulePolicyCheckedEveryPlacementQuery=false;},
    (r:any)=>{r.routeWidthConfig.capsuleCollisionPolicy.responses[0]=0;},
    (r:any)=>{r.routeWidthConfig.capsuleCollisionPolicy.classDefaultResponses[63]=1;},
  ]) {
    const candidate=report();edit(candidate);
    expect(()=>validateCitadelProof(candidate,config())).toThrow();
  }
  expect(()=>validateCitadelProof(report(),config())).not.toThrow();
});

test('bounded native width diagnostics retain every signed sample and cannot grant traversal acceptance',()=>{
  const diagnostic={...report(),diagnosticOnly:true,passed:false,routesWalked:0,completedRoutes:[],
    citywideAcceptance:false,routeWidthPassed:false};
  diagnostic.routeWidthSamples[0].passed=false;
  expect(()=>validateCitadelWidthDiagnostic(diagnostic,config())).not.toThrow();
  expect(()=>validateCitadelProof(diagnostic,config())).toThrow(/failed/);
  for (const edit of [
    (r:typeof diagnostic)=>{r.passed=true;},
    (r:typeof diagnostic)=>{r.releaseAcceptance=true;},
    (r:typeof diagnostic)=>{r.routeWidthSamples.pop();},
    (r:typeof diagnostic)=>{r.routeWidthSamples[0]=structuredClone(r.routeWidthSamples[1]);},
    (r:typeof diagnostic)=>{r.routeWidthSamples[0].seed[2]+=1;},
  ]) {
    const bad=structuredClone(diagnostic);edit(bad);
    expect(()=>validateCitadelWidthDiagnostic(bad,config())).toThrow(/diagnostic/);
  }
});

test('native spawn receipts cannot omit, duplicate, move or waive blocked pad samples', () => {
  const setup=config();
  setup.spawnPads=[{index:3,point:[15300,-4500,4210],widthCm:600}];
  const spawnSamples=Array.from({length:25},(_,i)=>{
    const x=Math.floor(i/5)-2,y=i%5-2;
    return {index:3,x,y,seed:[15300+x*129,-4500+y*129,4210],clear:true};
  });
  const evidence={...report(),spawnSamples};
  expect(()=>validateCitadelProof(evidence,setup)).not.toThrow();
  for (const change of ['missing','duplicate','moved','blocked']) {
    const altered=structuredClone(evidence);
    if (change==='missing') altered.spawnSamples.pop();
    else if (change==='duplicate') altered.spawnSamples[24]=altered.spawnSamples[0];
    else if (change==='moved') altered.spawnSamples[0].seed[1]+=1;
    else altered.spawnSamples[0].clear=false;
    expect(()=>validateCitadelProof(altered,setup)).toThrow(/spawn|Spawn/);
  }
});

test('every corridor includes grounded edge lanes and swept transitions through turns', () => {
  const evidence = widthEvidence();
  expect(() => validateCitadelRouteWidth(evidence, config().routes)).not.toThrow();
  expect(evidence.routeWidthSamples.some(row => row.segment === 1 && row.sample === 0 && row.lane === 1 && row.movementSteps > 1)).toBe(true);
  const missing = widthEvidence(); missing.routeWidthSamples.pop();
  expect(() => validateCitadelRouteWidth(missing, config().routes)).toThrow(/full-width route sample/);
  const duplicate = widthEvidence(); duplicate.routeWidthSamples.push(duplicate.routeWidthSamples[0]);
  expect(() => validateCitadelRouteWidth(duplicate, config().routes)).toThrow(/Duplicate full-width/);
  const noTransition = widthEvidence(); noTransition.routeWidthSamples[5].movementSteps = 0;
  expect(() => validateCitadelRouteWidth(noTransition, config().routes)).toThrow(/full-width route sample/);
});

test('full-width proof cannot shrink the capsule, retreat its edges or substitute another floor', () => {
  for (const alter of [
    (e: ReturnType<typeof widthEvidence>) => { e.routeWidthConfig.capsuleRadiusCm = 20; e.capsuleRadiusCm = 20; },
    (e: ReturnType<typeof widthEvidence>) => { e.routeWidthConfig.edgeInsetCm = 100; },
    (e: ReturnType<typeof widthEvidence>) => { e.routeWidthSamples[0].seed[1] += 100; },
    (e: ReturnType<typeof widthEvidence>) => { e.routeWidthSamples[0].floorDistanceCm = 100; },
    (e: ReturnType<typeof widthEvidence>) => { e.routeWidthSamples[0].center[2] += 1000; },
    (e: ReturnType<typeof widthEvidence>) => { e.routeWidthSamples[0].floorNormalZ = .5; },
    (e: ReturnType<typeof widthEvidence>) => { e.routeWidthSamples[0].floorZCm = 500; e.routeWidthSamples[0].floorImpact[2] = 500; },
    (e: ReturnType<typeof widthEvidence>) => { e.routeWidthSamples[0].placementClear = false; },
    (e: ReturnType<typeof widthEvidence>) => { e.routeWidthSamples[0].stepAttempted = true; },
  ]) { const evidence = widthEvidence(); alter(evidence); expect(() => validateCitadelRouteWidth(evidence, config().routes)).toThrow(); }
});

test('rounded-capsule floor contact is checked using native support rather than planar arithmetic', () => {
  const evidence = widthEvidence(); evidence.routeWidthSamples[0].floorZCm += 10; evidence.routeWidthSamples[0].floorImpact[2] += 10;
  expect(() => validateCitadelRouteWidth(evidence, config().routes)).not.toThrow();
});

test('every ledger corridor gets independent forward and reverse movement proof', () => {
  const setup = config();
  expect(setup.routes.map(r => r.id)).toEqual(['west_stair:forward', 'west_stair:reverse']);
  expect(setup.routes[1].points).toEqual([...ledger.routes[0].points].reverse());
  expect(setup.routes.every(r => r.clearWidthCm === 600)).toBe(true);
  expect(() => validateCitadelProof(report(), setup)).not.toThrow();
});

test('capture rings require actual floor, capsule clearance and unobstructed objective sight', () => {
  const blocked = report();
  blocked.objectiveSamples.slice(0, 5).forEach(s => { s.lineOfSight = false; });
  expect(() => validateCitadelProof(blocked, config())).toThrow(/playable capture/);
  const flying = report(); flying.objectiveSamples.slice(0, 5).forEach(s => { s.floor = false; });
  expect(() => validateCitadelProof(flying, config())).toThrow(/playable capture/);
  const duplicate = report(); duplicate.objectiveSamples[0].spoke = 1;
  expect(() => validateCitadelProof(duplicate, config())).toThrow(/playable capture/);
});

test('all eight leaves need both-direction center and edge sweeps for every gate milestone', () => {
  expect(config().gates).toHaveLength(8);
  expect(report().gateSweeps).toHaveLength(144);
  const missing = report(); missing.gateSweeps.pop();
  expect(() => validateCitadelProof(missing, config())).toThrow(/gate sweep/);
  const leaking = report(); leaking.gateSweeps[0].blocked = false;
  expect(() => validateCitadelProof(leaking, config())).toThrow(/leaking/);
  const obstructed = report(); obstructed.gateSweeps.at(-1)!.blocked = true;
  expect(() => validateCitadelProof(obstructed, config())).toThrow(/obstructed/);
});

test('a local gate sweep is derived from exact flat route legs and full capsule clearance', () => {
  const limited: CitadelLedger = structuredClone(ledger);
  const leaf = limited.gates[0].leaves[1];
  leaf.approachClearance = { incomingFlatLengthCm: 155, outgoingFlatLengthCm: 2300,
    maximumLeafHalfThicknessCm: 55, pedestrianCapsuleRadiusCm: 42, requiredCapsuleFloorMarginCm: 3,
    localSweepHalfSpanCm: 110, actualNativeStartClearanceRequired: true, fullWidthRouteTraversalRequired: true };
  limited.routes.push({ id: 'gate_in', start: 'ramp', end: 'gate', width: 1200, bidirectional: true,
    points: [[-500, 1000, 300], [-155, 1000, 0], [0, 1000, 0]] },
    { id: 'gate_out', start: 'gate', end: 'court', width: 600, bidirectional: true,
      points: [[0, 1000, 0], [2300, 1000, 0]] });
  const generate = (value: CitadelLedger) => citadelProofConfig(value, config().map,
    config().cityRevision, config().mapSha256, 'routes');
  expect(generate(limited).gates[1].sweepHalfSpanCm).toBe(110);
  for (const alter of [
    (value: CitadelLedger) => { value.gates[0].leaves[1].approachClearance!.localSweepHalfSpanCm = 90; },
    (value: CitadelLedger) => { value.gates[0].leaves[1].approachClearance!.incomingFlatLengthCm = 160; },
    (value: CitadelLedger) => { value.gates[0].leaves[1].approachClearance!.maximumLeafHalfThicknessCm = 70; },
    (value: CitadelLedger) => { value.routes[1].points[1][2] = 5; },
    (value: CitadelLedger) => { value.gates[0].leaves[1].approachClearance!.fullWidthRouteTraversalRequired = false; },
  ]) { const invalid = structuredClone(limited); alter(invalid); expect(() => generate(invalid)).toThrow(/gate|Gate/); }
});

test('gate receipts reject a penetrating seed, an abbreviated sweep or an oversized actual leaf', () => {
  for (const alter of [
    (value: ReturnType<typeof report>) => { value.gateSweeps[0].startClear = false; },
    (value: ReturnType<typeof report>) => { value.gateSweeps[0].endClear = false; },
    (value: ReturnType<typeof report>) => { value.gateSweeps[0].sweepHalfSpanCm = 100; },
    (value: ReturnType<typeof report>) => { value.gateSweeps[0].actualLeafHalfThicknessCm = 360; },
    (value: ReturnType<typeof report>) => { value.gateVerticalSweeps[0].startClear = false; },
  ]) { const invalid = report(); alter(invalid); expect(() => validateCitadelProof(invalid, config())).toThrow(/stage cut|elevated approach/); }
});

test('closed gate evidence covers the upper opening accessible from gallery approaches', () => {
  expect(report().gateVerticalSweeps).toHaveLength(144);
  const missing = report(); missing.gateVerticalSweeps.pop();
  expect(() => validateCitadelProof(missing, config())).toThrow(/Elevated gate/);
  const bypass = report(); bypass.gateVerticalSweeps[0].blocked = false;
  expect(() => validateCitadelProof(bypass, config())).toThrow(/elevated approach/);
  const wrongHeight = report(); wrongHeight.gateVerticalSweeps[0].heightCm = 900;
  expect(() => validateCitadelProof(wrongHeight, config())).toThrow(/elevated approach/);
  const floorOnly = report(); floorOnly.gateVerticalSweeps[0].centerOffsetCm = 99;
  expect(() => validateCitadelProof(floorOnly, config())).toThrow(/elevated approach/);
});

test('total route counts cannot substitute for intended corridor identity or actual movement', () => {
  const wrong = report(); wrong.completedRoutes[1].id = wrong.completedRoutes[0].id;
  expect(() => validateCitadelProof(wrong, config())).toThrow(/Duplicate/);
  const stationary = report(); stationary.completedRoutes[0].distanceCm = 0;
  expect(() => validateCitadelProof(stationary, config())).toThrow(/grounded movement/);
  const flying = report(); flying.completedRoutes[0].grounded = false;
  expect(() => validateCitadelProof(flying, config())).toThrow(/grounded movement/);
});

test('stale revision and missing reverse proof fail without granting review', () => {
  const stale = report(); stale.mapSha256 = 'd'.repeat(64);
  expect(() => validateCitadelProof(stale, config())).toThrow(/another revision/);
  const incomplete = report(); incomplete.completedRoutes.pop();
  expect(() => validateCitadelProof(incomplete, config())).toThrow(/incomplete/);
  const approved = report(); approved.visualApproved = true;
  expect(() => validateCitadelProof(approved, config())).toThrow();
});

test('only fingerprinted private candidate maps and walkable-width ledgers are accepted', () => {
  expect(() => citadelProofConfig(ledger, '/Game/Other', 'b'.repeat(64), 'c'.repeat(64))).toThrow();
  expect(() => citadelProofConfig({ ...ledger, routes: [{ ...ledger.routes[0], width: 50 }] },
    config().map, config().cityRevision, config().mapSha256)).toThrow(/physical route/);
});

test('native visual views use the signed source camera and reject reframing receipts', () => {
  const ids = ['hero', 'front', 'top_down', 'central_plaza', 'grand_gate',
    'west_balcony', 'east_balcony', 'commander_hall'];
  const reviewViews = ids.map(id => ({ id, eyeCm: [0, 0, 1000] as [number, number, number],
    targetCm: [1000, 0, 1000] as [number, number, number], focalLengthMm: 48,
    ...(id === 'top_down' ? { orthographicWidthCm: 26_000 } : {}) }));
  expect(() => citadelProofConfig(ledger, config().map, config().cityRevision, config().mapSha256, 'views'))
    .toThrow(/reference-aligned/);
  const setup = citadelProofConfig({ ...ledger, reviewViews }, config().map,
    config().cityRevision, config().mapSha256, 'views');
  expect(setup.views[0].fieldOfView).toBeCloseTo(41.11209);
  expect(setup.views[2].orthographicWidthCm).toBe(26_000);
  const evidence = { ...report(), routesWalked: 0, completedRoutes: [], views: 8, architectureUiSuppressed: true,
    viewPerformance: setup.views.map(v => ({ id: v.id, eye: v.eye, direction: [1, 0, 0],
      fieldOfView: v.fieldOfView, projection: v.orthographicWidthCm ? 'orthographic' : 'perspective',
      orthographicWidthCm: v.orthographicWidthCm, canvasHudHidden: true, viewportWidgetsCollapsed: true,
      canvasHudCount: 1, viewportWidgetCount: 2 })) };
  expect(() => validateCitadelProof(evidence, setup)).not.toThrow();
  for (const modify of [
    (r: typeof evidence) => { r.architectureUiSuppressed = false; },
    (r: typeof evidence) => { r.viewPerformance[0].canvasHudHidden = false; },
    (r: typeof evidence) => { r.viewPerformance[0].viewportWidgetsCollapsed = false; },
    (r: typeof evidence) => { r.viewPerformance[0].canvasHudCount = -1; },
    (r: typeof evidence) => { r.viewPerformance[0].viewportWidgetCount = .5; },
    (r: typeof evidence) => { r.viewPerformance[0].canvasHudCount = 1025; },
  ]) {
    const unverified = structuredClone(evidence); modify(unverified);
    expect(() => validateCitadelProof(unverified, setup)).toThrow(/UI|suppression/);
  }
  const historical = structuredClone(evidence);
  delete (historical as any).architectureUiSuppressed;
  delete (historical.viewPerformance[0] as any).canvasHudHidden;
  expect(() => validateCitadelProof(historical, setup)).toThrow(/suppression/);
  evidence.viewPerformance[0].eye = [100, 0, 1000];
  expect(() => validateCitadelProof(evidence, setup)).toThrow(/differs from/);
});
