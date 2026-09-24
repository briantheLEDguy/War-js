import { conditionSummary } from './conditions';
import { effectiveAbility, readNumeric, editCells } from './workspace';
import { assertWorkspace } from './validation';
import type { AbilityWorkspace, ClassAbilityAssignment, WorkshopAbility, ConditionPredicate } from './types';
import type { CellEdit } from './workspace';

export type GridFilter = { kind: 'text'; value: string } | { kind: 'values'; values: string[] }
  | { kind: 'number'; operator: 'eq' | 'gt' | 'gte' | 'lt' | 'lte' | 'between'; value: number; upper?: number }
  | { kind: 'empty'; empty: boolean };
export interface GridView { name: string; columns: string[]; widths: Record<string, number>; pinned: string[];
  filters: Record<string, GridFilter>; sort: { column: string; descending: boolean }[]; classes: string[]; compact: boolean }
export interface GridRow { id: string; assignment: ClassAbilityAssignment; ability: WorkshopAbility; className: string; values: Record<string, string | number | undefined> }
export const COLUMN_PRESETS = {
  Overview: ['class', 'ability', 'unlock', 'effects', 'target', 'cooldownSec', 'resource/manaCost', 'conditions'],
  Damage: ['class', 'ability', 'damage', 'periodicDamage', 'targeting/range', 'targeting/radius', 'targeting/maxTargets', 'conditions'],
  'Healing & Protection': ['class', 'ability', 'healing', 'periodicHealing', 'shield', 'resource/manaCost', 'conditions'],
  'Crowd Control': ['class', 'ability', 'control', 'duration', 'targeting/radius', 'cooldownSec', 'conditions'],
  'Timing & Resources': ['class', 'ability', 'timing/castSec', 'cooldownSec', 'gcdSec', 'resource/manaCost', 'resource/careerCost', 'resource/careerBuild'],
  Conditions: ['class', 'ability', 'conditions', 'checks', 'subject', 'source', 'evaluation', 'bonus', 'dependencies'],
  Changes: ['class', 'ability', 'overrides', 'conditions'],
} as const;

export function gridRows(workspace: AbilityWorkspace): GridRow[] {
  const names = new Map(workspace.classes.map(value => [value.id, value.name]));
  return workspace.assignments.map(assignment => {
    const ability = effectiveAbility(workspace, assignment);
    const unique = (values: string[]) => [...new Set(values)].join(', ');
    const predicates = ability.conditions.flatMap(rule => rule.condition.children.flatMap(node => 'children' in node ? node.children : [node])).filter((node): node is ConditionPredicate => !('children' in node));
    const amount = (kind: string, periodic: boolean): number | undefined => {
      const effects = ability.effects.filter(effect => effect.kind === kind && Boolean(effect.periodic) === periodic);
      return effects.length ? effects.reduce((sum, effect) => sum + ((effect.amount?.min ?? 0) + (effect.amount?.max ?? 0)) / 2, 0) : undefined;
    };
    return { id: assignment.id, assignment, ability, className: names.get(assignment.classId) ?? assignment.classId,
      values: { class: names.get(assignment.classId), ability: ability.name, unlock: assignment.unlockLevel,
        effects: unique(ability.effects.map(effect => effect.kind)), target: ability.targeting.target,
        damage: amount('damage', false), healing: amount('heal', false), periodicDamage: amount('damage', true), periodicHealing: amount('heal', true),
        shield: ability.effects.find(effect => effect.playerStatus?.kind === 'shield')?.playerStatus?.magnitude,
        control: unique(ability.effects.flatMap(effect => effect.status ? [effect.status.kind] : [])),
        duration: ability.effects.length === 1 ? (ability.effects[0].status?.durationSec ?? ability.effects[0].periodic?.durationSec) : undefined,
        conditions: ability.conditions.map(rule => `IF ${conditionSummary(rule.condition)} THEN ${rule.actions.map(action => action.kind === 'add_effect' ? action.effect.kind : `${action.kind} ${action.value}`).join(' + ')}`).join('; '),
        checks: unique(predicates.map(node => node.kind)), subject: unique(predicates.map(node => node.subject)), source: unique(predicates.map(node => node.source)),
        evaluation: unique(ability.conditions.map(rule => rule.event)), bonus: unique(ability.conditions.flatMap(rule => rule.actions.map(action => action.kind))),
        dependencies: unique(predicates.flatMap(node => node.abilityId ? [node.abilityId] : [])), overrides: assignment.overrides.map(value => `${value.path} = ${value.value}`).join('; ') } };
  });
}
export function cellValue(row: GridRow, column: string): string | number | undefined {
  return column in row.values ? row.values[column] : readNumeric(row.ability, column);
}
export function matchesFilter(value: string | number | undefined, filter: GridFilter): boolean {
  if (filter.kind === 'empty') return (value === undefined || value === '') === filter.empty;
  if (filter.kind === 'text') return String(value ?? '').toLocaleLowerCase().includes(filter.value.toLocaleLowerCase());
  if (filter.kind === 'values') return filter.values.includes(String(value ?? ''));
  if (typeof value !== 'number') return false;
  switch (filter.operator) {
    case 'eq': return value === filter.value;
    case 'gt': return value > filter.value;
    case 'gte': return value >= filter.value;
    case 'lt': return value < filter.value;
    case 'lte': return value <= filter.value;
    case 'between': return value >= filter.value && value <= (filter.upper ?? filter.value);
  }
}
export function queryRows(rows: readonly GridRow[], view: GridView, search = ''): GridRow[] {
  const words = search.toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return rows.filter(row => (!view.classes.length || view.classes.includes(row.assignment.classId))
    && words.every(word => `${row.className} ${row.ability.name} ${row.ability.id} ${row.values.conditions}`.toLocaleLowerCase().includes(word))
    && Object.entries(view.filters).every(([column, filter]) => matchesFilter(cellValue(row, column), filter)))
    .sort((a, b) => {
      for (const sort of view.sort) {
        const left = cellValue(a, sort.column), right = cellValue(b, sort.column);
        const order = left === right ? 0 : left === undefined ? 1 : right === undefined ? -1
          : typeof left === 'number' && typeof right === 'number' ? left - right : String(left).localeCompare(String(right));
        if (order) return sort.descending ? -order : order;
      }
      return a.id.localeCompare(b.id);
    });
}

export class WorkspaceHistory {
  private past: AbilityWorkspace[] = [];
  private future: AbilityWorkspace[] = [];
  constructor(public current: AbilityWorkspace) { assertWorkspace(current); this.current = structuredClone(current); }
  commit(next: AbilityWorkspace): void {
    assertWorkspace(next);
    this.past.push(this.current); this.past = this.past.slice(-100); this.future = []; this.current = structuredClone(next);
  }
  edit(edits: readonly CellEdit[], visibleSelected: ReadonlySet<string>): void { this.commit(editCells(this.current, edits, visibleSelected)); }
  undo(): boolean { const value = this.past.pop(); if (!value) return false; this.future.push(this.current); this.current = value; return true; }
  redo(): boolean { const value = this.future.pop(); if (!value) return false; this.past.push(this.current); this.current = value; return true; }
}
