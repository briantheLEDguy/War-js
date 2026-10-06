import type { ScenarioCharacter } from '../scenarios/types';
import { validateScenarioCharacter } from '../scenarios/character';
import { validateNativeRuntime,nativeUtf8ByteLength } from './runtime';

export const NATIVE_CHARACTER_DOCUMENT_LIMIT = 262_144;
export interface NativeCampaignCharacterCheckpoint {
  version: 1;
  characterId: string;
  hostId: string;
  activationId: string;
  realm: 'aegis' | 'riftbound';
  scope: 'participant' | 'evacuation';
  revision: number;
  savedAt: number;
  siegeSequence: number;
  recoveryPending: boolean;
  returned: boolean;
  respawnPending: boolean;
  /** Optional on historical checkpoints; zero means no native mutation WAL has been replayed. */
  walSequence?: number;
  walBaseRevision?: number;
  character: ScenarioCharacter;
}
export interface NativeCampaignCharacterAck {
  version: 1;
  characterId: string;
  revision: number;
  recoveryPending: boolean;
  respawnPending: boolean;
  walSequence?: number;
}
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
/** Preserve the exact native inventory/runtime document, including defeat and transaction receipts. */
export function validateNativeCampaignCharacter(value: unknown): asserts value is ScenarioCharacter {
  validateScenarioCharacter(value);
  const { inventory, runtime, zone } = value.document;
  if (!object(inventory) || !object(runtime) || typeof zone !== 'string' || !zone
    || typeof runtime.health !== 'number' || !Number.isFinite(runtime.health) || runtime.health < 0
    || typeof runtime.mana !== 'number' || !Number.isFinite(runtime.mana) || runtime.mana < 0
    || (runtime.dead !== undefined && typeof runtime.dead !== 'boolean')
    || JSON.stringify(value).length > NATIVE_CHARACTER_DOCUMENT_LIMIT
    || runtime.version===2 && nativeUtf8ByteLength(JSON.stringify(value)) > NATIVE_CHARACTER_DOCUMENT_LIMIT)
    throw new Error('Invalid or oversized native character state.');
  validateNativeRuntime(runtime);
}
export function validateNativeCharacterCheckpoint(value: unknown): asserts value is NativeCampaignCharacterCheckpoint {
  const c = value as NativeCampaignCharacterCheckpoint;
  if (!c || c.version !== 1 || typeof c.hostId !== 'string' || !c.hostId || typeof c.activationId !== 'string' || !c.activationId
    || !['participant', 'evacuation'].includes(c.scope) || !Number.isSafeInteger(c.revision) || c.revision < 1
    || !Number.isSafeInteger(c.siegeSequence) || c.siegeSequence < 0 || !Number.isFinite(c.savedAt) || c.savedAt < 0
    || typeof c.recoveryPending !== 'boolean' || typeof c.returned !== 'boolean' || typeof c.respawnPending !== 'boolean'
    || (c.walSequence !== undefined && (!Number.isSafeInteger(c.walSequence) || c.walSequence < 0))
    || (c.walBaseRevision !== undefined && (!Number.isSafeInteger(c.walBaseRevision) || c.walBaseRevision < 1
      || c.walBaseRevision >= c.revision || !c.walSequence)))
    throw new Error('Invalid native character checkpoint.');
  validateNativeCampaignCharacter(c.character);
  if (c.characterId !== c.character.id || c.realm !== c.character.realm) throw new Error('Native character checkpoint identity differs.');
  const runtime = c.character.document.runtime as Record<string, unknown>;
  if (c.respawnPending !== (runtime.dead === true || runtime.health === 0)) throw new Error('Native character checkpoint defeat intent differs.');
}
export function validateNativeCharacterAck(value: unknown): asserts value is NativeCampaignCharacterAck {
  const ack = value as NativeCampaignCharacterAck;
  if (!ack || ack.version !== 1 || typeof ack.characterId !== 'string' || !ack.characterId || !Number.isSafeInteger(ack.revision)
    || ack.revision < 1 || typeof ack.recoveryPending !== 'boolean' || typeof ack.respawnPending !== 'boolean'
    || (ack.walSequence !== undefined && (!Number.isSafeInteger(ack.walSequence) || ack.walSequence < 0)))
    throw new Error('Invalid native character acknowledgement.');
}
