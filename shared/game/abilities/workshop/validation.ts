import { WORKSHOP_LIMITS } from './types';
import type { AbilityWorkspace, ValidationIssue, WorkshopAbility, ConditionNode, WorkshopEffect } from './types';
import { effectiveAbility, classId } from './workspace';
import { CLASSES_BY_RACE, playerRealmForRace, type PlayableRace } from '../../../data/careers';

const object = (value: unknown): value is Record<string, any> => Boolean(value && typeof value === 'object' && !Array.isArray(value));
const identity = (value: unknown): value is string => typeof value === 'string' && /^[a-zA-Z0-9_.:-]{1,120}$/.test(value);
const finite = (value: unknown, min = 0, max = 1_000_000): value is number => typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max;
const choice = (value: unknown, options: string[]) => typeof value === 'string' && options.includes(value);

export function validateWorkspace(input: unknown): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const error = (path: string, message: string) => { issues.push({ path, message, severity: 'error' }); };
  if (!object(input) || input.schemaVersion !== 1 || !identity(input.id) || !Number.isSafeInteger(input.revision) || input.revision < 0
    || typeof input.baseVersion !== 'string' || !/^[a-f0-9]{40}$/.test(input.buildId) || !/^[a-f0-9]{64}$/.test(input.contentId)) {
    error('', 'Invalid workspace identity, revision, schema, or build/content compatibility.'); return issues;
  }
  if (!Array.isArray(input.abilities) || !Array.isArray(input.assignments) || !Array.isArray(input.classes)
    || input.abilities.length > WORKSHOP_LIMITS.abilities || input.assignments.length > WORKSHOP_LIMITS.assignments || input.classes.length !== 24) {
    error('', 'A bounded ability catalog and the 24 campaign classes are required.'); return issues;
  }
  const abilities = new Map<string, WorkshopAbility>();
  for (const [index, ability] of input.abilities.entries()) {
    if (!object(ability) || !identity(ability.id) || abilities.has(ability.id)) { error(`abilities/${index}`, 'Invalid or duplicate ability identity.'); continue; }
    abilities.set(ability.id, ability as WorkshopAbility);
  }
  const classes = new Map<string, any>();
  const roster = new Map(Object.entries(CLASSES_BY_RACE).flatMap(([race,names]) => names.map(name => [classId(name), { name, race, realm: playerRealmForRace(race as PlayableRace) }] as const)));
  for (const [index, career] of input.classes.entries()) {
    if (!object(career) || !identity(career.id) || classes.has(career.id) || typeof career.name !== 'string'
      || !choice(career.realm, ['aegis', 'riftbound']) || !object(career.resource) || !finite(career.resource.max, 1, 10000)
      || !finite(career.resource.initial, 0, career.resource.max)) error(`classes/${index}`, 'Invalid or duplicate campaign class/resource.');
    else {
      const expected = roster.get(career.id);
      if (!expected || expected.name !== career.name || expected.race !== career.race || expected.realm !== career.realm) error(`classes/${index}`, 'Campaign class identities, names, race and realm cannot be changed.');
      classes.set(career.id, career);
    }
  }
  const validateEffect = (effect: unknown, path: string, ability: WorkshopAbility): effect is WorkshopEffect => {
    if (!object(effect) || !identity(effect.id) || !choice(effect.recipient, ['caster', 'target', 'allies', 'enemies'])
      || !choice(effect.kind, ['damage', 'heal', 'status', 'player_status', 'cleanse', 'movement', 'wrath_relic'])) { error(path, 'Invalid effect identity, kind, or recipient.'); return false; }
    if (effect.kind === 'wrath_relic' && ability.id !== 'battle_prelate.icon_of_wrath') error(path, 'Relic execution is reserved for the admitted existing ability.');
    if (['damage', 'heal'].includes(effect.kind)) {
      if (!object(effect.amount) || !finite(effect.amount.min) || !finite(effect.amount.max, effect.amount.min)) error(`${path}/amount`, 'Minimum and maximum amounts must be finite and ordered.');
      else for (const key of ['statScale', 'resourceScale', 'levelScale']) if (effect.amount[key] !== undefined && !finite(effect.amount[key], 0, 1000)) error(`${path}/amount/${key}`, 'Scaling must be between 0 and 1000.');
    }
    if (effect.periodic !== undefined && (!['damage', 'heal'].includes(effect.kind) || !object(effect.periodic)
      || !finite(effect.periodic.durationSec, .1, 60) || !finite(effect.periodic.intervalSec, .1, effect.periodic.durationSec))) error(`${path}/periodic`, 'Periodic damage/healing requires duration <=60 s and interval >=0.1 s within duration.');
    if (effect.kind === 'status' || effect.kind === 'player_status') {
      const status = effect.kind === 'status' ? effect.status : effect.playerStatus;
      const kinds = effect.kind === 'status' ? ['burn', 'bleed', 'slow', 'root', 'silence', 'stagger', 'mark', 'debuff'] : ['guard', 'shield', 'empower', 'haste'];
      if (!object(status) || !choice(status.kind, kinds) || !finite(status.durationSec, .01, 60)
        || (status.magnitude !== undefined && !finite(status.magnitude, 0, ['root', 'silence', 'stagger'].includes(status.kind) ? 1 : status.kind === 'guard' ? .75 : .6))) error(path, 'Invalid status kind, duration, or magnitude (native status limits apply).');
    }
    if (effect.kind === 'movement' && (effect.recipient !== 'caster' || !object(effect.movement) || !choice(effect.movement.mode, ['forward', 'backward', 'toward_target']) || !finite(effect.movement.distance, 0, 12))) error(path, 'Movement requires the caster, a supported direction and distance up to 12 m.');
    if (effect.kind === 'cleanse' && (!object(effect.cleanse) || !Array.isArray(effect.cleanse.kinds) || effect.cleanse.kinds.some((kind: unknown) => !choice(kind, ['slow', 'root', 'stagger', 'debuff'])))) error(path, 'Invalid cleanse selection.');
    return true;
  };
  const validateAbility = (ability: WorkshopAbility, path: string) => {
    if (typeof ability.name !== 'string' || !ability.name.trim() || ability.name.length > 100 || typeof ability.summary !== 'string' || ability.summary.length > 4000
      || typeof ability.archived !== 'boolean' || !finite(ability.cooldownSec, 0, 3600) || !finite(ability.gcdSec, 0, 60)) error(path, 'Invalid name, description, archive state, or cooldown.');
    const target = ability.targeting;
    if (!object(target) || !choice(target.target, ['self', 'enemy', 'ally', 'ground']) || !choice(target.shape, ['melee', 'projectile', 'beam', 'cone', 'area', 'self', 'dash', 'deployable', 'pet'])
      || !finite(target.range, 0, 200) || (target.radius !== undefined && !finite(target.radius, 0, 100))
      || (target.projectileSpeed !== undefined && !finite(target.projectileSpeed, .1, 1000))
      || (target.maxTargets !== undefined && (!Number.isInteger(target.maxTargets) || !finite(target.maxTargets, 1, 128)))) error(`${path}/targeting`, 'Invalid target geometry or target limit.');
    if (!object(ability.resource)) error(`${path}/resource`, 'Resource definition required.');
    else for (const key of ['manaCost', 'careerBuild', 'careerCost', 'minCareer'] as const) if (ability.resource[key] !== undefined && !finite(ability.resource[key], 0, 10000)) error(`${path}/resource/${key}`, 'Cost/gain must be between 0 and 10000.');
    if (!object(ability.timing) || !choice(ability.timing.mode, ['instant', 'cast', 'channel']) || !finite(ability.timing.castSec, 0, 60)
      || (ability.timing.mode === 'channel' && (!finite(ability.timing.channelSec, .1, 60) || !finite(ability.timing.intervalSec, .1, ability.timing.channelSec)))) error(`${path}/timing`, 'Invalid cast/channel timing.');
    if (!object(ability.animation) || !finite(ability.animation.durationSec, .01, 120) || !object(ability.visual)) error(`${path}/presentation`, 'Animation and visual definitions are required.');
    if (!Array.isArray(ability.effects) || ability.effects.length > WORKSHOP_LIMITS.effects || (!ability.effects.length && !ability.unavailableReason)) { error(`${path}/effects`, 'Ability requires 1–32 effects, or an explicit unavailable reason.'); return; }
    const effectIds = new Set<string>();
    for (const effect of ability.effects) {
      const effectPath = `${path}/effects/${effect?.id ?? '?'}`;
      if (!validateEffect(effect, effectPath, ability)) continue;
      if (effectIds.has(effect.id)) error(effectPath, 'Duplicate effect identity.');
      effectIds.add(effect.id);
    }
    if (!Array.isArray(ability.conditions) || ability.conditions.length > WORKSHOP_LIMITS.rules) { error(`${path}/conditions`, 'At most 16 conditional rules are permitted.'); return; }
    const ruleIds = new Set<string>();
    for (const rule of ability.conditions) {
      const rulePath = `${path}/conditions/${rule?.id ?? '?'}`;
      if (!object(rule) || !identity(rule.id) || ruleIds.has(rule.id) || !choice(rule.event, ['cast_start', 'application', 'tick'])) { error(rulePath, 'Invalid or duplicate rule identity/event.'); continue; }
      ruleIds.add(rule.id);
      let predicates = 0;
      const validateNode = (node: ConditionNode, nodePath: string, depth: number): void => {
        if (!object(node)) { error(nodePath, 'A condition is required.'); return; }
        if (node.kind === 'all' || node.kind === 'any') {
          if (depth > WORKSHOP_LIMITS.groupDepth || !Array.isArray(node.children) || !node.children.length || node.children.length > 16) { error(nodePath, 'Condition groups require 1–16 children and at most two group levels.'); return; }
          node.children.forEach((child, index) => validateNode(child, `${nodePath}/${index}`, depth + 1)); return;
        }
        if (++predicates > 16) { error(nodePath, 'At most 16 predicates per rule.'); return; }
        if (!choice(node.kind, ['ability_effect', 'effect', 'hot', 'dot', 'casting']) || !choice(node.subject, ['caster', 'target', 'recipient']) || !choice(node.source, ['self', 'allied', 'any']) || (node.not !== undefined && typeof node.not !== 'boolean')) error(nodePath, 'Invalid condition kind, subject, source, or negation.');
        if (rule.event === 'cast_start' && node.subject === 'recipient') error(nodePath, 'Recipients are unavailable at cast start; use target/caster or application timing.');
        if (['ability_effect', 'effect', 'casting'].includes(node.kind)) {
          const referenced = abilities.get(node.abilityId ?? '');
          if (!referenced) error(nodePath, 'Referenced ability does not exist.');
          const hasEffect = referenced && ((Array.isArray(referenced.effects) && referenced.effects.some(effect => effect?.id === node.effectId))
            || (Array.isArray(referenced.conditions) && referenced.conditions.some(condition => Array.isArray(condition?.actions)
              && condition.actions.some(action => action?.kind === 'add_effect' && action.effect?.id === node.effectId))));
          if (node.kind === 'effect' && !hasEffect) error(nodePath, 'Referenced effect does not exist.');
        }
      };
      if (!object(rule.condition) || !['all', 'any'].includes(rule.condition.kind)) error(rulePath, 'Rules require an ALL/ANY root group.');
      else validateNode(rule.condition, `${rulePath}/condition`, 1);
      if (!Array.isArray(rule.actions) || !rule.actions.length || rule.actions.length > 32) { error(rulePath, 'A rule requires 1–32 actions.'); continue; }
      const modifiers = new Set<string>();
      for (const [index, action] of rule.actions.entries()) {
        const actionPath = `${rulePath}/actions/${index}`;
        if (!object(action)) { error(actionPath, 'Invalid action.'); continue; }
        if (action.kind === 'add_effect') {
          if (!validateEffect(action.effect, actionPath, ability)) continue;
          if (effectIds.has(action.effect.id)) error(actionPath, 'Bonus effect identities must be unique within the ability.');
          effectIds.add(action.effect.id);
          if (['movement', 'cleanse', 'wrath_relic'].includes(action.effect.kind)) error(actionPath, 'Conditional actions support damage, healing, and statuses.');
          if (rule.event === 'tick' && (action.effect.periodic || ['burn', 'bleed'].includes(action.effect.status?.kind ?? ''))) error(actionPath, 'Tick rules cannot create periodic schedulers.');
        } else if (action.kind === 'flat' || action.kind === 'percent') {
          const effect = ability.effects.find(value => value.id === action.effectId);
          if (!effect || !['damage', 'heal'].includes(effect.kind) || (rule.event === 'tick' && !effect.periodic && ability.timing?.mode !== 'channel')) error(actionPath, 'Modifier must reference a base damage/healing effect; tick modifiers require a periodic effect.');
          if (!finite(action.value, action.kind === 'percent' ? -1 : -1_000_000, action.kind === 'percent' ? 100 : 1_000_000)) error(actionPath, 'Modifier is non-finite or outside its limits.');
          const key = `${action.kind}:${action.effectId}`;
          if (modifiers.has(key)) error(actionPath, 'Combine duplicate modifiers into one action.');
          modifiers.add(key);
        } else error(actionPath, 'Unsupported conditional action.');
      }
      if (rule.event === 'tick' && !ability.effects.some(effect => effect.periodic) && ability.timing?.mode !== 'channel') error(rulePath, 'Tick rules require a periodic effect or channel.');
    }
  };
  for (const ability of abilities.values()) validateAbility(ability, `abilities/${ability.id}`);
  // Avoid materializing malformed definitions. These errors already identify their fields.
  if (issues.length) return issues;
  const assignmentIds = new Set<string>(), pairs = new Set<string>();
  for (const [index, assignment] of input.assignments.entries()) {
    const path = `assignments/${assignment?.id ?? index}`;
    if (!object(assignment) || !identity(assignment.id) || assignmentIds.has(assignment.id) || !classes.has(assignment.classId) || !abilities.has(assignment.abilityId)
      || !Number.isInteger(assignment.unlockLevel) || !finite(assignment.unlockLevel, 1, 45) || !Number.isInteger(assignment.displayOrder) || !finite(assignment.displayOrder, 0, 10000)
      || !object(assignment.presentations) || Object.entries(assignment.presentations).some(([profile, recipe]) => !identity(profile) || !identity(recipe)) || !Array.isArray(assignment.overrides) || assignment.overrides.length > 256) { error(path, 'Invalid assignment, level, class, presentation, or overrides.'); continue; }
    assignmentIds.add(assignment.id);
    const pair = `${assignment.classId}:${assignment.abilityId}`;
    if (pairs.has(pair)) error(path, 'An ability can be assigned only once to a class.');
    pairs.add(pair);
    const paths = new Set<string>();
    for (const override of assignment.overrides) {
      if (!object(override) || typeof override.path !== 'string' || paths.has(override.path) || !finite(override.value, -1_000_000)) { error(path, 'Invalid or duplicate numeric override.'); continue; }
      paths.add(override.path);
    }
    try {
      const effective = effectiveAbility(input as AbilityWorkspace, assignment as any);
      validateAbility(effective, path);
      if (Math.max(effective.resource.careerCost ?? 0, effective.resource.minCareer ?? 0) > classes.get(assignment.classId).resource.max) error(path, 'Resource requirement exceeds the assigned class resource maximum.');
    } catch (cause) { error(path, cause instanceof Error ? cause.message : 'Invalid override.'); }
  }
  return issues;
}

export function assertWorkspace(value: unknown): asserts value is AbilityWorkspace {
  const errors = validateWorkspace(value).filter(issue => issue.severity === 'error');
  if (errors.length) throw new Error(errors.map(issue => `${issue.path}: ${issue.message}`).join('\n'));
}
