import { beforeEach, describe, expect, test, vi } from 'vitest';
import { CLASS_RENAMES, CLASSES_BY_RACE, DESTRUCTION_RACES, ORDER_RACES } from '../src/data/careers';
import { createAbilityResourceState, getCareerAbilityKit, HOTBAR_KEYS } from '../src/game/abilities/abilityData';
import {
  abilityUnlockLevel,
  FULL_KIT_LEVEL,
  isAbilityUnlocked,
  newlyUnlockedAbilities,
} from '../src/game/abilities/abilityProgression';
import { getAbilityActivationFailure, tryActivateAbility } from '../src/game/abilities/AbilityRuntime';
import { spawnAbilityVfx } from '../src/game/abilities/AbilityVfx';
import { Combat } from '../src/game/Combat';
import { useGameStore } from '../src/state/gameStore';
import { getEnemyObject, makeCharacter, makeEnemy, makePlayer, resetGameStore } from './testUtils';

vi.mock('../src/game/abilities/AbilityVfx', () => ({ spawnAbilityVfx: vi.fn() }));

const careers = [...ORDER_RACES, ...DESTRUCTION_RACES].flatMap((race) => CLASSES_BY_RACE[race]);

describe('ability progression', () => {
  beforeEach(() => {
    resetGameStore();
    vi.mocked(spawnAbilityVfx).mockClear();
  });

  test.each(careers)('%s has a usable three-ability starter kit and one unlock per later level', (career) => {
    const kit = getCareerAbilityKit(career);
    const starters = kit.abilities.filter((ability) => isAbilityUnlocked(ability, 1));
    expect(starters).toHaveLength(3);
    expect(starters.some((ability) => ability.effects.some((effect) => effect.kind === 'damage'))).toBe(true);
    expect(starters.some((ability) =>
      (ability.resource.careerBuild ?? 0) > 0 &&
      (ability.resource.careerCost ?? 0) === 0 &&
      (ability.resource.minCareer ?? 0) === 0 &&
      (ability.resource.manaCost ?? 0) === 0 &&
      ability.effects.some((effect) => effect.kind === 'damage') &&
      !ability.resource.spendAllCareer,
    )).toBe(true);
    expect(starters.every((ability) => ability.effects.length > 0 || (ability.resource.careerBuild ?? 0) > 0)).toBe(true);

    const firstUnlock = newlyUnlockedAbilities(career, 1, 2)[0];
    expect(
      firstUnlock.effects.length > 0 ||
      (firstUnlock.resource.careerBuild ?? 0) > (firstUnlock.resource.careerCost ?? 0),
      `${career} should learn a usable fourth ability`,
    ).toBe(true);

    for (let level = 2; level <= FULL_KIT_LEVEL; level++) {
      expect(newlyUnlockedAbilities(career, level - 1, level)).toHaveLength(1);
      expect(kit.abilities.filter((ability) => isAbilityUnlocked(ability, level))).toHaveLength(level + 2);
    }
    expect(newlyUnlockedAbilities(career, FULL_KIT_LEVEL, 50)).toEqual([]);
    expect(kit.abilities.map((ability) => ability.key)).toEqual([...HOTBAR_KEYS]);
    expect(kit.abilities.map((ability) => ability.slot)).toEqual([...Array(10).keys()]);
  });

  test('uses the same level policy for legacy class names and multi-level rewards', () => {
    for (const [legacy, career] of Object.entries(CLASS_RENAMES)) {
      expect(newlyUnlockedAbilities(legacy, 1, 8)).toEqual(newlyUnlockedAbilities(career, 1, 8));
    }
    expect(newlyUnlockedAbilities('Sunfire Templar', 0, 1).map((ability) => ability.name)).toEqual([
      'Sunbrand Strike', 'Radiant Counter', 'Heavenrend Sweep',
    ]);
    expect(newlyUnlockedAbilities('Sunfire Templar', 1, 4).map(abilityUnlockLevel)).toEqual([2, 3, 4]);
    expect(newlyUnlockedAbilities('Sunfire Templar', 4, 2)).toEqual([]);
    const ability = getCareerAbilityKit('Sunfire Templar').abilities[3];
    expect(isAbilityUnlocked(ability, 0)).toBe(false);
    expect(isAbilityUnlocked(ability, Number.NaN)).toBe(false);
  });

  test('keeps established tank and healer unlock ordering as utility effects become functional', () => {
    expect(newlyUnlockedAbilities('Sunfire Templar', 1, 4).map((ability) => ability.name)).toEqual([
      'Rallying Rebuke', 'Banner Rush', 'Daybreak Standard',
    ]);
    expect(newlyUnlockedAbilities('Sunfire Templar', 4, 8).map((ability) => ability.name)).toEqual([
      'Solar Edict', 'Bastion Edict', 'Pursuit Edict', 'Shield of Noon',
    ]);
    expect(newlyUnlockedAbilities('Battle Prelate', 1, 5).map((ability) => ability.name)).toEqual([
      'Penance Step', 'Reliquary Smash', 'Judgment of Ash', 'Last Homily',
    ]);
    expect(newlyUnlockedAbilities('Battle Prelate', 5, 8).map((ability) => ability.name)).toEqual([
      "Martyr's Ward", 'Hymn of Resolve', 'Icon of Wrath',
    ]);
  });

  test.each(careers)('%s rejects locked runtime activations without side effects and permits them at their unlock level', (career) => {
    const kit = getCareerAbilityKit(career);
    for (const ability of kit.abilities.filter((entry) => !isAbilityUnlocked(entry, 1))) {
      resetGameStore();
      const player = makePlayer();
      useGameStore.getState().setCharacter(makeCharacter({ className: career, level: 1, mana: 100 }));
      useGameStore.getState().setAbilityResource({ ...createAbilityResourceState(career), current: kit.resource.max });
      const enemy = makeEnemy({ position: { x: 0, y: 0, z: 1 } });
      useGameStore.getState().setEnemies([enemy]);
      useGameStore.getState().setTarget(enemy.id);
      const context = { slot: ability.slot, player, now: 1000, vfx: null, getEnemyObject, movePlayer: () => true };
      const before = useGameStore.getState();
      const vfxCalls = vi.mocked(spawnAbilityVfx).mock.calls.length;

      expect(getAbilityActivationFailure(context)).toMatchObject({
        code: 'locked_ability',
        message: `${ability.name} unlocks at level ${abilityUnlockLevel(ability)}.`,
      });
      expect(tryActivateAbility(context)).toBeNull();
      expect(useGameStore.getState().character).toEqual(before.character);
      expect(useGameStore.getState().abilityResource).toEqual(before.abilityResource);
      expect(useGameStore.getState().hotbarCooldowns).toEqual(before.hotbarCooldowns);
      expect(player.animator?.playAction).not.toHaveBeenCalled();
      expect(vi.mocked(spawnAbilityVfx)).toHaveBeenCalledTimes(vfxCalls);

      useGameStore.getState().updateCharacter({ level: abilityUnlockLevel(ability) });
      if (ability.unavailableReason) {
        expect(getAbilityActivationFailure(context)?.code).toBe('unavailable_ability');
        expect(tryActivateAbility(context)).toBeNull();
      } else expect(tryActivateAbility(context)?.ability).toBe(ability);
    }
  });

  test.each(careers)('%s can deal damage and build resource from empty at level one', (career) => {
    const kit = getCareerAbilityKit(career);
    const builder = kit.abilities.find((ability) =>
      isAbilityUnlocked(ability, 1) &&
      (ability.resource.careerBuild ?? 0) > 0 &&
      ability.effects.some((effect) => effect.kind === 'damage'),
    )!;
    useGameStore.getState().setCharacter(makeCharacter({ className: career, level: 1, mana: 0 }));
    useGameStore.getState().setAbilityResource({ ...createAbilityResourceState(career), current: 0 });
    const enemy = makeEnemy({ position: { x: 0, y: 0, z: 1 } });
    useGameStore.getState().setEnemies([enemy]);
    useGameStore.getState().setTarget(enemy.id);

    const combat = new Combat();
    expect(combat.tryAbility(builder.slot, makePlayer(), 1000)).toBe(true);
    combat.tickAbilityImpacts(5000);
    expect(useGameStore.getState().enemies[0].health).toBeLessThan(enemy.health);
    expect(useGameStore.getState().abilityResource?.current).toBeGreaterThan(0);
    expect(useGameStore.getState().character?.mana).toBe(0);
  });
});
