import { describe, expect, it } from 'vitest';
import { citadelDefendedProofConfig, validateCitadelSiegeProof, type CitadelSiegeProofConfig } from '../scripts/unreal/citadel-siege-proof';

const config: CitadelSiegeProofConfig = {
  map: '/Game/WorldRebuild/AegisCitadel_123456abcdef/SiegeCandidate', signature: 'a'.repeat(64),
  geometrySignature: 'b'.repeat(64), cityRevision: 'c'.repeat(64), mapSha256: 'd'.repeat(64),
  proofOnly: true, contentReviewOverride: true,
};
const report = () => ({
  ...config, passed: true, transientReviewOverride: true, productionAdmission: false, steamAdmission: false,
  visualApproval: false, humanPlaytest: false, reconnectVerified: false, normalCharacterRecoveryVerified: false,
  campaignHumanEnrollmentVerified: false, encounterScopedCleanupVerified: true,
  syntheticNormalControllers: false, trustedSettlementAcknowledged: false,
  maxAegis: 18, maxRiftbound: 18, concurrentSides: true, lockedCenterObserved: true,
  movementCm: 50_000, normalAbilityActivations: 40,
  rounds: [
    { phase: 'finished', stage: 2, attackersWon: true, completed: [0, 1, 2, 3, 4, 5, 6, 7], elapsed: 1100 },
    { phase: 'finished', stage: 0, attackersWon: false, completed: [], elapsed: 840 },
  ],
  samples: [{ stage: 1, leftProgress: .2, rightProgress: .3 }],
});
const liveConfig: CitadelSiegeProofConfig = { ...config,
  map: config.map.replace('/SiegeCandidate', '/CampaignCandidate'),
  players: ['aegis', 'riftbound'].flatMap(realm => Array.from({ length: 18 }, (_, i) => `proof-${realm}-${i}`)),
};
const defendedConfig = citadelDefendedProofConfig(liveConfig);
const liveReport = () => ({ ...report(), ...liveConfig, encounterScopedCleanupVerified: false,
  syntheticNormalControllers: true, trustedSettlementAcknowledged: true,
  campaignOutcome: 'city_captured', trustedSettlementResult: 'city_captured', settledActivationId: 'owned-activation',
  rounds: [report().rounds[0]],
});
const defendedReport = () => ({ ...liveReport(), campaignOutcome: 'city_defended', trustedSettlementResult: 'city_defended',
  concurrentSides: false, lockedCenterObserved: false,
  rounds: [report().rounds[1]], samples: [{ stage: 0, completed: [], elapsed: 20 }],
  preparationObserved: true, servicesSuspendedObserved: true, servicesRestoredObserved: true, custodyMovementHeldObserved: true,
  normalCharacters: liveConfig.players!.map((characterId, i) => ({ characterId, realm: i < 18 ? 'aegis' : 'riftbound',
    normalized: false, combatLevel: 40, inventoryUnchanged: true, inventorySha256: 'a'.repeat(64),
    initialInventorySha256: 'a'.repeat(64), inventoryRevision: 1, transferPending: true, movementHeld: true,
    hasAvatar: true, alive: true, modelReady: true, zone: 'aegis_capital', health: 61, mana: 73 })),
});
describe('exact-candidate physical siege receipts', () => {
  it('accepts complete explicitly automated evidence for both real outcomes', () => {
    expect(() => validateCitadelSiegeProof(report(), config)).not.toThrow();
  });
  it('rejects missing physical participants, claims, clocks and independent side evidence', () => {
    for (const change of [
      { maxRiftbound: 17 }, { rounds: [report().rounds[0]] }, { concurrentSides: false }, { samples: [] },
      { rounds: [{ ...report().rounds[0], completed: [0, 1, 2, 3, 4, 6, 7] }, report().rounds[1]] },
      { rounds: [report().rounds[0], { ...report().rounds[1], elapsed: 1 }] },
    ]) expect(() => validateCitadelSiegeProof({ ...report(), ...change }, config)).toThrow();
  });
  it('rejects another candidate and fabricated human, recovery or release approval', () => {
    for (const change of [{ mapSha256: 'f'.repeat(64) }, { productionAdmission: true }, { visualApproval: true },
      { humanPlaytest: true }, { reconnectVerified: true }, { normalCharacterRecoveryVerified: true }])
      expect(() => validateCitadelSiegeProof({ ...report(), ...change }, config)).toThrow();
  });
  it('retains the default live attacker proof and requires the actual matching settlement', () => {
    expect(() => validateCitadelSiegeProof(liveReport(), liveConfig)).not.toThrow();
    expect(() => validateCitadelSiegeProof({ ...liveReport(), trustedSettlementResult: 'city_defended' }, liveConfig)).toThrow();
  });
  it('accepts the separate ordinary live timeout with normal character and custody witnesses', () => {
    expect(() => validateCitadelSiegeProof(defendedReport(), defendedConfig)).not.toThrow();
    // A dead avatar is observed honestly; this fixture does not claim a death/recovery experiment.
    const row = { ...defendedReport().normalCharacters[0], alive: false, health: 0 };
    expect(() => validateCitadelSiegeProof({ ...defendedReport(), normalCharacters: [row, ...defendedReport().normalCharacters.slice(1)] }, defendedConfig)).not.toThrow();
  });
  it('rejects forced early results, earned attacker milestones and unsupported defense approvals', () => {
    for (const change of [
      { rounds: [{ ...report().rounds[1], elapsed: 839 }] }, { rounds: [{ ...report().rounds[1], elapsed: 841 }] },
      { rounds: [{ ...report().rounds[1], completed: [0] }] }, { rounds: [report().rounds[0]] },
      { samples: [{ stage: 1, completed: [0] }] }, { concurrentSides: true }, { preparationObserved: false },
      { custodyMovementHeldObserved: false }, { servicesRestoredObserved: false }, { trustedSettlementAcknowledged: false },
      { trustedSettlementResult: 'city_captured' }, { settledActivationId: '' },
    ]) expect(() => validateCitadelSiegeProof({ ...defendedReport(), ...change }, defendedConfig)).toThrow();
  });
  it('rejects missing/replaced normal inventories, normalization and released custody during transfer', () => {
    for (const change of [{ characterId: 'foreign' }, { realm: 'riftbound' }, { normalized: true }, { combatLevel: 1 },
      { initialInventorySha256: 'b'.repeat(64) }, { inventorySha256: '' }, { movementHeld: false }, { health: Number.NaN }]) {
      const normalCharacters = [{ ...defendedReport().normalCharacters[0], ...change }, ...defendedReport().normalCharacters.slice(1)];
      expect(() => validateCitadelSiegeProof({ ...defendedReport(), normalCharacters }, defendedConfig)).toThrow();
    }
  });
  it('restricts the explicit defense option to a fresh private live fixture', () => {
    expect(() => citadelDefendedProofConfig(config)).toThrow();
    expect(() => citadelDefendedProofConfig({ ...liveConfig, performanceBaseline: true })).toThrow();
    expect(liveConfig.campaignOutcome).toBeUndefined();
    expect(defendedConfig.campaignOutcome).toBe('city_defended');
  });
  it('allows only floating point stage-clock error and the existing final 50ms substep', () => {
    for (const elapsed of [839.99999999998, 840.05])
      expect(() => validateCitadelSiegeProof({ ...defendedReport(), rounds: [{ ...report().rounds[1], elapsed }] }, defendedConfig)).not.toThrow();
    expect(() => validateCitadelSiegeProof({ ...defendedReport(), rounds: [{ ...report().rounds[1], elapsed: 840.1 }] }, defendedConfig)).toThrow();
  });
});
