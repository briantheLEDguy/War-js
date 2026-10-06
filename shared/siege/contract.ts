/** Versioned semantic contract; native servers alone evaluate physical siege presence/combat. */
export const CAPITAL_SIEGE_RULES_VERSION = 2 as const;
export const CAPITAL_SIEGE_RULES = Object.freeze({
  version: CAPITAL_SIEGE_RULES_VERSION, capacity: 18, preparationSeconds: 180,
  stageSeconds: 840, transitionSeconds: 60, overtimeSeconds: 120,
  captureSeconds: 90, objectiveCount: 8, optionalCount: 3,
});
export const CAPITAL_SIEGE_OBJECTIVES = [
  'supplies', 'convoy_checkpoint_1', 'convoy_checkpoint_2', 'outer_breach',
  'left_capture', 'right_capture', 'central_capture', 'commander',
] as const;
export const CAPITAL_SIEGE_OPTIONALS = ['sabotage_emplacement', 'reinforcement_post', 'rally_beacon'] as const;
export type CapitalSiegePhase = 'preparing' | 'active' | 'transition' | 'finished';
export interface CapitalSiegeSnapshot {
  stage: 0 | 1 | 2;
  phase: CapitalSiegePhase;
  completed: number[];
  optionalCompleted: number[];
  elapsed: number;
  remaining: number;
  transitionRemaining: number;
  overtimeRemaining: number;
  attackersWon?: boolean;
  preparationRemaining?: number;
  progress?: number;
  leftProgress?: number;
  rightProgress?: number;
  optionalProgress?: number;
  absence?: number;
  leftAbsence?: number;
  rightAbsence?: number;
  optionalAbsence?: number;
  overtimeAbsence?: number;
  contestedSeconds?: number;
  milestoneSeconds?: number[];
}
export interface CapitalSiegeParticipant {
  characterId: string;
  realm: 'aegis' | 'riftbound';
  /** Absent fields in earlier v2 checkpoints mean a connected participant. */
  connected?: boolean;
  reconnectUntil?: number;
}
export interface NativeCapitalSiegeLease {
  activationId: string;
  campaignId: string;
  round: number;
  zoneId: 'aegis_capital';
  hostId: string;
  contentRevision: string;
  rulesVersion: typeof CAPITAL_SIEGE_RULES_VERSION;
  attacker: 'riftbound';
  defender: 'aegis';
  stats: 'campaign';
  capacity: 18;
  preparationSeconds: 180;
  stageSeconds: 840;
  transitionSeconds: 60;
  overtimeSeconds: 120;
  expiresAt: number;
  paused: boolean;
  sequence: number;
  snapshot: CapitalSiegeSnapshot;
  participants: CapitalSiegeParticipant[];
  /** Only explicitly secured, same-realm adjacent territory is offered for evacuation. */
  safeEvacuationZones?: Record<'aegis' | 'riftbound', string[]>;
  result?: 'city_captured' | 'city_defended';
}
export function initialCapitalSiegeSnapshot(): CapitalSiegeSnapshot {
  return { stage: 0, phase: 'preparing', completed: [], optionalCompleted: [], elapsed: 0,
    remaining: 840, transitionRemaining: 0, overtimeRemaining: 120 };
}
export function capitalObjectiveUnlocked(index: number, completed: readonly number[]): boolean {
  if (!Number.isInteger(index) || index < 0 || index > 7) return false;
  if (index === 0) return true;
  if (index <= 3) return completed.includes(index - 1);
  if (index <= 5) return completed.includes(3);
  if (index === 6) return completed.includes(4) && completed.includes(5);
  return completed.includes(6);
}
/** Completion is a set: the right side can finish before the left side. */
export function validateCapitalSiegeSnapshot(value: unknown, previous?: CapitalSiegeSnapshot): asserts value is CapitalSiegeSnapshot {
  const s = value as CapitalSiegeSnapshot;
  const phases: readonly CapitalSiegePhase[] = ['preparing', 'active', 'transition', 'finished'];
  const indices = (values: unknown, count: number): values is number[] => Array.isArray(values)
    && values.length <= count && new Set(values).size === values.length
    && values.every(i => Number.isInteger(i) && i >= 0 && i < count);
  if (!s || ![0, 1, 2].includes(s.stage) || !['preparing', 'active', 'transition', 'finished'].includes(s.phase)
    || !indices(s.completed, 8) || !indices(s.optionalCompleted, 3)
    // Native capture-first substeps return before decrementing the clock at milestones.
    // One second bounds that existing timing budget without extending any individual timer.
    || !Number.isFinite(s.elapsed) || s.elapsed < 0 || s.elapsed > 3 * (840 + 120) + 2 * 60 + 1
    || !Number.isFinite(s.remaining) || s.remaining < 0 || s.remaining > 840
    || !Number.isFinite(s.transitionRemaining) || s.transitionRemaining < 0 || s.transitionRemaining > 60
    || !Number.isFinite(s.overtimeRemaining) || s.overtimeRemaining < 0 || s.overtimeRemaining > 120
    || (s.attackersWon !== undefined && typeof s.attackersWon !== 'boolean')) throw new Error('Invalid capital siege snapshot.');
  if (s.completed.some(i => !capitalObjectiveUnlocked(i, s.completed))
    || (s.stage > 0 && ![0, 1, 2, 3].every(i => s.completed.includes(i)))
    || (s.stage > 1 && ![4, 5, 6].every(i => s.completed.includes(i)))
    || (s.stage === 0 && s.completed.some(i => i > 3))
    || (s.stage === 1 && s.completed.includes(7))
    || s.optionalCompleted.some(i => i > s.stage)
    || (s.phase === 'preparing' && (s.stage !== 0 || s.completed.length || s.optionalCompleted.length || s.elapsed !== 0))
    || (s.phase === 'transition' && (s.stage === 2 || !s.completed.includes(s.stage === 0 ? 3 : 6)))
    || (s.phase === 'finished' && (s.attackersWon === undefined || (s.attackersWon && s.completed.length !== 8)))
    || (s.phase === 'finished' && !s.attackersWon && (s.completed.includes(7) || s.remaining !== 0 || s.overtimeRemaining !== 0))
    || (s.phase !== 'finished' && s.attackersWon !== undefined)) throw new Error('Capital siege prerequisites or result are invalid.');
  for (const key of ['progress', 'leftProgress', 'rightProgress', 'optionalProgress'] as const)
    if (s[key] !== undefined && (!Number.isFinite(s[key]) || s[key]! < 0 || s[key]! > 1)) throw new Error('Invalid siege capture progress.');
  for (const key of ['absence', 'leftAbsence', 'rightAbsence', 'optionalAbsence', 'overtimeAbsence', 'contestedSeconds'] as const)
    if (s[key] !== undefined && (!Number.isFinite(s[key]) || s[key]! < 0 || s[key]! > s.elapsed)) throw new Error('Invalid siege activity clock.');
  if (s.preparationRemaining !== undefined && (!Number.isFinite(s.preparationRemaining) || s.preparationRemaining < 0 || s.preparationRemaining > 180))
    throw new Error('Invalid siege preparation clock.');
  if (s.milestoneSeconds !== undefined && (!Array.isArray(s.milestoneSeconds) || s.milestoneSeconds.length > 8
    || s.milestoneSeconds.some((t, index, times) => !Number.isFinite(t) || t < 0 || t > s.elapsed
      || (index > 0 && t < times[index - 1])))) throw new Error('Invalid siege milestone clock.');
  if (previous?.milestoneSeconds !== undefined && (!Array.isArray(s.milestoneSeconds)
    || previous.milestoneSeconds.some((time, index) => s.milestoneSeconds![index] !== time)))
    throw new Error('Recorded siege milestone clocks cannot be removed or rewritten.');
  if (previous && (s.stage < previous.stage || s.elapsed < previous.elapsed
    || (s.stage === previous.stage && phases.indexOf(s.phase) < phases.indexOf(previous.phase))
    || previous.completed.some(i => !s.completed.includes(i))
    || previous.optionalCompleted.some(i => !s.optionalCompleted.includes(i))
    || (previous.phase === 'finished' && JSON.stringify(s) !== JSON.stringify(previous))
    || (s.stage === previous.stage && s.phase === previous.phase && (s.remaining > previous.remaining
      || s.transitionRemaining > previous.transitionRemaining || s.overtimeRemaining > previous.overtimeRemaining
      || (s.preparationRemaining !== undefined && previous.preparationRemaining !== undefined
        && s.preparationRemaining > previous.preparationRemaining)))))
    throw new Error('Capital siege milestones and clocks cannot be rolled back.');
}

export function validateNativeCapitalSiegeLease(value: unknown): asserts value is NativeCapitalSiegeLease {
  const lease = value as NativeCapitalSiegeLease;
  if (!lease || lease.rulesVersion !== 2 || lease.zoneId !== 'aegis_capital' || lease.stats !== 'campaign'
    || lease.capacity !== 18 || lease.preparationSeconds !== 180 || lease.stageSeconds !== 840
    || lease.transitionSeconds !== 60 || lease.overtimeSeconds !== 120 || lease.attacker !== 'riftbound' || lease.defender !== 'aegis'
    || !Number.isSafeInteger(lease.round) || lease.round < 1 || !Number.isSafeInteger(lease.sequence) || lease.sequence < 0
    || !Number.isFinite(lease.expiresAt) || lease.expiresAt < 0 || typeof lease.paused !== 'boolean'
    || [lease.activationId, lease.campaignId, lease.hostId, lease.contentRevision].some(v => typeof v !== 'string' || !v || v.length > 300)
    || !Array.isArray(lease.participants) || lease.participants.length > 36
    || lease.participants.some(p => !p || typeof p.characterId !== 'string' || !/^[a-zA-Z0-9_-]{1,100}$/.test(p.characterId) || !['aegis', 'riftbound'].includes(p.realm))
    || lease.participants.some(p => (p.connected !== undefined && typeof p.connected !== 'boolean')
      || (p.reconnectUntil !== undefined && (!Number.isFinite(p.reconnectUntil) || p.reconnectUntil < 0)))
    || new Set(lease.participants.map(p => p.characterId)).size !== lease.participants.length
    || ['aegis', 'riftbound'].some(realm => lease.participants.filter(p => p.realm === realm).length > 18)
    || (lease.result !== undefined && !['city_captured', 'city_defended'].includes(lease.result))) throw new Error('Invalid saved native capital lease.');
  validateCapitalSiegeSnapshot(lease.snapshot);
  if (lease.safeEvacuationZones && ['aegis', 'riftbound'].some(realm => {
    const zones = lease.safeEvacuationZones![realm as 'aegis' | 'riftbound'];
    return !Array.isArray(zones) || zones.length > 8 || new Set(zones).size !== zones.length || zones.some(z => typeof z !== 'string' || !/^[a-z0-9_]+$/.test(z));
  })) throw new Error('Invalid saved native evacuation destinations.');
  if (lease.result && (lease.snapshot.phase !== 'finished' || (lease.result === 'city_captured') !== lease.snapshot.attackersWon))
    throw new Error('Invalid saved native capital result.');
}
