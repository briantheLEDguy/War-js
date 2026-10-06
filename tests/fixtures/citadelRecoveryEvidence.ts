import { createHash } from 'node:crypto';
import path from 'node:path';
import { recoveryCanonical, type CitadelRecoveryBundle } from '../../scripts/unreal/citadel-recovery-evidence';
import { RECOVERY_EPOCH, recoveryCastFixture, recoveryRuntimeFixture } from './citadelRecoveryRuntime';

const digest = (value: any) => createHash('sha256').update(typeof value === 'string' ? value : recoveryCanonical(value)).digest('hex');
export function recoveryEvidenceFixture(repository = '/portable-test'): CitadelRecoveryBundle {
  const signature = 'a'.repeat(64), fixtureId = 'recovery-portable-fixture', hostId = `citadel-proof-${fixtureId}`;
  const identity = { map: '/Game/WorldRebuild/AegisCitadel_0123456789ab/CampaignCandidate', mapSha256: digest('portable campaign package'),
    signature, cityRevision: 'c'.repeat(64), geometrySignature: 'd'.repeat(64) };
  const players = ['aegis', 'riftbound'].flatMap(realm => Array.from({ length: 18 }, (_, i) => `proof-${signature.slice(0, 12)}-${realm}-${i}`));
  const target = players[0], activationId = `${hostId}:1:aegis_capital:1`, rewardA = digest(`${fixtureId}:reward-a`).slice(0, 32), rewardB = digest(`${fixtureId}:reward-b`).slice(0, 32);
  const character = (id: string) => ({ id, name: 'Portable test character', realm: id.includes('-aegis-') ? 'aegis' : 'riftbound',
    visual: '/Game/Characters/PortableTest', returnMap: identity.map, returnPosition: [10, 20, 109],
    document: { zone: 'aegis_capital', inventory: { revision: 1, characterProgression: { level: 40, xp: 900, gold: 87 },
      items: [{ key: 'earned_item', bagSlot: 0 }], equipment: [{ slot: 'weapon', bagSlot: 0 }], quests: ['active_quest'] },
    runtime: recoveryRuntimeFixture(id,id.includes('-aegis-') ? 'aegis' : 'riftbound') } });
  const beforeA = character(target);
  beforeA.document.runtime=recoveryRuntimeFixture(target,'aegis',RECOVERY_EPOCH+1100,RECOVERY_EPOCH+1000);
  const afterA = structuredClone(beforeA);
  afterA.document.inventory.revision++; afterA.document.inventory.characterProgression.xp += 25;
  afterA.document.inventory.characterProgression.gold += 7; afterA.document.runtime.rewards.push(rewardA);
  const beforeB = structuredClone(afterA);
  beforeB.document.runtime={...recoveryRuntimeFixture(target,'aegis',RECOVERY_EPOCH+5100,RECOVERY_EPOCH+5000),
    rewards:[rewardA]};
  const afterB = structuredClone(beforeB); afterB.document.inventory.revision++;
  afterB.document.inventory.characterProgression.xp += 25; afterB.document.inventory.characterProgression.gold += 7;
  afterB.document.runtime.rewards.push(rewardB);
  const physical = (value: any, returned = false) => ({ characterId: value.id, zone: value.document.zone, pending: false, movementHeld: false, member: !returned,
    normalized: false, alive: true, modelReady: true, sceneReady: true, physicalReady: true, zoneMatches: true, combatLevel: 40,
    capsuleRadiusCm: 42, capsuleHalfHeightCm: 96, safeReturn: returned, position: value.returnPosition, validatedCenter: value.returnPosition });
  const binaryPath = repository + '/unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll';
  const sourceHashes = { [path.join(repository, 'unreal/AegisWar/Source/AegisWar/Private/WarCitadelSiegeProof.cpp')]: digest('portable proof source'),
    [path.join(repository, 'unreal/AegisWar/Source/AegisWar/Private/WarCampaignSiegeSubsystem.cpp')]: digest('portable bridge source') };
  const configs: any[] = [0, 1, 2].map(attempt => ({ ...identity, proofOnly: true, contentReviewOverride: true, players, recoveryOnly: true,
    recovery: { version: 1, attempt, fixtureId, receiptA: rewardA, receiptB: rewardB, binaryPath,
      binarySha256: digest('portable native binary'), sourceHashes, expected: [] } }));
  const mutations: any[] = [0, 1].map(attempt => ({ schemaVersion: 1, ...identity, attempt, fixtureId,
    mutationSucceeded: true, receipt: attempt ? rewardB : rewardA, before: attempt ? beforeB : beforeA, after: attempt ? afterB : afterA,
    cast:recoveryCastFixture((attempt ? afterB : afterA).document.runtime,RECOVERY_EPOCH+(attempt ? 5000 : 1000)),
    witness: { characterId: target, pending: true, movementHeld: true, normalized: false }, configSha256: '' }));
  const cases: any[] = [0, 1].map(attempt => ({ mode: attempt ? 'after_commit' : 'before_commit', requestId: `original-wal-${attempt}`,
    baseRevision: attempt ? 3 : 1, walSequence: attempt + 1, walFilename: `original-${attempt}.json`,
    nodeRevision: attempt ? 4 : 1, nodeCommittedBeforeKill: Boolean(attempt), nativeAckWithheld: true, processKilled: true }));
  const wals = cases.map((c, i) => ({ schemaVersion: 1, hostId, body: { hostId, activationId, characterId: target,
    requestId: c.requestId, baseRevision: c.baseRevision, walSequence: c.walSequence, character: mutations[i].after } }));
  mutations.forEach((m,i)=>{m.wal={filename:cases[i].walFilename,sha256:digest(wals[i]),requestId:cases[i].requestId,
    baseRevision:cases[i].baseRevision,walSequence:cases[i].walSequence};});
  const snapshot = { stage: 0, phase: 'active', completed: [], optionalCompleted: [], elapsed: 10, remaining: 830, transitionRemaining: 0, overtimeRemaining: 120 };
  const checkpoints: any[] = [0, 1, 2].map(attempt => {
    const characters = Object.fromEntries(players.map(id => {
      const value = structuredClone(id === target && attempt ? afterB : character(id));
      if (attempt === 2) {
        value.document.zone = id.includes('-aegis-') ? 'sunmeadow_march' : 'aegis_gate_fortress';
        value.document.runtime={...recoveryRuntimeFixture(id,value.realm,RECOVERY_EPOCH+40_000),rewards:value.document.runtime.rewards};
      }
      const sequence = id === target && attempt ? 2 : 0;
      return [`${hostId}:${id}`, { version: 1, hostId, activationId, characterId: id, realm: value.realm, scope: attempt === 2 ? 'evacuation' : 'participant',
        revision: attempt === 2 ? 8 : id === target && attempt ? 4 : 1, walSequence: sequence, ...(sequence ? { walBaseRevision: 3 } : {}),
        siegeSequence: 0, savedAt: 1000 + attempt, recoveryPending: false, returned: attempt === 2, respawnPending: false, character: value }];
    }));
    const lease = { hostId, activationId, campaignId: hostId, round: 1, zoneId: 'aegis_capital', rulesVersion: 2, stats: 'campaign',
      attacker: 'riftbound', defender: 'aegis', capacity: 18, preparationSeconds: 180, stageSeconds: 840, transitionSeconds: 60,
      overtimeSeconds: 120, sequence: 0, expiresAt: 15000, paused: true, contentRevision: identity.cityRevision, snapshot,
      participants: attempt === 2 ? [] : players.map(id => ({ characterId: id, realm: id.includes('-aegis-') ? 'aegis' : 'riftbound' })),
      safeEvacuationZones: { aegis: ['sunmeadow_march'], riftbound: ['aegis_gate_fortress'] } };
    return { revision: attempt + 1, state: { id: hostId, phase: 'city', results: [], nativeSiegeJournal: { characters, leases: { [activationId]: lease } },
      zones: { aegis_capital: { nativeSiege: lease } } } };
  });
  const row = (route: string, id: string, values: any = {}) => ({ route, hostId, characterId: id, bodySha256: digest('portable HTTP row'),
    forwarded: true, responseStatus: 200, ...values });
  const ack = (revision: number, walSequence = 0, recoveryPending = false) => ({ version: 1, characterId: target, revision, walSequence, recoveryPending });
  const http: any[][] = [0, 1, 2].map(attempt => {
    const rows: any[] = players.map(id => row('membership', id, { action: 'join', characterSha256: digest(character(id)) }));
    if (attempt) {
      const c = cases[attempt - 1]; rows.push(row('replay', target, { requestId: c.requestId, ack: ack(c.baseRevision + 1, c.walSequence, true) }),
        row('restore', target), row('restored', target, { ack: ack(c.baseRevision + 1, c.walSequence) }));
    }
    if (attempt < 2) rows.push(row('replay', target, { requestId: cases[attempt].requestId, baseRevision: cases[attempt].baseRevision,
      walSequence: cases[attempt].walSequence, characterSha256: digest(mutations[attempt].after),
      ...(attempt ? { ack: ack(4, 2) } : { forwarded: false, responseStatus: undefined }) }));
    else for (const id of players) {
      const saved = checkpoints[2].state.nativeSiegeJournal.characters[`${hostId}:${id}`];
      const a = { version: 1, characterId: id, revision: 8, walSequence: saved.walSequence, recoveryPending: false };
      rows.push(row('membership', id, { action: 'leave' }), row('checkpoint', id, { scope: 'participant', returned: true, ack: a }),
        row('checkpoint', id, { scope: 'evacuation', ack: a }), row('checkpoint', id, { scope: 'evacuation', returned: true, ack: a, characterSha256: digest(saved.character) }));
    }
    return rows.map((r, index) => ({ ...r, index }));
  });
  const recovered: any[] = [1, 2].map(attempt => {
    const value=structuredClone(attempt===1 ? afterA : afterB);
    value.document.runtime={...recoveryRuntimeFixture(target,'aegis',RECOVERY_EPOCH+(attempt===1 ? 3000 : 7000),
      RECOVERY_EPOCH+(attempt===1 ? 1000 : 5000)),rewards:value.document.runtime.rewards};
    return {schemaVersion:1,fixtureId,attempt,map:identity.map,signature,configSha256:'',heldObserved:true,character:value,witness:physical(value)};
  });
  const finalCharacters = players.map(id => checkpoints[2].state.nativeSiegeJournal.characters[`${hostId}:${id}`].character);
  const nativeReport: any = { schemaVersion: 1, ...identity, fixtureId, attempt: 2, passed: true, proofOnly: true, recoveryOnly: true,
    heldObserved: true, characters: finalCharacters, returnWitnesses: finalCharacters.map(c => physical(c, true)),
    unfinishedSiege: snapshot, configSha256: '', bindings: configs[2].recovery };
  const flags = ['productionAdmission', 'steamAdmission', 'humanPlaytest', 'visualApproval', 'releaseAcceptance', 'victoryAcceptance', 'conquestAcceptance', 'fullSiegeAdmission'];
  for (const key of [...flags, 'routeAcceptance', 'progressionAcceptance']) nativeReport[key] = false;
  const processes = { schemaVersion: 1, fixtureId, hostId, attempts: [0, 1, 2].map(attempt => ({ attempt, pid: 100 + attempt,
    startedAt: 1000 + attempt * 100, endedAt: 1090 + attempt * 100, termination: attempt === 2 ? 'normal_exit' : 'SIGKILL',
    killRequested: attempt !== 2, exitCode: attempt === 2 ? 0 : null, signalCode: attempt === 2 ? null : 'SIGKILL',
    ...(attempt < 2 ? { requestId: cases[attempt].requestId } : {}), configSha256: '' })) };
  const evidence: any = { version: 1 }, base = `artifacts/unreal/citadel-reference/recovery-proofs/${fixtureId}/`;
  const binding = (name: string, value: any) => ({ path: base + name + '.json', sha256: digest(value) });
  for (let attempt = 0; attempt < 3; attempt++) {
    configs[attempt].recovery.expected = Array.from({ length: attempt }, (_, i) => ({ path: repository + `/unreal/AegisWar/Saved/CitadelSiegeProof/${fixtureId}/attempt-${i}/mutation.json`, sha256: digest(mutations[i]) }));
    const configHash = digest(configs[attempt]); processes.attempts[attempt].configSha256 = configHash;
    if (attempt < 2) mutations[attempt].configSha256 = configHash;
    if (attempt) recovered[attempt - 1].configSha256 = configHash;
    if (attempt === 2) nativeReport.configSha256 = configHash;
  }
  for (const [key, values] of Object.entries({ mutations, recovered, wals, configs, checkpoints }))
    evidence[key] = values.map((value: any, i) => binding(key + '-' + i, value));
  const httpFile = { schemaVersion: 1, fixtureId, hostId, attempts: http };
  evidence.nativeReport = binding('native-recovery-report', nativeReport); evidence.http = binding('http', httpFile); evidence.processes = binding('processes', processes);
  cases.forEach((c, i) => { c.walSha256 = evidence.wals[i].sha256; c.nativeMutationFileSha256 = evidence.mutations[i].sha256;
    c.replayBodySha256 = http[i].find(r => r.requestId === c.requestId).bodySha256; });
  const report: any = { schemaVersion: 1, ...identity, fixtureId, hostId, players, binaryPath, binarySha256: configs[0].recovery.binarySha256, sourceHashes,
    passed: true, recoveryOnly: true, proofOnly: true, contentReviewOverride: true, normalCharacterRecoveryVerified: true,
    outcomeRecoveryVerified: false, equipmentMutationVerified: false, deadIntentVerified: false, cases, http, evidence };
  for (const flag of flags) report[flag] = false;
  return { report, nativeReport, mutations, recovered, wals, configs, checkpoints, http: httpFile, processes };
}
