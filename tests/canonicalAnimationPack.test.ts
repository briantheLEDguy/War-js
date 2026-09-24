import { describe, expect, test } from 'vitest';
import catalog from '../shared/game/animation/suppliedPresentationCatalog.json';
import { CAREER_ABILITY_KITS } from '../shared/game/abilities/abilityData';

describe('supplied animation presentation contract', () => {
  test('every supplied source has a reachable character state or ability', () => {
    expect(Object.keys(catalog.clips)).toHaveLength(44);
    const reachable = new Set<string>();
    for (const [profile, definition] of Object.entries(catalog.profiles)) {
      for (const role of Object.keys(definition.locomotion)) reachable.add(`${profile}:${role}`);
      for (const ability of definition.abilities) reachable.add(`${profile}:${ability.id}`);
    }
    for (const clip of Object.values(catalog.clips)) {
      expect(clip.sha256).toMatch(/^[a-f0-9]{64}$/);
      expect(clip.duration).toBeGreaterThan(0);
      expect(clip.fps).toBeGreaterThan(0);
      expect(clip.uses.length).toBeGreaterThan(0);
      expect(clip.uses.every(use => reachable.has(use))).toBe(true);
    }
  });
  test('all forty live abilities have explicit presentation recipes', () => {
    const abilities = Object.values(CAREER_ABILITY_KITS).flatMap(kit => kit.abilities);
    const ids = new Set(abilities.map(ability => ability.id));
    const recipes = Object.values(catalog.profiles).flatMap(profile => profile.abilities);
    expect(recipes).toHaveLength(40);
    expect(new Set(recipes.map(recipe => recipe.id)).size).toBe(40);
    for (const recipe of recipes) {
      expect(ids.has(recipe.id), recipe.id).toBe(true);
      expect(recipe.sources.every(source => source in catalog.clips)).toBe(true);
      expect(recipe.contactFraction).toBeGreaterThan(0);
      expect(recipe.contactFraction).toBeLessThan(1);
    }
  });
  test('hybrid invocations use magic and physical weapon attacks retain weapon motions', () => {
    const prelate = catalog.profiles.civic_battle_prelate_m;
    const strike = prelate.abilities.find(a => a.id.endsWith('.litany_of_strikes'))!;
    const heal = prelate.abilities.find(a => a.id.endsWith('.redemption_surge'))!;
    const smash = prelate.abilities.find(a => a.id.endsWith('.reliquary_smash'))!;
    expect(strike.sources).toEqual(['two.slash']);
    expect(heal.sources).toEqual(['spell.ritual']);
    expect(heal.equipment).toBe('stowed');
    expect(smash.sources).toEqual(['two.jump_attack', 'two.spin']);
    for (const ability of catalog.profiles.civic_ember_arcanist_m.abilities) {
      expect(ability.sources.every(source => source.startsWith('spell.'))).toBe(true);
    }
  });
});
