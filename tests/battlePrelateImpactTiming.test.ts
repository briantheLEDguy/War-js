import * as THREE from 'three';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { tryActivateAbility } from '../src/game/abilities/AbilityRuntime';
import { AbilityMotionSequence } from '../src/game/animation/battlePrelateProfile';
import { VfxLayer } from '../src/game/animation/VfxLayer';
import { useGameStore } from '../src/state/gameStore';
import { makeCharacter, makeEnemy, makePlayer, resetGameStore, getEnemyObject } from './testUtils';

beforeEach(() => {
  resetGameStore();
  useGameStore.getState().setCharacter(makeCharacter({ level: 40, mana: 100 }));
  useGameStore.getState().setAbilityResource({ key: 'zeal', label: 'Zeal', max: 100, current: 100 });
  const enemy = makeEnemy(); useGameStore.getState().setEnemies([enemy]); useGameStore.getState().setTarget(enemy.id);
});

describe('shared animation and impact timeline', () => {
  test.each([30, 60])('melee and beam VFX meet gameplay impact within a frame at %i FPS', (fps) => {
    for (const slot of [0, 5, 6]) {
      useGameStore.setState({ globalCooldownUntil: 0, hotbarCooldowns: Array(10).fill(0) });
      const vfx = new VfxLayer(new THREE.Scene());
      const spawn = vi.spyOn(vfx, 'spawn');
      const player = makePlayer();
      const sequence = new AbilityMotionSequence();
      player.resolveAbilityMotion = sequence.resolve.bind(sequence);
      const result = tryActivateAbility({ slot, player, now: 1000, vfx, getEnemyObject });
      expect(result).not.toBeNull();
      const due = (result!.impacts[0].dueAt - 1000) / 1000;
      const contacts = spawn.mock.calls.map(([effect]) => effect).filter((effect) => /ImpactBurst|ContactFlair|GroundPulse/.test(effect.constructor.name));
      expect(contacts.length).toBeGreaterThan(0);
      contacts.forEach((effect) => expect(effect.startDelay).toBeCloseTo(due, 8));
      let elapsed = 0;
      while (elapsed + 1 / fps < due - 1e-8) { vfx.update(1 / fps); elapsed += 1 / fps; }
      contacts.forEach((effect) => expect(effect.root?.visible).toBe(false));
      vfx.update(1 / fps); elapsed += 1 / fps;
      contacts.forEach((effect) => expect(effect.root?.visible).toBe(true));
      expect(Math.abs(elapsed - due)).toBeLessThanOrEqual(1 / fps + 1e-8);
      vfx.dispose();
    }
  });
  test('failed activation does not consume a combo variant; successful activations use one resolved motion', () => {
    const player = makePlayer();
    const sequence = new AbilityMotionSequence();
    player.resolveAbilityMotion = vi.fn(sequence.resolve.bind(sequence));
    useGameStore.getState().setTarget(null);
    expect(tryActivateAbility({ slot: 0, player, now: 1000, vfx: null, getEnemyObject })).toBeNull();
    expect(player.resolveAbilityMotion).not.toHaveBeenCalled();
    useGameStore.getState().setTarget('enemy-test');
    const first = tryActivateAbility({ slot: 0, player, now: 1000, vfx: null, getEnemyObject })!;
    useGameStore.setState({ globalCooldownUntil: 0, hotbarCooldowns: Array(10).fill(0) });
    const second = tryActivateAbility({ slot: 0, player, now: 2300, vfx: null, getEnemyObject })!;
    expect(first.ability.animation.clip).toBe('prelate_litany_a');
    expect(second.ability.animation.clip).toBe('prelate_litany_b');
    expect(second.impacts[0].ability).toBe(second.ability);
  });
});
