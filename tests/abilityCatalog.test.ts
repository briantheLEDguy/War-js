import { describe, expect, test } from 'vitest';
import {
  CLASS_RENAMES,
  CLASSES_BY_RACE,
  DESTRUCTION_RACES,
  ORDER_RACES,
} from '../src/data/careers';
import {
  CAREER_ABILITY_KITS,
  HOTBAR_KEYS,
  HOTBAR_SLOT_COUNT,
  createAbilityResourceState,
  getAbilityForCareer,
  getCareerAbilityKit,
} from '../src/game/abilities/abilityData';
import type { AbilityDefinition } from '../src/game/abilities/types';

const playableClasses = [...ORDER_RACES, ...DESTRUCTION_RACES]
  .flatMap((race) => CLASSES_BY_RACE[race]);

describe('ability catalog', () => {
  test('has a complete ten-slot kit for every playable class', () => {
    expect(playableClasses).toHaveLength(24);

    for (const className of playableClasses) {
      const kit = CAREER_ABILITY_KITS[className];
      expect(kit, `${className} kit`).toBeDefined();
      expect(kit.career).toBe(className);
      expect(kit.abilities).toHaveLength(HOTBAR_SLOT_COUNT);
      expect(kit.resource.max).toBeGreaterThan(0);
      expect(kit.resource.initial).toBeGreaterThanOrEqual(0);
      expect(kit.resource.initial).toBeLessThanOrEqual(kit.resource.max);

      expect(kit.abilities.map((ability) => ability.slot)).toEqual([...Array(HOTBAR_SLOT_COUNT).keys()]);
      expect(kit.abilities.map((ability) => ability.key)).toEqual([...HOTBAR_KEYS]);
      expect(new Set(kit.abilities.map((ability) => ability.id)).size).toBe(HOTBAR_SLOT_COUNT);
    }
  });

  test('keeps ability IDs unique and stable-looking', () => {
    const ids = new Set<string>();

    for (const ability of allAbilities()) {
      expect(ability.id).toMatch(/^[a-z0-9_]+\.[a-z0-9_]+$/);
      expect(ability.id.startsWith(`${slug(ability.career)}.`)).toBe(true);
      expect(ids.has(ability.id), `duplicate ability ID ${ability.id}`).toBe(false);
      ids.add(ability.id);
    }

    expect(ids.size).toBe(playableClasses.length * HOTBAR_SLOT_COUNT);
  });

  test('keeps resources, targeting, effects, animations, and visuals valid', () => {
    for (const className of playableClasses) {
      const kit = getCareerAbilityKit(className);
      for (const ability of kit.abilities) {
        expect(ability.career).toBe(className);
        expect(ability.classFamily).toBe(kit.classFamily);
        expect(ability.cooldownSec).toBeGreaterThanOrEqual(0);
        expect(ability.gcdSec).toBeGreaterThanOrEqual(0);

        expectCostWithinKit(ability, kit.resource.max);
        expectTargetingValid(ability);
        expectEffectsValid(ability);
        expectAnimationValid(ability);
        expectVisualValid(ability);
      }
    }
  });

  test('resolves legacy career aliases to renamed playable classes', () => {
    for (const [legacyName, renamedClass] of Object.entries(CLASS_RENAMES)) {
      const renamedKit = getCareerAbilityKit(renamedClass);
      expect(getCareerAbilityKit(legacyName)).toBe(renamedKit);
      expect(getAbilityForCareer(legacyName, 0)?.career).toBe(renamedClass);
      expect(createAbilityResourceState(legacyName)).toEqual(createAbilityResourceState(renamedClass));
    }
  });
});

function allAbilities(): AbilityDefinition[] {
  return playableClasses.flatMap((className) => getCareerAbilityKit(className).abilities);
}

function expectCostWithinKit(ability: AbilityDefinition, resourceMax: number): void {
  const { resource } = ability;
  expect(resource.manaCost ?? 0).toBeGreaterThanOrEqual(0);
  expect(resource.careerBuild ?? 0).toBeGreaterThanOrEqual(0);
  expect(resource.careerCost ?? 0).toBeGreaterThanOrEqual(0);
  expect(resource.minCareer ?? 0).toBeGreaterThanOrEqual(0);
  expect(resource.careerBuild ?? 0).toBeLessThanOrEqual(resourceMax);
  expect(resource.careerCost ?? 0).toBeLessThanOrEqual(resourceMax);
  expect(resource.minCareer ?? 0).toBeLessThanOrEqual(resourceMax);
}

function expectTargetingValid(ability: AbilityDefinition): void {
  expect(ability.targeting.range).toBeGreaterThanOrEqual(0);
  expect(ability.targeting.tracePolicy).toBe('server_auth');
  if (ability.targeting.radius !== undefined) {
    expect(ability.targeting.radius).toBeGreaterThan(0);
  }
  if (ability.targeting.shape === 'projectile' || ability.targeting.shape === 'pet') {
    expect(ability.targeting.projectileSpeed).toBeGreaterThan(0);
  } else {
    expect(ability.targeting.projectileSpeed).toBeUndefined();
  }
}

function expectEffectsValid(ability: AbilityDefinition): void {
  for (const effect of ability.effects) {
    expect(['damage', 'heal', 'status']).toContain(effect.kind);
    if (effect.kind === 'damage' || effect.kind === 'heal') {
      expect(effect.school).toBeDefined();
      expect(effect.amount?.min).toBeGreaterThan(0);
      expect(effect.amount?.max).toBeGreaterThanOrEqual(effect.amount?.min ?? 0);
    }
    if (effect.kind === 'status') {
      expect(effect.status?.id).toMatch(/^[a-z0-9_]+$/);
      expect(effect.status?.label.length).toBeGreaterThan(0);
      expect(effect.status?.durationSec).toBeGreaterThan(0);
    }
  }
}

function expectAnimationValid(ability: AbilityDefinition): void {
  expect(ability.animation.actionId.length).toBeGreaterThan(0);
  expect(ability.animation.clip.length).toBeGreaterThan(0);
  expect(ability.animation.durationSec).toBeGreaterThan(0);
  expect(ability.animation.notifyWindows.length).toBeGreaterThan(0);
  for (const window of ability.animation.notifyWindows) {
    expect(window.start).toBeGreaterThanOrEqual(0);
    expect(window.end).toBeLessThanOrEqual(1);
    expect(window.end).toBeGreaterThanOrEqual(window.start);
  }
}

function expectVisualValid(ability: AbilityDefinition): void {
  const { icon, vfx } = ability.visual;
  expect(ability.visual.school).toBeDefined();
  expect(icon.symbol.length).toBeGreaterThan(0);
  expect(icon.frame.length).toBeGreaterThan(0);
  expect(icon.accent.length).toBeGreaterThan(0);
  expect(icon.seed).toBeGreaterThanOrEqual(0);
  expect(vfx.cast.length).toBeGreaterThan(0);
  expect(vfx.projectile.length).toBeGreaterThan(0);
  expect(vfx.impact.length).toBeGreaterThan(0);
  expect(vfx.trail.length).toBeGreaterThan(0);
  expect(vfx.motion.length).toBeGreaterThan(0);
  expect(vfx.flair).not.toBe('neutral');
  expect(vfx.seed).toBe(icon.seed);
  expect(vfx.colors.primary).toMatch(/^#[0-9a-f]{6}$/i);
  expect(vfx.colors.secondary).toMatch(/^#[0-9a-f]{6}$/i);
  expect(vfx.colors.accent).toMatch(/^#[0-9a-f]{6}$/i);
  expect(vfx.colors.shadow).toMatch(/^#[0-9a-f]{6}$/i);
  expect(vfx.colors.glow).toMatch(/^rgba\(\d+, \d+, \d+, 0\.\d+\)$/);
}

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}
