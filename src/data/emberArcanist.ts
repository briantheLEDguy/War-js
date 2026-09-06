import { normalizeClassName } from './careers';

export const EMBER_STAFF_KEY = 'weapon_ember_brazier_staff';
export const EMBER_STAFF_MODEL = 'wep_civic_ember_arcanist_ember_staff.glb';

/** This fitted outfit is currently authored for the male Empire profile only. */
export function hasEmberArcanistOutfit(race: string, className: string, bodyVariant?: string): boolean {
  return race === 'empire' && normalizeClassName(className) === 'Ember Arcanist' && bodyVariant !== 'f';
}
