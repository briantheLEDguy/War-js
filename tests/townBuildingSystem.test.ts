import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';
import {
  prefabDefinitionForKind,
  prefabsForGroup,
} from '../src/world/editor/PrefabCatalog';

interface AssetIndex {
  staticProps: Record<string, { model: string }>;
}

const root = process.cwd();
const modelDir = path.join(root, 'public', 'assets', 'models');
const assetIndex = JSON.parse(readFileSync(path.join(modelDir, 'asset-index.json'), 'utf8')) as AssetIndex;

describe('dark-fantasy town building system', () => {
  test('maps every generated town asset into the GM modular town kit', () => {
    const prefabs = prefabsForGroup('Modular Town Kit');
    expect(prefabs).toHaveLength(20);
    expect(prefabs.map((prefab) => prefab.kind)).toContain('town_castle');

    for (const prefab of prefabs) {
      expect(prefab.assetKey, prefab.kind).toBe(prefab.kind);
      expect(prefab.model, prefab.kind).toMatch(/^prop_town_.*\.glb$/);
      expect(assetIndex.staticProps[prefab.assetKey!]?.model, prefab.kind).toBe(prefab.model);
      expect(existsSync(path.join(modelDir, prefab.model!)), prefab.kind).toBe(true);
    }
  });

  test('routes the general realm house tools through the generated town models', () => {
    expect(prefabDefinitionForKind('building')).toEqual(expect.objectContaining({
      assetKey: 'town_house_1',
      model: 'prop_town_house_1.glb',
      cameraSolid: true,
    }));
    expect(prefabDefinitionForKind('rift_house')).toEqual(expect.objectContaining({
      assetKey: 'town_house_2',
      model: 'prop_town_house_2.glb',
      cameraSolid: true,
    }));
  });

  test('maps the dark-fantasy fortress build pack into the GM prefab catalog', () => {
    const prefabs = prefabsForGroup('Fortress Build Pack');
    expect(prefabs.map((prefab) => prefab.kind)).toEqual(expect.arrayContaining([
      'castle_gate',
      'town_fortress_wall',
      'town_fortress_corner_tower',
      'town_fortress_gatehouse',
      'town_fortress_wall_stairs',
      'town_fortress_brazier',
      'town_fortress_banner',
      'town_fortress_barricade',
    ]));

    for (const prefab of prefabs.filter((entry) => entry.kind.startsWith('town_fortress_'))) {
      expect(prefab.assetKey, prefab.kind).toBe(prefab.kind);
      expect(prefab.model, prefab.kind).toMatch(/^prop_town_fortress_.*\.glb$/);
      expect(assetIndex.staticProps[prefab.assetKey!]?.model, prefab.kind).toBe(prefab.model);
      expect(existsSync(path.join(modelDir, prefab.model!)), prefab.kind).toBe(true);
    }
  });
});
