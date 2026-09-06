import { normalizeClassName } from '../../data/careers';
import { novitiateArmorEquipment } from '../../data/novitiateArmor';
import type { CharacterState } from '../../services/types';

export type ArmorPreviewMode = 'current' | 'novitiate';

export function supportsNovitiatePreview(character: CharacterState | null): boolean {
  return character?.race === 'empire' && character.bodyVariant === 'm'
    && normalizeClassName(character.className) === 'Battle Prelate';
}

/** Player receives an isolated preview copy, never the persisted loadout. */
export function characterForArmorPreview(character: CharacterState, mode: ArmorPreviewMode): CharacterState {
  const preview = structuredClone(character);
  if (mode === 'novitiate' && supportsNovitiatePreview(character)) {
    preview.equipment = { ...preview.equipment, ...novitiateArmorEquipment() };
  }
  return preview;
}
