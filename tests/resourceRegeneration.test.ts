import { describe, expect, test } from 'vitest';
import {
  BASELINE_FULL_REGEN_SECONDS,
  ResourceRegeneration,
} from '../src/game/ResourceRegeneration';
import type { CharacterState } from '../src/services/types';
import { makeCharacter } from './testUtils';

describe('resource regeneration', () => {
  test('regenerates health and mana from empty to full over the baseline duration', () => {
    const regen = new ResourceRegeneration();
    const character = makeRegenCharacter({
      health: 0,
      mana: 0,
      maxHealth: 180,
      maxMana: 60,
    });

    tickFor(regen, character, BASELINE_FULL_REGEN_SECONDS - 0.1);
    expect(character.health).toBeLessThan(character.maxHealth);
    expect(character.mana).toBeLessThan(character.maxMana);

    applyPatch(character, regen.tick(character, 0.1));
    expect(character.health).toBe(180);
    expect(character.mana).toBe(60);
  });

  test('scales by max resource pool so different class baselines finish together', () => {
    const regen = new ResourceRegeneration();
    const character = makeRegenCharacter({
      health: 0,
      mana: 0,
      maxHealth: 120,
      maxMana: 160,
    });

    tickFor(regen, character, BASELINE_FULL_REGEN_SECONDS / 2);
    expect(character.health).toBe(60);
    expect(character.mana).toBe(80);
  });

  test('uses fractional carry without updating every frame', () => {
    const regen = new ResourceRegeneration();
    const character = makeRegenCharacter({
      health: 99,
      mana: 99,
      maxHealth: 100,
      maxMana: 100,
    });

    expect(regen.tick(character, 0.1)).toBeNull();
    expect(regen.tick(character, 0.1)).toBeNull();

    applyPatch(character, regen.tick(character, 0.1));
    expect(character.health).toBe(100);
    expect(character.mana).toBe(100);
  });

  test('resets carry when resources are full', () => {
    const regen = new ResourceRegeneration();
    const character = makeRegenCharacter({
      health: 100,
      mana: 100,
      maxHealth: 100,
      maxMana: 100,
    });

    expect(regen.tick(character, 20)).toBeNull();
    character.health = 99;
    character.mana = 99;

    expect(regen.tick(character, 0.1)).toBeNull();
  });

  test('suppresses health recovery in combat while mana keeps its normal rate', () => {
    const regen = new ResourceRegeneration();
    const character = makeRegenCharacter({ health: 90, maxHealth: 180, mana: 0, maxMana: 60 });

    const patch = regen.tick(character, 15, true);
    expect(patch).toEqual({ mana: 30 });
    applyPatch(character, patch);
    expect(character.health).toBe(90);

    applyPatch(character, regen.tick(character, 15, false));
    expect(character.health).toBe(180);
    expect(character.mana).toBe(60);
  });

  test('combat discards only health carry and resumes healing from a fresh fraction', () => {
    const regen = new ResourceRegeneration();
    const character = makeRegenCharacter({ health: 99, maxHealth: 100, mana: 99, maxMana: 100 });
    expect(regen.tick(character, 0.2)).toBeNull();
    expect(regen.tick(character, 0.05, true)).toBeNull();

    const firstRecovery = regen.tick(character, 0.05, false);
    expect(firstRecovery).toEqual({ mana: 100 });
    applyPatch(character, firstRecovery);
    expect(regen.tick(character, 0.25, false)).toEqual({ health: 100 });
  });

  test.each([0, 90, 180])('does not change health %i during a full combat recovery interval', (health) => {
    const regen = new ResourceRegeneration();
    const character = makeRegenCharacter({ health, maxHealth: 180, mana: 60, maxMana: 60 });
    expect(regen.tick(character, BASELINE_FULL_REGEN_SECONDS, true)).toBeNull();
    expect(character.health).toBe(health);
  });
});

function tickFor(
  regen: ResourceRegeneration,
  character: CharacterState,
  seconds: number,
): void {
  const tickSeconds = 0.1;
  const wholeTicks = Math.round(seconds / tickSeconds);
  for (let i = 0; i < wholeTicks; i += 1) {
    applyPatch(character, regen.tick(character, tickSeconds));
  }
}

function makeRegenCharacter(overrides: Partial<CharacterState>): CharacterState {
  return makeCharacter(overrides);
}

function applyPatch(character: CharacterState, patch: Partial<CharacterState> | null): void {
  if (patch) Object.assign(character, patch);
}
