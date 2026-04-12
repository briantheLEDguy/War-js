import type {
  CharacterService,
  CharacterState,
  CharacterSummary,
} from '../types';

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
    className: 'Warrior Priest',
    race: 'empire',
    level: 5,
    xp: 320,
    zoneId: 'altdorf',
    health: 180,
    maxHealth: 180,
    mana: 60,
    maxMana: 60,
    position: { x: 0, y: 0, z: 120 },
    rotationY: Math.PI,
  },
  'char-grik': {
    id: 'char-grik',
    name: 'Grik',
    className: 'Shaman',
    race: 'greenskin',
    level: 4,
    xp: 110,
    zoneId: 'inevitable_city',
    health: 120,
    maxHealth: 120,
    mana: 160,
    maxMana: 160,
    position: { x: 0, y: 0, z: 0 },
    rotationY: 0,
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
        Object.assign(this.store, saved);
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
    const id = `char-${crypto.randomUUID()}`;
    const startZone = defaultZoneForRace(data.race);
    const full: CharacterState = {
      id,
      name: data.name,
      className: data.className,
      race: data.race,
      level: 1,
      xp: 0,
      zoneId: startZone,
      health: 100,
      maxHealth: 100,
      mana: 100,
      maxMana: 100,
      position: { x: 0, y: 0, z: 120 },
      rotationY: Math.PI,
    };
    this.store[id] = full;
    this.persist();
    return toSummary(full);
  }

  async load(characterId: string): Promise<CharacterState> {
    const c = this.store[characterId];
    if (!c) throw new Error(`Character not found: ${characterId}`);
    return { ...c };
  }

  async save(characterId: string, state: Partial<CharacterState>): Promise<void> {
    const c = this.store[characterId];
    if (!c) return;
    this.store[characterId] = { ...c, ...state };
    this.persist();
  }
}

function toSummary(c: CharacterState): CharacterSummary {
  return {
    id: c.id,
    name: c.name,
    className: c.className,
    race: c.race,
    level: c.level,
    zoneId: c.zoneId,
  };
}
