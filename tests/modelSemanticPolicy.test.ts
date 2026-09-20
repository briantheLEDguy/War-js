import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  FORBIDDEN_GENERATED_TERMS,
  validateBlueprintRecord,
} from '../scripts/blender-character-pipeline/tools/pipeline-lib.mjs';

function farmerBlueprint() {
  return JSON.parse(readFileSync(
    'scripts/blender-character-pipeline/data/asset-blueprints/frontier_sunmeadow_empire_farmer.asset.json',
    'utf8',
  ));
}

function semanticErrors(blueprint) {
  return validateBlueprintRecord('semantic-policy.asset.json', blueprint).errors
    .filter((error) => error.includes('generated semantic field'));
}

describe('original regional Empire character naming', () => {
  it('accepts the published original farmer identifiers without a compatibility bypass', () => {
    expect(validateBlueprintRecord('farmer.asset.json', farmerBlueprint()).ok).toBe(true);
  });

  it('permits only the planned original herbalist identity in its exact semantic fields', () => {
    const blueprint = farmerBlueprint();
    blueprint.assetId = 'chr.frontier.sunmeadow.empire_herbalist';
    blueprint.output.model = 'frontier_sunmeadow_empire_herbalist_lod0.glb';
    blueprint.materials.textureSet = 'frontier_sunmeadow_empire_herbalist';
    blueprint.runtime.profileKey = 'npc_frontier_sunmeadow_empire_herbalist';
    expect(semanticErrors(blueprint)).toEqual([]);
    blueprint.runtime.profileKey += '_unreviewed';
    expect(semanticErrors(blueprint)).toHaveLength(1);
  });

  it.each(FORBIDDEN_GENERATED_TERMS)('still rejects %s in generated display names', (term) => {
    const blueprint = farmerBlueprint();
    blueprint.displayName = `Farmer ${term}`;
    expect(semanticErrors(blueprint)).toContain(
      `generated semantic field contains forbidden term "${term}": ${blueprint.displayName}`,
    );
  });

  it.each([
    ['assetId', 'chr.frontier.sunmeadow.empire_guard'],
    ['output.model', 'empire_guard.glb'],
    ['materials.textureSet', 'empire_guard'],
    ['runtime.profileKey', 'empire_guard'],
    ['runtime.bodyModel', 'empire_guard.glb'],
    ['materials.master', 'empire_guard'],
  ])('keeps legacy or unrecognized names blocked in %s', (field, value) => {
    const blueprint = farmerBlueprint();
    const parts = field.split('.');
    if (parts.length === 1) blueprint[field] = value;
    else blueprint[parts[0]][parts[1]] = value;
    expect(semanticErrors(blueprint)).toContain(
      `generated semantic field contains forbidden term "empire_": ${value}`,
    );
  });

  it('does not exempt allowed identity strings copied into other semantic fields', () => {
    const blueprint = farmerBlueprint();
    blueprint.displayName = blueprint.assetId;
    blueprint.materials.master = blueprint.materials.textureSet;
    blueprint.sets = [blueprint.materials.textureSet];
    expect(semanticErrors(blueprint)).toHaveLength(3);
  });

  it('does not extend the exception to non-character assets', () => {
    const blueprint = farmerBlueprint();
    blueprint.category = 'prop';
    expect(semanticErrors(blueprint)).toHaveLength(4);
  });

  it('does not permit protected names appended to the regional identity', () => {
    const blueprint = farmerBlueprint();
    const term = ['sig', 'mar'].join('');
    blueprint.assetId += `_${term}`;
    expect(semanticErrors(blueprint)).toContain(
      `generated semantic field contains forbidden term "${term}": ${blueprint.assetId}`,
    );
  });
});
