import * as THREE from 'three';
import { useGameStore, type EnemyState } from '../../state/gameStore';
import type { Player } from '../Player';
import type { VfxLayer } from '../animation/VfxLayer';
import {
  createAbilityResourceState,
  getAbilityForCareer,
  getCareerAbilityKit,
  type AbilityResourceState,
} from './abilityData';
import { spawnAbilityVfx } from './AbilityVfx';
import type { AbilityDefinition, AbilityEffect } from './types';

export interface PendingAbilityImpact {
  id: string;
  dueAt: number;
  ability: AbilityDefinition;
  effects: AbilityEffect[];
  targetId: string | null;
  center: { x: number; y: number; z: number };
  sourcePosition: { x: number; y: number; z: number };
  sourceRotationY: number;
  sourceStrength: number;
  sourceLevel: number;
  resourceSpent: number;
}

export interface AbilityActivationContext {
  slot: number;
  player: Player;
  now: number;
  vfx: VfxLayer | null;
  getEnemyObject: (id: string) => THREE.Object3D | null;
}

export interface AbilityActivationResult {
  ability: AbilityDefinition;
  impacts: PendingAbilityImpact[];
}

export type AbilityFailureReasonCode =
  | 'dead_player'
  | 'blocked_ui'
  | 'no_character'
  | 'unknown_ability'
  | 'cooldown'
  | 'insufficient_mana'
  | 'insufficient_resource'
  | 'no_target'
  | 'out_of_range';

export interface AbilityFailureReason {
  code: AbilityFailureReasonCode;
  message: string;
  ability?: AbilityDefinition;
}

export interface AbilityActivationBlockers {
  playerDead?: boolean;
  uiBlocked?: boolean;
  uiBlockedMessage?: string;
}

export function tryActivateAbility(
  context: AbilityActivationContext,
): AbilityActivationResult | null {
  if (getAbilityActivationFailure(context)) return null;

  const store = useGameStore.getState();
  const character = store.character!;
  const ability = getAbilityForCareer(character.className, context.slot)!;

  const kit = getCareerAbilityKit(character.className);
  const resource = store.abilityResource?.key === kit.resource.key
    ? store.abilityResource
    : createAbilityResourceState(character.className);

  const target = resolveTarget(ability, context.player, store.enemies, store.targetId);

  const releaseSec = releaseTimeSec(ability);
  const flightSec = target ? projectileFlightSec(ability, context.player, target) : 0;
  const resourceSpent = ability.resource.spendAllCareer
    ? resource.current
    : ability.resource.careerCost ?? 0;

  const nextMana = Math.max(0, character.mana - (ability.resource.manaCost ?? 0));
  const nextResource = ability.resource.spendAllCareer
    ? ability.resource.careerBuild ?? 0
    : resource.current - (ability.resource.careerCost ?? 0) + (ability.resource.careerBuild ?? 0);

  store.updateCharacter({ mana: nextMana });
  store.setAbilityResource({
    ...resource,
    current: clamp(nextResource, 0, resource.max),
  });
  store.setHotbarCooldown(ability.slot, ability.cooldownSec);

  playAbilityAnimation(context.player, ability, target);
  try {
    spawnAbilityVfx(
      context.vfx,
      ability,
      {
        source: context.player.object,
        targetObject: target ? context.getEnemyObject(target.id) : null,
        targetPosition: target?.position ?? context.player.position,
      },
      releaseSec,
      flightSec,
    );
  } catch (err) {
    console.error('Ability VFX spawn failed for', ability.id, err);
  }

  const impacts = ability.effects.length > 0
    ? [makeImpact(context, ability, target, releaseSec + flightSec, resourceSpent)]
    : [];

  return { ability, impacts };
}

export function getAbilityActivationFailure(
  context: AbilityActivationContext,
  blockers: AbilityActivationBlockers = {},
): AbilityFailureReason | null {
  const store = useGameStore.getState();
  if (blockers.playerDead) {
    return { code: 'dead_player', message: 'You are dead.' };
  }
  if (blockers.uiBlocked) {
    return {
      code: 'blocked_ui',
      message: blockers.uiBlockedMessage ?? 'Close the current panel to use abilities.',
    };
  }

  const character = store.character;
  if (!character) {
    return { code: 'no_character', message: 'No character is active.' };
  }
  if (store.playerDead) {
    return { code: 'dead_player', message: 'You cannot use abilities while defeated.' };
  }

  const ability = getAbilityForCareer(character.className, context.slot);
  if (!ability) {
    return { code: 'unknown_ability', message: 'No ability is assigned to that slot.' };
  }

  const cooldown = store.hotbarCooldowns[ability.slot] ?? 0;
  if (cooldown > 0) {
    return {
      code: 'cooldown',
      message: `${ability.name} is ready in ${formatCooldown(cooldown)}.`,
      ability,
    };
  }

  const kit = getCareerAbilityKit(character.className);
  const resource = store.abilityResource?.key === kit.resource.key
    ? store.abilityResource
    : createAbilityResourceState(character.className);

  const resourceFailure = resourceFailureForAbility(ability, character.mana, resource);
  if (resourceFailure) return { ...resourceFailure, ability };

  const targetFailure = targetFailureForAbility(
    ability,
    context.player,
    store.enemies,
    store.targetId,
  );
  if (targetFailure) return { ...targetFailure, ability };

  return null;
}

function resourceFailureForAbility(
  ability: AbilityDefinition,
  mana: number,
  resource: AbilityResourceState,
): AbilityFailureReason | null {
  const manaCost = ability.resource.manaCost ?? 0;
  if (mana < manaCost) {
    return { code: 'insufficient_mana', message: `Need ${manaCost} mana.` };
  }

  const requiredCareer = Math.max(
    ability.resource.minCareer ?? 0,
    ability.resource.careerCost ?? 0,
  );
  if (resource.current < requiredCareer) {
    return {
      code: 'insufficient_resource',
      message: `Need ${requiredCareer} ${resource.label}.`,
    };
  }

  return null;
}

function targetFailureForAbility(
  ability: AbilityDefinition,
  player: Player,
  enemies: EnemyState[],
  targetId: string | null,
): AbilityFailureReason | null {
  if (ability.targeting.target === 'self') return null;
  if (!targetId) return { code: 'no_target', message: 'Select a target.' };

  const target = enemies.find((enemy) => enemy.id === targetId);
  if (!target || !target.alive) {
    return { code: 'no_target', message: 'Select a living target.' };
  }

  if (dist2D(target.position, player.position) > ability.targeting.range) {
    return { code: 'out_of_range', message: `Move closer to ${target.name}.` };
  }

  return null;
}

function resolveTarget(
  ability: AbilityDefinition,
  player: Player,
  enemies: EnemyState[],
  targetId: string | null,
): EnemyState | null {
  if (ability.targeting.target === 'self') return null;
  if (!targetId) return null;
  const target = enemies.find((enemy) => enemy.id === targetId);
  if (!target || !target.alive) return null;
  if (dist2D(target.position, player.position) > ability.targeting.range) return null;
  return target;
}

function makeImpact(
  context: AbilityActivationContext,
  ability: AbilityDefinition,
  target: EnemyState | null,
  delaySec: number,
  resourceSpent: number,
): PendingAbilityImpact {
  const center = target?.position ?? context.player.position;
  const character = useGameStore.getState().character;
  return {
    id: `${ability.id}-${context.now}-${Math.random().toString(36).slice(2, 7)}`,
    dueAt: context.now + delaySec * 1000,
    ability,
    effects: ability.effects,
    targetId: target?.id ?? null,
    center: { x: center.x, y: center.y, z: center.z },
    sourcePosition: {
      x: context.player.position.x,
      y: context.player.position.y,
      z: context.player.position.z,
    },
    sourceRotationY: context.player.rotationY,
    sourceStrength: character?.strength ?? 10,
    sourceLevel: character?.level ?? 1,
    resourceSpent,
  };
}

function playAbilityAnimation(
  player: Player,
  ability: AbilityDefinition,
  target: EnemyState | null,
): void {
  if (player.animator) {
    player.animator.playAction(ability.animation.actionId, ability.animation.durationSec);
  } else {
    player.playGlbAction(ability.animation.actionId, ability.animation.durationSec);
  }
  player.playAbilityWeaponAction?.(ability, target?.position ?? null);
}

function releaseTimeSec(ability: AbilityDefinition): number {
  const release =
    ability.animation.notifyWindows.find((w) => w.name === 'release') ??
    ability.animation.notifyWindows.find((w) => w.name === 'active') ??
    ability.animation.notifyWindows[0];
  if (!release) return ability.animation.durationSec * 0.35;
  return ((release.start + release.end) / 2) * ability.animation.durationSec;
}

function projectileFlightSec(
  ability: AbilityDefinition,
  player: Player,
  target: EnemyState,
): number {
  const speed = ability.targeting.projectileSpeed;
  if (!speed) return 0;
  return Math.min(0.8, dist2D(player.position, target.position) / speed);
}

function dist2D(
  a: { x: number; z: number },
  b: { x: number; z: number },
): number {
  return Math.hypot(a.x - b.x, a.z - b.z);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function formatCooldown(seconds: number): string {
  return seconds < 1 ? '<1s' : `${Math.ceil(seconds)}s`;
}
