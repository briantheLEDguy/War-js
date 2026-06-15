import type { CharacterState } from '../services/types';

export const BASELINE_FULL_REGEN_SECONDS = 30;
const REGEN_CARRY_EPSILON = 1e-9;

type RegeneratingCharacter = Pick<CharacterState, 'health' | 'maxHealth' | 'mana' | 'maxMana'>;
export type ResourceRegenerationPatch = Partial<Pick<CharacterState, 'health' | 'mana'>>;

interface ResourceTickResult {
  value: number;
  carry: number;
  changed: boolean;
}

export class ResourceRegeneration {
  private healthCarry = 0;
  private manaCarry = 0;

  reset(): void {
    this.healthCarry = 0;
    this.manaCarry = 0;
  }

  tick(character: RegeneratingCharacter | null, dtSeconds: number): ResourceRegenerationPatch | null {
    if (!character) {
      this.reset();
      return null;
    }
    if (!Number.isFinite(dtSeconds) || dtSeconds <= 0) return null;

    const health = regenerateResource(
      character.health,
      character.maxHealth,
      dtSeconds,
      this.healthCarry,
    );
    const mana = regenerateResource(
      character.mana,
      character.maxMana,
      dtSeconds,
      this.manaCarry,
    );

    this.healthCarry = health.carry;
    this.manaCarry = mana.carry;

    const patch: ResourceRegenerationPatch = {};
    if (health.changed) patch.health = health.value;
    if (mana.changed) patch.mana = mana.value;
    return patch.health !== undefined || patch.mana !== undefined ? patch : null;
  }
}

function regenerateResource(
  rawCurrent: number,
  rawMax: number,
  dtSeconds: number,
  carry: number,
): ResourceTickResult {
  const max = normalizePoolValue(rawMax, 0);
  const current = clamp(normalizePoolValue(rawCurrent, max), 0, max);

  if (max <= 0 || current >= max) {
    return {
      value: max,
      carry: 0,
      changed: rawCurrent !== max,
    };
  }

  const nextCarry = carry + (max / BASELINE_FULL_REGEN_SECONDS) * dtSeconds;
  const wholePoints = Math.floor(nextCarry + REGEN_CARRY_EPSILON);
  if (wholePoints <= 0) {
    return {
      value: current,
      carry: nextCarry,
      changed: rawCurrent !== current,
    };
  }

  const value = Math.min(max, current + wholePoints);
  return {
    value,
    carry: value >= max ? 0 : nextCarry - wholePoints,
    changed: rawCurrent !== value,
  };
}

function normalizePoolValue(value: number, fallback: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.round(value)) : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
