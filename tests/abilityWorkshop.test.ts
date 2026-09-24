import { describe, expect, it } from 'vitest';
import { evaluateRules, conditionalAmount } from '../shared/game/abilities/workshop/conditions';
import { baselineWorkspace, editCells, effectiveAbility } from '../shared/game/abilities/workshop/workspace';
import { assertWorkspace, validateWorkspace } from '../shared/game/abilities/workshop/validation';
import type { ConditionContext, ConditionalRule, ConditionPredicate } from '../shared/game/abilities/workshop/types';

const context = (): ConditionContext => ({ now: 10, caster: { id: 'caster', realm: 'aegis', alive: true, statuses: [] },
  target: { id: 'enemy', realm: 'riftbound', alive: true, statuses: [] },
  recipient: { id: 'ally', realm: 'aegis', alive: true, statuses: [{ abilityId: 'renewal', effectId: 'hot', sourceId: 'caster', sourceRealm: 'aegis', category: 'hot', version: 'v1', expiresAt: 20 }] } });
const predicate = (overrides: Partial<ConditionPredicate> = {}): ConditionPredicate => ({ kind: 'hot', subject: 'recipient', source: 'self', ...overrides });
const rule = (condition = predicate()): ConditionalRule => ({ id: 'bonus', name: 'Renewal bonus', event: 'application',
  condition: { kind: 'all', children: [condition] }, actions: [{ kind: 'percent', effectId: 'heal', value: .25 }] });
const workspace = () => baselineWorkspace('a'.repeat(40), 'b'.repeat(64));

describe('ability workshop condition semantics', () => {
  it('checks source ownership, ability/effect identity, expiry, cleanse, death and depleted shields', () => {
    const input = context();
    expect(conditionalAmount(100, 'heal', [evaluateRules([rule()], 'application', input)])).toBe(125);
    input.caster.id = 'another';
    expect(evaluateRules([rule()], 'application', input).traces[0].passed).toBe(false);
    expect(evaluateRules([rule(predicate({ source: 'allied' }))], 'application', input).traces[0].passed).toBe(true);
    expect(evaluateRules([rule(predicate({ kind: 'effect', source: 'any', abilityId: 'renewal', effectId: 'hot' }))], 'application', input).traces[0].passed).toBe(true);
    input.now = 20;
    expect(evaluateRules([rule(predicate({ source: 'any' }))], 'application', input).traces[0].passed).toBe(false);
    input.recipient!.statuses = [];
    expect(evaluateRules([rule()], 'application', input).traces[0].passed).toBe(false);
    input.recipient!.alive = false;
    expect(evaluateRules([rule(predicate({ not: true }))], 'application', input).traces[0].passed).toBe(false);
    input.recipient = { id: 'ally', realm: 'aegis', alive: true, statuses: [{ abilityId: 'ward', effectId: 'shield', sourceId: 'caster', sourceRealm: 'aegis', category: 'shield', version: 'v1', expiresAt: 30, remaining: 0 }] };
    expect(evaluateRules([rule(predicate({ kind: 'ability_effect', abilityId: 'ward', source: 'any' }))], 'application', input).traces[0].passed).toBe(false);
  });
  it('distinguishes casting/channeling from recovery and traces every ALL/ANY branch', () => {
    const input = context(); input.target!.action = { abilityId: 'spell', state: 'casting' };
    const test = rule(predicate({ kind: 'casting', subject: 'target', abilityId: 'spell' }));
    expect(evaluateRules([test], 'application', input).traces[0].passed).toBe(true);
    input.target!.action!.state = 'channeling';
    expect(evaluateRules([test], 'application', input).traces[0].passed).toBe(true);
    input.target!.action!.state = 'recovery';
    expect(evaluateRules([test], 'application', input).traces[0].passed).toBe(false);
    test.condition = { kind: 'any', children: [predicate(), { kind: 'all', children: [predicate({ kind: 'dot' }), predicate({ not: true })] }] };
    const trace = evaluateRules([test], 'application', input).traces[0];
    expect(trace.passed).toBe(true); expect(trace.predicates).toHaveLength(3);
  });
  it('retains cast-start decisions but rechecks application/ticks without accumulating bonuses', () => {
    const input = context(), start = { ...rule(), event: 'cast_start' as const }, tick = { ...rule(), event: 'tick' as const };
    const captured = evaluateRules([start], 'cast_start', input);
    input.now = 21;
    expect(conditionalAmount(100, 'heal', [captured])).toBe(125);
    expect(conditionalAmount(100, 'heal', [evaluateRules([rule()], 'application', input)])).toBe(100);
    input.now = 11;
    for (let index = 0; index < 5; index++) expect(conditionalAmount(125, 'heal', [evaluateRules([tick], 'tick', input)])).toBe(156);
    input.now = 21;
    expect(conditionalAmount(125, 'heal', [evaluateRules([tick], 'tick', input)])).toBe(125);
  });
  it('adds modifiers before multiplying and never mutates the pre-event state', () => {
    const input = context(), before = structuredClone(input);
    const first = rule(); first.actions.push({ kind: 'flat', effectId: 'heal', value: 20 });
    const second = rule(); second.id = 'second'; second.actions[0] = { kind: 'percent', effectId: 'heal', value: .5 };
    second.actions.push({ kind: 'add_effect', effect: { id: 'bonus_hot', kind: 'heal', recipient: 'target', amount: { min: 10, max: 10 }, periodic: { durationSec: 5, intervalSec: 1 } } });
    const result = evaluateRules([first, second], 'application', input);
    expect(conditionalAmount(100, 'heal', [result])).toBe(210);
    expect(input).toEqual(before); expect(result.effects).toHaveLength(1);
    input.recipient!.statuses = [];
    expect(evaluateRules([first, second], 'application', input).effects).toHaveLength(0);
  });
});

describe('ability workshop catalog and edits', () => {
  it('migrates all 24 class kits without changing the original abilities', () => {
    const data = workspace();
    expect(data.abilities).toHaveLength(240); expect(data.assignments).toHaveLength(240);
    expect(validateWorkspace(data)).toEqual([]);
  });
  it('supports extra assignments and stable effect overrides after reordering', () => {
    const data = workspace(), assignment = data.assignments.find(value => data.abilities.find(a => a.id === value.abilityId)!.effects.some(e => e.kind === 'damage'))!;
    const ability = data.abilities.find(value => value.id === assignment.abilityId)!;
    const effect = ability.effects.find(value => value.kind === 'damage')!;
    const path = `effects/${effect.id}/amount/min`;
    const changed = editCells(data, [{ assignmentId: assignment.id, path, operation: 'set', value: 1 }], new Set([assignment.id]));
    changed.abilities.find(value => value.id === ability.id)!.effects.reverse();
    expect(effectiveAbility(changed, changed.assignments.find(value => value.id === assignment.id)!).effects.find(value => value.id === effect.id)!.amount!.min).toBe(1);
    expect(ability.effects.find(value => value.id === effect.id)!.amount!.min).not.toBe(1);
    const extra = structuredClone(ability); extra.id = 'custom.extra'; changed.abilities.push(extra);
    changed.assignments.push({ ...structuredClone(assignment), id: 'extra-assignment', abilityId: extra.id, displayOrder: 10, overrides: [] });
    assertWorkspace(changed);
  });
  it('rejects hidden edits, invalid values, unsafe paths, duplicate overrides and missing dependencies', () => {
    const data = workspace(), id = data.assignments[0].id;
    expect(() => editCells(data, [{ assignmentId: id, path: 'cooldownSec', operation: 'set', value: 2 }], new Set())).toThrow('hidden');
    expect(() => editCells(data, [{ assignmentId: id, path: '__proto__/x', operation: 'set', value: 2 }], new Set([id]))).toThrow('Invalid numeric');
    const edited = editCells(data, [{ assignmentId: id, path: 'cooldownSec', operation: 'set', value: -1 }], new Set([id]));
    expect(validateWorkspace(edited).length).toBeGreaterThan(0);
    expect(data.assignments[0].overrides).toEqual([]);
    data.abilities[0].conditions = [rule(predicate({ kind: 'ability_effect', abilityId: 'missing' }))];
    expect(validateWorkspace(data).some(issue => issue.message.includes('Referenced ability'))).toBe(true);
  });
  it('rejects scheduler recursion, oversized condition trees and malformed untrusted input', () => {
    const data = workspace(), ability = data.abilities[0];
    ability.effects[0].periodic = { durationSec: 5, intervalSec: 1 };
    const conditional = rule(); conditional.event = 'tick'; conditional.actions = [{ kind: 'add_effect', effect: { id: 'recursive', kind: 'heal', recipient: 'target', amount: { min: 1, max: 1 }, periodic: { durationSec: 5, intervalSec: 1 } } }];
    ability.conditions = [conditional];
    expect(validateWorkspace(data).some(issue => issue.message.includes('schedulers'))).toBe(true);
    conditional.condition.children = Array.from({ length: 17 }, () => predicate());
    expect(validateWorkspace(data).some(issue => issue.message.includes('1–16'))).toBe(true);
    expect(validateWorkspace(null)).toHaveLength(1);
    expect(validateWorkspace({ ...data, abilities: [null] }).length).toBeGreaterThan(0);
  });
  it('preserves references to conditionally added effects and detects their removal', () => {
    const data = workspace(), ability = data.abilities[0];
    const bonus = rule();
    bonus.actions = [{ kind: 'add_effect', effect: { id: 'bonus_hot', kind: 'heal', recipient: 'caster', amount: { min: 1, max: 1 }, periodic: { durationSec: 5, intervalSec: 1 } } }];
    const reference = rule(predicate({ kind: 'effect', abilityId: ability.id, effectId: 'bonus_hot' }));
    reference.id = 'reference'; reference.actions = [{ kind: 'flat', effectId: ability.effects[0].id, value: 1 }];
    ability.conditions = [bonus, reference];
    expect(validateWorkspace(data)).toEqual([]);
    ability.conditions.shift();
    expect(validateWorkspace(data).some(issue => issue.message.includes('Referenced effect'))).toBe(true);
  });
});
