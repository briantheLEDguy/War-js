import { CAREER_ABILITY_KITS } from '../abilityData';
import { abilityUnlockLevel } from '../abilityProgression';
import { CLASSES_BY_RACE, playerRealmForRace } from '../../../data/careers';
import type { AbilityWorkspace, ClassAbilityAssignment, WorkshopAbility, WorkshopEffect } from './types';

export const classId = (name: string): string => name.toLowerCase().replace(/[^a-z0-9]+/g, '_');

/** Migrate once; IDs remain persisted thereafter, including when effects are reordered. */
export function baselineWorkspace(buildId: string, contentId: string, id = 'baseline'): AbilityWorkspace {
  const result: AbilityWorkspace = { schemaVersion: 1, id, revision: 0, baseVersion: 'baseline', buildId, contentId,
    classes: [], abilities: [], assignments: [] };
  for (const [race, names] of Object.entries(CLASSES_BY_RACE)) for (const name of names) {
    const kit = CAREER_ABILITY_KITS[name];
    if (!kit) continue;
    const career = classId(name);
    result.classes.push({ id: career, name, race, realm: playerRealmForRace(race as Parameters<typeof playerRealmForRace>[0]), resource: structuredClone(kit.resource) });
    for (const legacy of kit.abilities) {
      const { career: _career, classFamily: _family, slot, key: _key, ...base } = structuredClone(legacy);
      const effects: WorkshopEffect[] = base.effects.map((effect, index) => ({ ...effect, id: `effect_${index + 1}`,
        recipient: ['heal', 'player_status', 'cleanse', 'movement', 'wrath_relic'].includes(effect.kind) ? 'caster' : 'target' }));
      result.abilities.push({ ...base, effects, conditions: [], archived: false, legacyTargeting: true,
        timing: { mode: 'cast', castSec: legacy.animation.contactSec ?? legacy.animation.durationSec * .4 } });
      result.assignments.push({ id: `${career}:${legacy.id}`, classId: career, abilityId: legacy.id,
        unlockLevel: abilityUnlockLevel(legacy), displayOrder: slot, presentations: {}, overrides: [] });
    }
  }
  return result;
}

type NumericLocation = { object: Record<string, unknown>; key: string };
const fields: Record<string, readonly string[]> = {
  targeting: ['range', 'radius', 'projectileSpeed', 'maxTargets'],
  resource: ['manaCost', 'careerBuild', 'careerCost', 'minCareer'],
  timing: ['castSec', 'channelSec', 'intervalSec'],
  amount: ['min', 'max', 'statScale', 'levelScale', 'resourceScale'],
  status: ['durationSec', 'magnitude'], playerStatus: ['durationSec', 'magnitude'],
  movement: ['distance'], periodic: ['durationSec', 'intervalSec'],
};

/** Resolve only declared numeric fields; never interpret user input as a property traversal. */
function numericLocation(ability: WorkshopAbility, path: string): NumericLocation | undefined {
  const parts = path.split('/');
  if (parts.length === 1 && ['cooldownSec', 'gcdSec'].includes(path)) return { object: ability as unknown as Record<string, unknown>, key: path };
  if (parts.length === 2 && ['targeting', 'resource', 'timing'].includes(parts[0]) && fields[parts[0]].includes(parts[1])) {
    return { object: ability[parts[0] as 'targeting' | 'resource' | 'timing'] as unknown as Record<string, unknown>, key: parts[1] };
  }
  if (parts.length === 4 && parts[0] === 'effects' && fields[parts[2]]?.includes(parts[3])) {
    const effect = ability.effects.find(value => value.id === parts[1]);
    const object = effect?.[parts[2] as keyof WorkshopEffect];
    if (object && typeof object === 'object' && !Array.isArray(object)) return { object: object as unknown as Record<string, unknown>, key: parts[3] };
  }
  if (parts.length === 5 && parts[0] === 'conditions' && parts[2] === 'modifiers' && ['flat', 'percent'].includes(parts[4])) {
    const action = ability.conditions.find(rule => rule.id === parts[1])?.actions.find(value => value.kind === parts[4] && value.kind !== 'add_effect' && value.effectId === parts[3]);
    if (action) return { object: action as unknown as Record<string, unknown>, key: 'value' };
  }
  return undefined;
}

export function readNumeric(ability: WorkshopAbility, path: string): number | undefined {
  const location = numericLocation(ability, path);
  const value = location?.object[location.key];
  return typeof value === 'number' ? value : undefined;
}
export function writeNumeric(ability: WorkshopAbility, path: string, value: number): void {
  const location = numericLocation(ability, path);
  if (!location || !Number.isFinite(value)) throw new Error(`Invalid numeric field: ${path}`);
  location.object[location.key] = value;
  if (path.startsWith('timing/')) ability.authoredTiming = true;
}
export function effectiveAbility(workspace: AbilityWorkspace, assignment: ClassAbilityAssignment): WorkshopAbility {
  const definition = workspace.abilities.find(value => value.id === assignment.abilityId);
  if (!definition) throw new Error(`Missing ability: ${assignment.abilityId}`);
  const result = structuredClone(definition);
  for (const override of assignment.overrides) writeNumeric(result, override.path, override.value);
  return result;
}

export interface CellEdit { assignmentId: string; path: string; operation: 'set' | 'add' | 'multiply' | 'reset'; value?: number }
/** Edits are applied to a clone; a caller commits only after validating the complete result. */
export function editCells(workspace: AbilityWorkspace, edits: readonly CellEdit[], selectedVisibleIds: ReadonlySet<string>): AbilityWorkspace {
  const result = structuredClone(workspace);
  const cells = new Set<string>();
  for (const edit of edits) {
    if (!['set', 'add', 'multiply', 'reset'].includes(edit.operation)) throw new Error('Unsupported edit operation.');
    const key = JSON.stringify([edit.assignmentId, edit.path]);
    if (cells.has(key)) throw new Error('Selection repeats the same assignment field.');
    cells.add(key);
    if (!selectedVisibleIds.has(edit.assignmentId)) throw new Error('Edit targets a hidden or unselected assignment.');
    const assignment = result.assignments.find(value => value.id === edit.assignmentId);
    if (!assignment) throw new Error('Assignment no longer exists.');
    const ability = effectiveAbility(result, assignment);
    if (edit.operation === 'reset') {
      assignment.overrides = assignment.overrides.filter(value => value.path !== edit.path);
      continue;
    }
    const previous = readNumeric(ability, edit.path);
    if (edit.value === undefined || !Number.isFinite(edit.value) || (edit.operation !== 'set' && previous === undefined)) throw new Error('A finite numeric value is required.');
    const value = edit.operation === 'add' ? previous! + edit.value : edit.operation === 'multiply' ? previous! * edit.value : edit.value;
    writeNumeric(ability, edit.path, value);
    assignment.overrides = [...assignment.overrides.filter(entry => entry.path !== edit.path), { path: edit.path, value }];
  }
  return result;
}

export function duplicateAbility(source: WorkshopAbility, id: string, name: string): WorkshopAbility {
  const result = structuredClone(source);
  result.id = id; result.name = name; result.archived = false;
  // References to the source are intentional dependencies, not implicit self references.
  return result;
}
