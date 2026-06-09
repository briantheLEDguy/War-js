import type {
  CharacterService,
  CharacterState,
  CharacterSummary,
} from '../types';
import { normalizeClassName } from '../../data/careers';
import { normalizeBodyVariant, starterArmorEquipmentFor } from '../../data/playableAssets.generated';
import { createLocalId } from './id';

/** Order races start in Altdorf; Destruction races in the Inevitable City. */
function defaultZoneForRace(race: CharacterState['race']): string {
  switch (race) {
    case 'empire':
    case 'dwarf':
    case 'high_elf':
      return 'altdorf';
    case 'chaos':
    case 'greenskin':
    case 'dark_elf':
      return 'inevitable_city';
    default:
      return 'altdorf';
  }
}

const PREBUILT: Record<string, CharacterState> = {
  'char-sigmund': {
    id: 'char-sigmund',
    name: 'Sigmund',
    className: 'Battle Prelate',
    race: 'empire',
    bodyVariant: 'm',
    level: 5,
    xp: 320,
    zoneId: 'altdorf',
    health: 180,
    maxHealth: 180,
    mana: 60,
    maxMana: 60,
    strength: 14,
    gold: 25,
    position: { x: -20, y: 0, z: 31 },
    rotationY: Math.PI,
    equipment: starterArmorEquipmentFor('empire', 'Battle Prelate', 'm'),
  },
  'char-grik': {
    id: 'char-grik',
    name: 'Grik',
    className: 'Bog Hexer',
    race: 'greenskin',
    bodyVariant: 'm',
    level: 4,
    xp: 110,
    zoneId: 'inevitable_city',
    health: 120,
    maxHealth: 120,
    mana: 160,
    maxMana: 160,
    strength: 10,
    gold: 12,
    position: { x: 0, y: 0, z: 0 },
    rotationY: 0,
    equipment: starterArmorEquipmentFor('greenskin', 'Bog Hexer', 'm'),
  },
};

const STORAGE_KEY = 'war-js:local-characters';

export class CharacterLocal implements CharacterService {
  private store: Record<string, CharacterState>;

  constructor() {
    this.store = { ...PREBUILT };
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved = JSON.parse(raw) as Record<string, CharacterState>;
        Object.assign(this.store, Object.fromEntries(
          Object.entries(saved).map(([id, state]) => [id, normalizeCharacterState(state)]),
        ));
        this.persist();
      }
    } catch {
      /* ignore */
    }
  }

  private persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.store));
    } catch {
      /* ignore */
    }
  }

  async list(_userId: string): Promise<CharacterSummary[]> {
    return Object.values(this.store).map(toSummary);
  }

  async create(
    _userId: string,
    data: Omit<CharacterSummary, 'id' | 'level' | 'zoneId'>,
  ): Promise<CharacterSummary> {
    const id = createLocalId('char');
    const startZone = defaultZoneForRace(data.race);
    const full: CharacterState = {
      id,
      name: data.name,
      className: normalizeClassName(data.className),
      race: data.race,
      bodyVariant: normalizeBodyVariant(data.bodyVariant),
      level: 1,
      xp: 0,
      zoneId: startZone,
      health: 100,
      maxHealth: 100,
      mana: 100,
      maxMana: 100,
      strength: 10,
      gold: 0,
      position: { x: -20, y: 0, z: 31 },
      rotationY: Math.PI,
      equipment: starterArmorEquipmentFor(data.race, data.className, data.bodyVariant),
    };
    this.store[id] = full;
    this.persist();
    return toSummary(full);
  }

  async load(characterId: string): Promise<CharacterState> {
    const c = this.store[characterId];
    if (!c) throw new Error(`Character not found: ${characterId}`);
    // Backfill fields added after this character was first saved so older
    // localStorage payloads still load cleanly with sensible defaults.
    return {
      ...c,
      className: normalizeClassName(c.className),
      bodyVariant: normalizeBodyVariant(c.bodyVariant),
      strength: c.strength ?? 10,
      gold: c.gold ?? 0,
      equipment: equipmentOrStarter(c),
    };
  }

  async save(characterId: string, state: Partial<CharacterState>): Promise<void> {
    const c = this.store[characterId];
    if (!c) return;
    this.store[characterId] = {
      ...c,
      ...state,
      className: normalizeClassName(state.className ?? c.className),
      bodyVariant: normalizeBodyVariant(state.bodyVariant ?? c.bodyVariant),
    };
    this.persist();
  }
}

function toSummary(c: CharacterState): CharacterSummary {
  return {
    id: c.id,
    name: c.name,
    className: normalizeClassName(c.className),
    race: c.race,
    bodyVariant: normalizeBodyVariant(c.bodyVariant),
    level: c.level,
    zoneId: c.zoneId,
  };
}

function normalizeCharacterState(c: CharacterState): CharacterState {
  return {
    ...c,
    className: normalizeClassName(c.className),
    bodyVariant: normalizeBodyVariant(c.bodyVariant),
    equipment: equipmentOrStarter(c),
  };
}

function equipmentOrStarter(c: CharacterState): CharacterState['equipment'] {
  return c.equipment && Object.keys(c.equipment).length > 0
    ? c.equipment
    : starterArmorEquipmentFor(c.race, c.className, c.bodyVariant);
}
