import { describe, expect, it } from 'vitest';
import { CAREER_ABILITY_KITS } from '../shared/game/abilities/abilityData';
import { baselineWorkspace, effectiveAbility, writeNumeric } from '../shared/game/abilities/workshop/workspace';
import { validateWorkspace } from '../shared/game/abilities/workshop/validation';
import { buildContentManifest } from '../scripts/unreal/export-content';
import { composeCombatContent } from '../scripts/unreal/stage-combat-content';
import { canonicalJson, sha256 } from '../scripts/unreal/content-contract';

describe('fluid combat baseline and workshop compatibility', () => {
  const workspace = () => baselineWorkspace('a'.repeat(40), 'b'.repeat(64));
  it('gives every baseline ability an explicit movement policy and preserves short cooldowns', () => {
    const abilities = Object.values(CAREER_ABILITY_KITS).flatMap(kit => kit.abilities);
    expect(abilities.length).toBe(240);
    for (const ability of abilities) {
      expect(['free', 'stationary']).toContain(ability.movementPolicy);
      expect([.5, 1]).toContain(ability.gcdSec);
      if (ability.targeting.shape === 'melee' || ability.targeting.shape === 'dash') expect(ability.movementPolicy).toBe('free');
      if (ability.effects.some(effect => effect.kind === 'movement')) expect(ability.preparationScale).toBe(1);
    }
    const caster = CAREER_ABILITY_KITS['Ember Arcanist'].abilities;
    expect(caster.some(ability => ability.movementPolicy === 'stationary' && ability.preparationScale === .8)).toBe(true);
    const named = (name: string) => abilities.find(ability => ability.name === name)!;
    for (const name of ['Heavenrend Sweep', 'Reliquary Smash', 'Warding Arc', 'Spiral Guard', 'Sevenfold Kata', 'Hexbrand Cleave', 'Moonshot']) {
      expect(named(name).movementPolicy).toBe('free');
      expect(named(name).preparationScale).toBe(1);
    }
    for (const name of ['Blood Rite', 'Razor Prayer', 'Feast of the Shrine']) expect(named(name).movementPolicy).toBe('stationary');
    expect(named('Blood Rite').preparationScale).toBe(.8);
  });
  it('applies preparation tuning once to newly created workspaces without changing explicit timing', () => {
    const value = workspace();
    const spell = value.abilities.find(ability => ability.preparationScale === .8)!;
    expect(spell.timing.castSec).toBeCloseTo((spell.animation.contactSec ?? spell.animation.durationSec * .4) * .8);
    writeNumeric(spell, 'timing/castSec', 2.75);
    const assignment = value.assignments.find(row => row.abilityId === spell.id)!;
    expect(effectiveAbility(value, assignment).timing.castSec).toBe(2.75);
    expect(spell.authoredTiming).toBe(true);
    const stored = JSON.parse(JSON.stringify(value));
    expect(validateWorkspace(stored).filter(issue => issue.severity === 'error')).toEqual([]);
    expect(stored.abilities.find((a: { id: string }) => a.id === spell.id).timing.castSec).toBe(2.75);
  });
  it('accepts older documents unchanged and rejects invalid movement policy or preparation scaling', () => {
    const old = workspace();
    for (const ability of old.abilities) { delete ability.movementPolicy; delete ability.preparationScale; ability.gcdSec = 1.2; }
    const before = JSON.stringify(old);
    expect(validateWorkspace(old).filter(issue => issue.severity === 'error')).toEqual([]);
    expect(JSON.stringify(old)).toBe(before);
    const invalid = workspace();
    Object.assign(invalid.abilities[0], { movementPolicy: 'rooted', preparationScale: 0 });
    expect(validateWorkspace(invalid).filter(issue => issue.severity === 'error').map(issue => issue.path))
      .toEqual(expect.arrayContaining([expect.stringContaining('movementPolicy'), expect.stringContaining('preparationScale')]));
  });
  it('stages combat without activating unrelated map changes or mutating the installed snapshot', async () => {
    const installed = await buildContentManifest();
    const current = structuredClone(installed);
    current.maps[0].definition.name += ' unreviewed edit';
    current.abilities.definitions[0].gcdSec = .9;
    const { source: _, ...data } = current;
    current.source.contentSha256 = sha256(canonicalJson(data));
    const before = canonicalJson(installed);
    const staged = composeCombatContent(installed, current);
    expect(staged.maps).toEqual(installed.maps);
    expect(staged.abilities).toEqual(current.abilities);
    expect(staged.source.files.filter(file => file.path.startsWith('public/assets/maps/')))
      .toEqual(installed.source.files.filter(file => file.path.startsWith('public/assets/maps/')));
    expect(canonicalJson(installed)).toBe(before);
    current.careers.classes[0].name += ' changed';
    const { source: __, ...changedData } = current;
    current.source.contentSha256 = sha256(canonicalJson(changedData));
    expect(() => composeCombatContent(installed, current)).toThrow('Class/rig roster changed');
  }, 20000);
});
