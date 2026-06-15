import { EQUIP_SLOT_LABELS, EQUIP_SLOT_ORDER } from '../../data/items';
import { BODY_VARIANT_DISPLAY } from '../../data/careers';
import {
  baseStrengthForCharacter,
  getEquippedGear,
  strengthFromEquipment,
} from '../../game/Equipment';
import { useGameStore } from '../../state/gameStore';
import { useDraggableWindow } from './useDraggableWindow';

const RACE_DISPLAY: Record<string, string> = {
  empire: 'Empire',
  dwarf: 'Dwarf',
  high_elf: 'High Elf',
  chaos: 'Chaos',
  greenskin: 'Greenskin',
  dark_elf: 'Dark Elf',
};

export function CharacterSheetPanel() {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>();
  const character = useGameStore((s) => s.character);
  const inventory = useGameStore((s) => s.inventory);
  const toggleCharacterSheet = useGameStore((s) => s.toggleCharacterSheet);

  if (!character) return null;

  const equipmentBonus = strengthFromEquipment(character.equipment, inventory);
  const baseStrength = baseStrengthForCharacter(character, inventory);

  return (
    <div ref={panelRef} className={`panel character-sheet${dragClassName}`} style={dragStyle}>
      <div className="character-sheet-header draggable-window-handle" {...dragHandleProps}>
        <div>
          <h2>Character</h2>
          <div className="character-sheet-name">{character.name}</div>
        </div>
        <button className="character-sheet-close" onClick={toggleCharacterSheet}>
          Close
        </button>
      </div>

      <div className="character-sheet-meta">
        Lv {character.level} {BODY_VARIANT_DISPLAY[character.bodyVariant ?? 'm']} {RACE_DISPLAY[character.race] ?? character.race} {character.className}
      </div>

      <div className="character-sheet-stats">
        <div>
          <span>Health</span>
          <strong>{character.health} / {character.maxHealth}</strong>
        </div>
        <div>
          <span>Mana</span>
          <strong>{character.mana} / {character.maxMana}</strong>
        </div>
        <div>
          <span>Strength</span>
          <strong>
            {character.strength}
            {equipmentBonus > 0 && (
              <em>{baseStrength} + {equipmentBonus}</em>
            )}
          </strong>
        </div>
        <div>
          <span>Gold</span>
          <strong>{character.gold}</strong>
        </div>
      </div>

      <div className="equipment-list">
        {EQUIP_SLOT_ORDER.map((slot) => {
          const gear = getEquippedGear(character, slot, inventory);
          return (
            <div key={slot} className={`equipment-row ${gear ? '' : 'empty'}`}>
              <div className="equipment-slot-label">{EQUIP_SLOT_LABELS[slot]}</div>
              <div className="equipment-icon">{gear?.icon ?? '\u25CB'}</div>
              <div className="equipment-details">
                <strong>{gear?.name ?? 'Empty'}</strong>
                {gear?.affix?.strengthBonus && (
                  <span>+{gear.affix.strengthBonus} Strength</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
