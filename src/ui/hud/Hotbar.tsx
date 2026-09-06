import type { CSSProperties } from 'react';
import {
  abilityHasEnoughResources,
  getCareerAbilityKit,
} from '../../game/abilities/abilityData';
import { abilityUnlockLevel, isAbilityUnlocked } from '../../game/abilities/abilityProgression';
import { useGameStore } from '../../state/gameStore';
import { AbilityIcon } from './AbilityIcon';

function activateSlot(slot: number) {
  useGameStore.getState().setPendingTouchAbility(slot);
}

export function Hotbar() {
  const cooldowns = useGameStore((s) => s.hotbarCooldowns);
  const character = useGameStore((s) => s.character);
  const abilityResource = useGameStore((s) => s.abilityResource);
  const globalCooldownUntil = useGameStore((s) => s.globalCooldownUntil);
  const kit = getCareerAbilityKit(character?.className);

  return (
    <div className="hotbar">
      {kit.abilities.map((ability) => {
        const unlockLevel = abilityUnlockLevel(ability);
        const unlocked = isAbilityUnlocked(ability, character?.level ?? 0);
        const available = !ability.unavailableReason;
        const cd = cooldowns[ability.slot] ?? 0;
        const recovery = ability.gcdSec > 0 ? Math.max(0, (globalCooldownUntil - performance.now()) / 1000) : 0;
        const displayedCooldown = Math.max(cd, recovery);
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
        const tooltip = `${ability.key}. ${ability.name}${unlocked ? '' : ` — Unlocks at level ${unlockLevel}`} - ${ability.unavailableReason ?? ability.summary}${costParts.length && available ? ` (${costParts.join(', ')})` : ''}`;
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
            className={`hotbar-slot school-${school}${!unlocked || !available ? ' locked' : !canPay && cd <= 0 ? ' no-mana' : ''}`}
            title={tooltip}
            aria-label={tooltip}
            aria-disabled={!unlocked || !available}
            type="button"
            style={colorStyle}
            onClick={() => { if (unlocked && available) activateSlot(ability.slot); }}
          >
            <span className="ability-icon">
              <AbilityIcon ability={ability} />
            </span>
            <span className="key">{ability.key}</span>
            {!unlocked && <span className="ability-unlock-level">Lv {unlockLevel}</span>}
            {unlocked && !available && <span className="ability-unlock-level">Planned</span>}
            {unlocked && available && displayedCooldown > 0 && <span className="cd-overlay">{displayedCooldown.toFixed(1)}</span>}
          </button>
        );
      })}
    </div>
  );
}
