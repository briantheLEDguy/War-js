import fs from 'node:fs';
import { describe, expect, test } from 'vitest';
import { generateBuilderCatalog } from '../scripts/generate-builder-catalog.mjs';
import { WORLD_EDITOR_PREFABS, prefabDefinitionForKind, prefabDefaultCollidersForKind,
  prefabDefaultInteractionForKind } from '../src/world/editor/PrefabCatalog';
import { pickFallback } from '../src/world/Props';
import { WORLD_LIFE_PROP_KINDS } from '../src/world/WorldLifeAssets';
import generated from '../src/world/editor/prefabs.generated.json';

describe('GM scenery catalog coverage', () => {
  test('generated catalog stays synchronized with maps, reviewed assets and geometry', () => {
    expect(generated).toEqual(generateBuilderCatalog());
    expect(new Set(WORLD_EDITOR_PREFABS.map(p => p.kind)).size).toBe(WORLD_EDITOR_PREFABS.length);
  });
  test('every runtime-ready static asset and every visible map model has a placement entry', () => {
    const registry = JSON.parse(fs.readFileSync('public/assets/models/asset-index.json', 'utf8'));
    for (const [key, asset] of Object.entries(registry.staticProps) as Array<[string, { runtimeReady: boolean }]>) {
      if (asset.runtimeReady) expect(WORLD_EDITOR_PREFABS.some(p => p.assetKey === key), key).toBe(true);
    }
    for (const file of fs.readdirSync('public/assets/maps').filter(f => f.endsWith('.json'))) {
      const map = JSON.parse(fs.readFileSync(`public/assets/maps/${file}`, 'utf8'));
      for (const prop of map.props ?? []) {
        if (prop.visible === false) continue;
        expect(WORLD_EDITOR_PREFABS.some(p => (p.kind === prop.kind || p.fallbackKind === prop.kind)
          && (!prop.model || p.model === prop.model)), `${file}: ${prop.kind}/${prop.model}`).toBe(true);
      }
    }
  });
  test('new city pieces retain traversable stairs, open bridge decks and correctly sized mountain footprint', () => {
    const stairs = prefabDefinitionForKind('aegis_stairs')!;
    expect(stairs.walkableSurfaces?.some(s => Math.abs((s.toY ?? 0) - (s.fromY ?? 0)) === 6)).toBe(true);
    expect(prefabDefinitionForKind('aegis_bridge_wide')!.walkableSurfaces?.length).toBeGreaterThan(0);
    expect(prefabDefinitionForKind('aegis_mountain_massif')!.footprint.width).toBeGreaterThan(500);
    expect(prefabDefinitionForKind('aegis_citadel')!.lodModels).toHaveLength(2);
  });
  test('gate copies receive independent interaction IDs and preserve their closed blockers', () => {
    const a = prefabDefaultInteractionForKind('aegis_portcullis', 'copy-a')!;
    const b = prefabDefaultInteractionForKind('aegis_portcullis', 'copy-b')!;
    expect(a.id).not.toBe(b.id);
    const colliders = prefabDefaultCollidersForKind('aegis_portcullis', a.id)!;
    expect(colliders.some(c => c.blocksWhen === 'closed' && c.interactionId === a.id)).toBe(true);
    colliders[0].width = 999;
    expect(prefabDefaultCollidersForKind('aegis_portcullis', b.id)![0].width).not.toBe(999);
  });
  test('world life furniture uses its proper procedural asset when a model is absent', () => {
    for (const kind of WORLD_LIFE_PROP_KINDS) {
      expect(prefabDefinitionForKind(kind), kind).not.toBeNull();
      const object = pickFallback(kind)();
      expect(object.children.length, kind).toBeGreaterThan(0);
    }
  });
});
