import type { CSSProperties } from 'react';
import {
  abilityHasEnoughResources,
  getCareerAbilityKit,
} from '../../game/abilities/abilityData';
import { useGameStore } from '../../state/gameStore';
import { AbilityIcon } from './AbilityIcon';

function activateSlot(slot: number) {
  useGameStore.getState().setPendingTouchAbility(slot);
}

export function Hotbar() {
  const cooldowns = useGameStore((s) => s.hotbarCooldowns);
  const character = useGameStore((s) => s.character);
  const abilityResource = useGameStore((s) => s.abilityResource);
  const kit = getCareerAbilityKit(character?.className);

  return (
    <div className="hotbar">
      {kit.abilities.map((ability) => {
        const cd = cooldowns[ability.slot] ?? 0;
        const canPay = abilityHasEnoughResources(
          ability,
          character?.mana ?? 0,
          abilityResource,
        );
        const school = ability.effects[0]?.school ?? 'physical';
        const costParts = [
          ability.resource.manaCost ? `${ability.resource.manaCost} mana` : null,
          ability.resource.careerCost ? `${ability.resource.careerCost} ${kit.resource.label}` : null,
          ability.resource.spendAllCareer ? `all ${kit.resource.label}` : null,
          ability.resource.careerBuild ? `builds ${ability.resource.careerBuild} ${kit.resource.label}` : null,
        ].filter(Boolean);
        const tooltip = `${ability.key}. ${ability.name} - ${ability.summary}${costParts.length ? ` (${costParts.join(', ')})` : ''}`;
        const colors = ability.visual.vfx.colors;
        const colorStyle = {
          '--ability-primary': colors.primary,
          '--ability-secondary': colors.secondary,
          '--ability-accent': colors.accent,
          '--ability-shadow': colors.shadow,
          '--ability-glow': colors.glow,
        } as CSSProperties;

        return (
          <button
            key={ability.id}
            className={`hotbar-slot school-${school}${!canPay && cd <= 0 ? ' no-mana' : ''}`}
            title={tooltip}
            type="button"
            style={colorStyle}
            onClick={() => activateSlot(ability.slot)}
          >
            <span className="ability-icon">
              <AbilityIcon ability={ability} />
            </span>
            <span className="key">{ability.key}</span>
            {cd > 0 && <span className="cd-overlay">{cd.toFixed(1)}</span>}
          </button>
        );
      })}
    </div>
  );
}
