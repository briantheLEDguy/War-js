import type {
  CharacterService,
  CharacterState,
  CharacterSummary,
  EquipmentEntry,
  EquipmentState,
} from '../types';
import { normalizeClassName } from '../../data/careers';
import { normalizeBodyVariant, starterArmorEquipmentFor } from '../../data/playableAssets.generated';
import {
  defaultZoneForRace,
  defaultZoneSpawnPoint,
  normalizePlayableZoneId,
  zoneWasNormalized,
} from '../../data/zoneRouting';
import { createLocalId } from './id';

const PREBUILT: Record<string, CharacterState> = {
  'char-sigmund': {
    id: 'char-sigmund',
    name: 'Sigmund',
    className: 'Battle Prelate',
    race: 'empire',
    bodyVariant: 'm',
    level: 5,
    xp: 320,
    zoneId: 'aegis_capital',
    health: 180,
    maxHealth: 180,
    mana: 60,
    maxMana: 60,
    strength: 14,
    gold: 25,
    position: { x: -20, y: 0, z: 31 },
    rotationY: Math.PI,
    equipment: defaultEquipmentFor('empire', 'Battle Prelate', 'm'),
  },
  'char-grik': {
    id: 'char-grik',
    name: 'Grik',
    className: 'Bog Hexer',
    race: 'greenskin',
    bodyVariant: 'm',
    level: 4,
    xp: 110,
    zoneId: 'riftspire_capital',
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
    const className = normalizeClassName(data.className);
    const bodyVariant = normalizeBodyVariant(data.bodyVariant);
    const full: CharacterState = {
      id,
      name: data.name,
      className,
      race: data.race,
      bodyVariant,
      level: 1,
      xp: 0,
      zoneId: startZone,
      health: 100,
      maxHealth: 100,
      mana: 100,
      maxMana: 100,
      strength: 10,
      gold: 0,
      position: { x: 0, y: 0, z: -40 },
      rotationY: Math.PI,
      equipment: defaultEquipmentFor(data.race, className, bodyVariant),
    };
    this.store[id] = full;
    this.persist();
    return toSummary(full);
  }

  async load(characterId: string): Promise<CharacterState> {
    const c = this.store[characterId];
    if (!c) throw new Error(`Character not found: ${characterId}`);
    const normalized = normalizeCharacterState(c);
    if (normalized.zoneId !== c.zoneId) {
      this.store[characterId] = normalized;
      this.persist();
    }
    // Backfill fields added after this character was first saved so older
    // localStorage payloads still load cleanly with sensible defaults.
    return normalized;
  }

  async save(characterId: string, state: Partial<CharacterState>): Promise<void> {
    const c = this.store[characterId];
    if (!c) return;
    this.store[characterId] = normalizeCharacterState({
      ...c,
      ...state,
      className: normalizeClassName(state.className ?? c.className),
      bodyVariant: normalizeBodyVariant(state.bodyVariant ?? c.bodyVariant),
    });
    this.persist();
  }

  async findByName(name: string): Promise<CharacterState[]> {
    const needle = normalizeLookupName(name);
    if (!needle) return [];
    return Object.values(this.store)
      .map(normalizeCharacterState)
      .filter((character) => normalizeLookupName(character.name) === needle);
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
  const zoneId = normalizePlayableZoneId(c.zoneId, c.race);
  return {
    ...c,
    className: normalizeClassName(c.className),
    bodyVariant: normalizeBodyVariant(c.bodyVariant),
    zoneId,
    position: zoneWasNormalized(c.zoneId, zoneId) ? defaultZoneSpawnPoint(zoneId) : c.position,
    strength: c.strength ?? 10,
    gold: c.gold ?? 0,
    equipment: equipmentOrStarter(c),
  };
}

function equipmentOrStarter(c: CharacterState): CharacterState['equipment'] {
  const className = normalizeClassName(c.className);
  const bodyVariant = normalizeBodyVariant(c.bodyVariant);
  if (!c.equipment || Object.keys(c.equipment).length === 0) {
    return defaultEquipmentFor(c.race, className, bodyVariant);
  }
  if (isBattlePrelate(c.race, className) && shouldResetBattlePrelateEquipment(c.equipment)) {
    return defaultEquipmentFor(c.race, className, bodyVariant);
  }
  return c.equipment;
}

const LEGACY_BATTLE_PRELATE_EQUIPMENT_KEYS = new Set([
  'base_male_blackened_chest',
  'base_male_blackened_shoulders',
  'base_male_blackened_bracers',
  'base_male_blackened_belt',
  'base_male_blackened_legs',
  'base_male_blackened_boots',
  'base_male_oath_tabard',
  'base_male_crimson_cape',
]);

function defaultEquipmentFor(
  race: CharacterSummary['race'],
  className: string,
  bodyVariant: CharacterSummary['bodyVariant'],
): EquipmentState {
  const equipment = starterArmorEquipmentFor(race, className, bodyVariant);
  if (isBattlePrelate(race, className)) {
    equipment.mainHand = 'weapon_hammer_reliquary_2h';
    delete equipment.offHand;
  }
  return equipment;
}

function shouldResetBattlePrelateEquipment(equipment: EquipmentState): boolean {
  const keys = Object.values(equipment)
    .map(equipmentKey)
    .filter((key): key is string => Boolean(key));
  return (
    keys.some((key) => LEGACY_BATTLE_PRELATE_EQUIPMENT_KEYS.has(key)) ||
    equipmentKey(equipment.mainHand) === 'sword_iron' ||
    equipmentKey(equipment.offHand) === 'shield_wood' ||
    !equipment.mainHand
  );
}

function equipmentKey(entry: EquipmentEntry | undefined): string | null {
  if (!entry) return null;
  return typeof entry === 'string' ? entry : entry.key;
}

function isBattlePrelate(race: CharacterSummary['race'], className: string): boolean {
  return race === 'empire' && normalizeClassName(className) === 'Battle Prelate';
}

function normalizeLookupName(name: string | null | undefined): string {
  return name?.trim().toLowerCase() ?? '';
}
