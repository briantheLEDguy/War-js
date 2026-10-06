import type { ScenarioCharacter } from './types';

/** Trusted-host document envelope shared by scenario transfer and live campaign recovery. */
export function validateScenarioCharacter(value: unknown): asserts value is ScenarioCharacter {
  const character = value as ScenarioCharacter;
  if (!character || typeof character.id !== 'string' || !/^[a-zA-Z0-9_-]{1,80}$/.test(character.id)
    || ['__proto__', 'constructor', 'prototype'].includes(character.id) || !['aegis', 'riftbound'].includes(character.realm)
    || typeof character.name !== 'string' || !character.name.trim() || character.name.length > 64
    || typeof character.visual !== 'string' || !character.visual.startsWith('/Game/')
    || typeof character.returnMap !== 'string' || !character.returnMap.startsWith('/Game/')
    || !Array.isArray(character.returnPosition) || character.returnPosition.length !== 3 || !character.returnPosition.every(Number.isFinite)
    || !character.document || typeof character.document !== 'object' || Array.isArray(character.document))
    throw new Error('Invalid trusted character snapshot.');
}
