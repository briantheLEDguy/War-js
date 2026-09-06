export type WorldLifeActorKind = 'citizen' | 'guard' | 'deer' | 'bird';
export type WorldLifeEmitterKind = 'smoke' | 'embers' | 'motes';

export interface WorldLifeActorSpawn {
  id: string;
  kind: WorldLifeActorKind;
  x: number;
  z: number;
  /** Authored, unobstructed loop from the spawn through these points and back. */
  route?: Array<{ x: number; z: number }>;
  speed?: number;
  pauseSeconds?: number;
  scale?: number;
  variant?: number;
}

export interface WorldLifeEmitterSpawn {
  id: string;
  kind: WorldLifeEmitterKind;
  x: number;
  z: number;
  /** Height above the terrain. */
  y?: number;
  count?: number;
  radius?: number;
}

/** Cosmetic population is separate from quest NPCs, combat and persistence. */
export interface WorldLifeDefinition {
  actors: WorldLifeActorSpawn[];
  emitters: WorldLifeEmitterSpawn[];
}
