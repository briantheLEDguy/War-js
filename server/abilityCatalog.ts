import { CAREER_ABILITY_KITS, getCareerAbilityKit } from '../src/game/abilities/abilityData';
import type { AbilityRule, PlayerIdentity, Realm } from '../src/shared/orvr/protocol';

export function campaignAbilityRules(): AbilityRule[] {
  return Object.values(CAREER_ABILITY_KITS).flatMap(kit => kit.abilities.map(ability => ({
    id: ability.id, cooldownSeconds: ability.cooldownSec, range: ability.targeting.range,
    targeting: ability.targeting, effects: ability.effects, resource: ability.resource, gcdSeconds: ability.gcdSec,
    impactDelaySeconds: ability.animation.contactSec ?? (() => {
      const window = ability.animation.notifyWindows.find(entry => entry.name === 'release')
        ?? ability.animation.notifyWindows.find(entry => entry.name === 'active') ?? ability.animation.notifyWindows[0];
      return ability.animation.durationSec * (window ? (window.start + window.end) / 2 : .35);
    })(),
    ...(ability.targeting.shape === 'pet' || ability.targeting.shape === 'deployable' ? { unavailableReason: 'Persistent companions are not available in this campaign playtest.' } : {}),
  })));
}

/** Current network recruits use two explicit test careers; client-supplied power is never accepted. */
export function recruitCombatProfile(realm: Realm): Pick<PlayerIdentity, 'avatarProfileKey' | 'className' | 'abilityIds' | 'combatProfile'> {
  const className = realm === 'aegis' ? 'Battle Prelate' : 'Ruin Oracle';
  const kit = getCareerAbilityKit(className);
  return {
    className, avatarProfileKey: realm === 'aegis' ? 'civic_battle_prelate_m' : 'npc_riftspire_chaos',
    abilityIds: kit.abilities.slice(0, 4).map(ability => ability.id),
    combatProfile: { level: 1, strength: 10, maxHealth: 100, maxMana: 100, careerMax: kit.resource.max, careerInitial: kit.resource.initial },
  };
}
