import type { AbilityDefinition, AbilityEffect, AbilityTargeting, CareerResourceDefinition } from '../types';

export const WORKSHOP_LIMITS = { rules: 16, predicates: 16, groupDepth: 2, effects: 32, abilities: 5000, assignments: 10000 } as const;
export type EvaluationEvent = 'cast_start' | 'application' | 'tick';
export type ConditionSubject = 'caster' | 'target' | 'recipient';
export type ConditionSource = 'self' | 'allied' | 'any';
export type PredicateKind = 'ability_effect' | 'effect' | 'hot' | 'dot' | 'casting';

export interface ConditionPredicate {
  kind: PredicateKind;
  subject: ConditionSubject;
  source: ConditionSource;
  not?: boolean;
  abilityId?: string;
  effectId?: string;
}
export type ConditionGroup = { kind: 'all'; children: ConditionNode[] } | { kind: 'any'; children: ConditionNode[] };
export type ConditionNode = ConditionPredicate | ConditionGroup;
export interface WorkshopEffect extends AbilityEffect {
  id: string;
  recipient: 'caster' | 'target' | 'enemies' | 'allies';
  periodic?: { durationSec: number; intervalSec: number };
}
export type ConditionalAction =
  | { kind: 'flat' | 'percent'; effectId: string; value: number }
  | { kind: 'add_effect'; effect: WorkshopEffect };
export interface ConditionalRule {
  id: string;
  name: string;
  event: EvaluationEvent;
  condition: ConditionGroup;
  actions: ConditionalAction[];
}
export interface WorkshopAbility extends Omit<AbilityDefinition, 'career' | 'classFamily' | 'slot' | 'key' | 'effects' | 'targeting'> {
  effects: WorkshopEffect[];
  targeting: Omit<AbilityTargeting, 'target'> & { target: 'enemy' | 'self' | 'ally' | 'ground'; maxTargets?: number };
  conditions: ConditionalRule[];
  archived: boolean;
  /** Migration preserves the historical self/siege-heal recipient rule until targeting is edited. */
  legacyTargeting?: boolean;
  authoredTiming?: boolean;
  timing: { mode: 'instant' | 'cast' | 'channel'; castSec: number; channelSec?: number; intervalSec?: number };
}
export interface NumericOverride { path: string; value: number }
export interface ClassAbilityAssignment {
  id: string;
  classId: string;
  abilityId: string;
  unlockLevel: number;
  displayOrder: number;
  /** Keys are approved character profiles; values are admitted presentation recipe IDs. */
  presentations: Record<string, string>;
  overrides: NumericOverride[];
}
export interface WorkshopClass {
  id: string;
  name: string;
  realm: 'aegis' | 'riftbound';
  race: string;
  resource: CareerResourceDefinition;
}
export interface AbilityWorkspace {
  schemaVersion: 1;
  id: string;
  revision: number;
  baseVersion: string;
  buildId: string;
  contentId: string;
  classes: WorkshopClass[];
  abilities: WorkshopAbility[];
  assignments: ClassAbilityAssignment[];
}
export interface ValidationIssue { path: string; message: string; severity: 'error' | 'warning' }
export interface StatusObservation {
  abilityId: string;
  effectId: string;
  sourceId: string;
  sourceRealm: string;
  version: string;
  category: 'hot' | 'dot' | 'status' | 'shield';
  expiresAt: number;
  remaining?: number;
}
export interface CombatObservation {
  id: string;
  realm: string;
  alive: boolean;
  statuses: readonly StatusObservation[];
  action?: { abilityId: string; state: 'casting' | 'channeling' | 'recovery' };
}
export interface ConditionContext {
  now: number;
  caster: CombatObservation;
  target?: CombatObservation;
  recipient?: CombatObservation;
}
export interface PredicateTrace { path: string; passed: boolean; subjectId?: string; matchingSources: string[] }
export interface RuleTrace {
  ruleId: string;
  event: EvaluationEvent;
  at: number;
  recipientId?: string;
  passed: boolean;
  predicates: PredicateTrace[];
}
export interface RuleEvaluation {
  modifiers: Record<string, { flat: number; percent: number }>;
  effects: WorkshopEffect[];
  traces: RuleTrace[];
}
export interface AbilityTestResult {
  id: string;
  workspaceId: string;
  revision: number;
  catalogHash: string;
  kind: 'calculated' | 'native';
  scenario: Record<string, unknown>;
  measures: { damage: number; healing: number; overhealing: number; absorption: number; controlSeconds: number; resource: number };
  traces: RuleTrace[];
}
