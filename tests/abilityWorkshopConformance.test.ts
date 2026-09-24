import { describe, expect, it } from 'vitest';
import fixtures from './fixtures/ability-conditions.json';
import { conditionalAmount, evaluateRules } from '../shared/game/abilities/workshop/conditions';
import type { ConditionContext, ConditionalRule, EvaluationEvent } from '../shared/game/abilities/workshop/types';

describe('shared Unreal / TypeScript conditional conformance', () => {
  for (const fixture of fixtures.cases) it(fixture.name, () => {
    const context = structuredClone(fixture.context) as ConditionContext;
    const before = structuredClone(context);
    const result = evaluateRules(fixture.conditions as ConditionalRule[], fixture.event as EvaluationEvent, context);
    expect(conditionalAmount(fixture.normal, fixture.effectId, [result])).toBe(fixture.expected.amount);
    expect(result.traces.map(trace => trace.passed)).toEqual(fixture.expected.passed);
    expect(result.traces.flatMap(trace => trace.predicates.map(predicate => predicate.passed))).toEqual(fixture.expected.predicates);
    expect(result.traces.flatMap(trace => trace.predicates.map(predicate => predicate.matchingSources))).toEqual(fixture.expected.sources);
    expect(result.effects.map(effect => effect.id)).toEqual(fixture.expected.bonusEffects);
    expect(context).toEqual(before);
  });
});
