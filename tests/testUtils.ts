import * as THREE from 'three';
import { vi } from 'vitest';
import type { Mock } from 'vitest';
import type { CharacterState, Vec3 } from '../src/services/types';
import { HOTBAR_SLOT_COUNT } from '../src/game/abilities/abilityData';
import type { Player } from '../src/game/Player';
import type { VfxLayer } from '../src/game/animation/VfxLayer';
import { useGameStore, type EnemyState } from '../src/state/gameStore';

export interface MockPlayer {
  object: THREE.Object3D;
  position: Vec3;
  rotationY: number;
  animator: { playAction: Mock };
  playGlbAction: Mock;
  playAbilityWeaponAction: Mock;
}

export interface MockVfxLayer {
  spawn: Mock;
}

export function resetGameStore(): void {
  useGameStore.getState().setCharacter(null);
  useGameStore.setState({
    enemies: [],
    targetId: null,
    floatingDamage: [],
    playerStatusEffects: [],
    abilityResource: null,
    hotbarCooldowns: Array.from({ length: HOTBAR_SLOT_COUNT }, () => 0),
    pendingTouchAbility: null,
    contextPrompt: null,
    abilityFeedback: null,
  });
}

export function makeCharacter(overrides: Partial<CharacterState> = {}): CharacterState {
  return {
    id: 'char-test',
    name: 'Test Character',
    className: 'Battle Prelate',
    race: 'empire',
    bodyVariant: 'm',
    level: 5,
    zoneId: 'aegis_capital',
    xp: 0,
    health: 120,
    maxHealth: 180,
    mana: 60,
    maxMana: 60,
    strength: 14,
    gold: 0,
    position: { x: 0, y: 0, z: 0 },
    rotationY: 0,
    ...overrides,
  };
}

export function makeEnemy(overrides: Partial<EnemyState> = {}): EnemyState {
  return {
    id: 'enemy-test',
    name: 'Training Dummy',
    level: 1,
    health: 100,
    maxHealth: 100,
    position: { x: 0, y: 0, z: 2 },
    alive: true,
    ...overrides,
  };
}

export function makePlayer(overrides: Partial<MockPlayer> = {}): Player {
  const object = new THREE.Object3D();
  const position = overrides.position ?? { x: 0, y: 0, z: 0 };
  object.position.set(position.x, position.y, position.z);
  return {
    object,
    position,
    rotationY: 0,
    animator: { playAction: vi.fn() },
    playGlbAction: vi.fn(),
    playAbilityWeaponAction: vi.fn(),
    ...overrides,
  } as unknown as Player;
}

export function makeVfxLayer(): VfxLayer {
  return {
    spawn: vi.fn(),
  } as unknown as VfxLayer;
}

export function getEnemyObject(): THREE.Object3D {
  const object = new THREE.Object3D();
  object.position.set(0, 0, 2);
  return object;
}
