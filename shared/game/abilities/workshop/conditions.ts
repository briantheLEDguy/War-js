import type { ConditionContext, ConditionNode, ConditionalRule, EvaluationEvent, PredicateTrace, RuleEvaluation } from './types';

function check(node: ConditionNode, context: ConditionContext, path: string, trace: PredicateTrace[]): boolean {
  if (node.kind === 'all' || node.kind === 'any') {
    // Evaluate every child so traces never hide a failed branch behind short-circuiting.
    const values = node.children.map((child, index) => check(child, context, `${path}.${index}`, trace));
    return values.length > 0 && (node.kind === 'all' ? values.every(Boolean) : values.some(Boolean));
  }
  const subject = node.subject === 'caster' ? context.caster : node.subject === 'target' ? context.target : context.recipient;
  const matches = subject?.alive ? subject.statuses.filter(status => status.expiresAt > context.now
    && (status.category !== 'shield' || (status.remaining ?? 0) > 0)
    && (node.source === 'any' || (node.source === 'self' ? status.sourceId === context.caster.id : Boolean(context.caster.realm) && status.sourceRealm === context.caster.realm))
    && (node.kind === 'hot' || node.kind === 'dot' ? status.category === node.kind
      : node.kind !== 'casting' && status.abilityId === node.abilityId && (node.kind !== 'effect' || status.effectId === node.effectId))) : [];
  const found = node.kind === 'casting'
    ? Boolean(subject?.action && subject.action.abilityId === node.abilityId && ['casting', 'channeling'].includes(subject.action.state))
    : matches.length > 0;
  // A missing/dead subject cannot satisfy even a negated condition.
  const passed = Boolean(subject?.alive) && (node.not ? !found : found);
  trace.push({ path, passed, subjectId: subject?.id, matchingSources: [...new Set(matches.map(value => value.sourceId))] });
  return passed;
}

/** Pure evaluation: callers capture observations once, evaluate, then apply all effects. */
export function evaluateRules(rules: readonly ConditionalRule[], event: EvaluationEvent, context: ConditionContext): RuleEvaluation {
  const result: RuleEvaluation = { modifiers: Object.create(null), effects: [], traces: [] };
  for (const rule of rules) {
    if (rule.event !== event) continue;
    const predicates: PredicateTrace[] = [];
    const passed = check(rule.condition, context, 'condition', predicates);
    result.traces.push({ ruleId: rule.id, event, at: context.now, recipientId: context.recipient?.id, passed, predicates });
    if (!passed) continue;
    for (const action of rule.actions) {
      if (action.kind === 'add_effect') result.effects.push(structuredClone(action.effect));
      else {
        const modifier = result.modifiers[action.effectId] ??= { flat: 0, percent: 0 };
        modifier[action.kind] += action.value;
      }
    }
  }
  return result;
}

/** Percent values use fractions (0.25 is +25%). Round only after all matching modifiers. */
export function conditionalAmount(normal: number, effectId: string, evaluations: readonly RuleEvaluation[]): number {
  const combined = evaluations.reduce((sum, result) => {
    const modifier = result.modifiers[effectId];
    return { flat: sum.flat + (modifier?.flat ?? 0), percent: sum.percent + (modifier?.percent ?? 0) };
  }, { flat: 0, percent: 0 });
  return Math.max(0, Math.round((normal + combined.flat) * (1 + combined.percent)));
}

export function conditionSummary(node: ConditionNode): string {
  if (node.kind === 'all' || node.kind === 'any') return `(${node.children.map(conditionSummary).join(node.kind === 'all' ? ' AND ' : ' OR ')})`;
  const names = { ability_effect: 'active effect from', effect: 'effect', hot: 'HoT', dot: 'DoT', casting: 'casting/channeling' };
  const source = node.kind === 'casting' ? '' : ` [${node.source === 'self' ? 'this caster' : node.source === 'allied' ? 'allied caster' : 'any caster'}]`;
  return `${node.subject} ${node.not ? 'IS NOT' : 'IS'} ${names[node.kind]}${node.abilityId ? ` ${node.abilityId}` : ''}${node.effectId ? ` / ${node.effectId}` : ''}${source}`;
}
