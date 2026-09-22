export type PlayableRace = 'empire' | 'dwarf' | 'high_elf' | 'chaos' | 'greenskin' | 'dark_elf';
export type BodyVariant = 'm' | 'f';

export const ORDER_RACES: PlayableRace[] = ['empire', 'dwarf', 'high_elf'];
export const DESTRUCTION_RACES: PlayableRace[] = ['chaos', 'greenskin', 'dark_elf'];
export const BODY_VARIANTS: BodyVariant[] = ['m', 'f'];

export const RACE_DISPLAY: Record<PlayableRace, string> = {
  empire: 'Empire',
  dwarf: 'Dwarf',
  high_elf: 'High Elf',
  chaos: 'Chaos',
  greenskin: 'Greenskin',
  dark_elf: 'Dark Elf',
};

export const BODY_VARIANT_DISPLAY: Record<BodyVariant, string> = {
  m: 'Male',
  f: 'Female',
};

export type PlayerRealm = 'aegis' | 'riftbound';

export function playerRealmForRace(race: PlayableRace): PlayerRealm {
  return ORDER_RACES.includes(race) ? 'aegis' : 'riftbound';
}

export const CLASS_RENAMES: Record<string, string> = {
  'Bright Wizard': 'Ember Arcanist',
  'Witch Hunter': 'Hex Inquisitor',
  'Knight of the Blazing Sun': 'Sunfire Templar',
  'Warrior Priest': 'Battle Prelate',
  Ironbreaker: 'Stoneguard',
  Slayer: 'Doomseeker',
  'Rune Priest': 'Glyphbinder',
  Engineer: 'Siegewright',
  Swordmaster: 'Blade Savant',
  'White Lion': 'Pride Warden',
  Archmage: 'Aether Sage',
  'Shadow Warrior': 'Veil Ranger',
  Chosen: 'Dreadsworn',
  Marauder: 'Warped Reaver',
  Magus: 'Void Magister',
  Zealot: 'Ruin Oracle',
  'Black Orc': 'Warbrute',
  'Squig Herder': 'Fang Herder',
  Shaman: 'Bog Hexer',
  Choppa: 'Cleaver',
  'Witch Elf': 'Blood Dancer',
  Blackguard: 'Dread Guard',
  Sorceress: 'Dusk Weaver',
  'Disciple of Khaine': 'Crimson Acolyte',
};

export const DEFAULT_CLASS_NAME = 'Battle Prelate';

export const CLASSES_BY_RACE: Record<PlayableRace, string[]> = {
  empire: ['Ember Arcanist', 'Hex Inquisitor', 'Sunfire Templar', 'Battle Prelate'],
  dwarf: ['Stoneguard', 'Doomseeker', 'Glyphbinder', 'Siegewright'],
  high_elf: ['Blade Savant', 'Pride Warden', 'Aether Sage', 'Veil Ranger'],
  chaos: ['Dreadsworn', 'Warped Reaver', 'Void Magister', 'Ruin Oracle'],
  greenskin: ['Warbrute', 'Fang Herder', 'Bog Hexer', 'Cleaver'],
  dark_elf: ['Blood Dancer', 'Dread Guard', 'Dusk Weaver', 'Crimson Acolyte'],
};

export function normalizeClassName(className: string | null | undefined): string {
  if (!className) return DEFAULT_CLASS_NAME;
  return CLASS_RENAMES[className] ?? className;
}
