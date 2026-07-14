import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';

interface IndexedModel {
  assetId?: string;
  model?: string;
  lifecycleStatus?: string;
  runtimeReady?: boolean;
}

interface AssetIndex {
  characterProfiles?: Record<string, IndexedModel>;
  staticProps?: Record<string, IndexedModel>;
}

interface NpcSpawn {
  id?: string;
  name?: string;
  model?: string;
  characterProfileKey?: string;
}

interface EnemySpawn {
  id?: string;
  name?: string;
  model?: string;
  assetKey?: string;
  characterProfileKey?: string;
}

interface ZoneFile {
  id?: string;
  npcs?: NpcSpawn[];
  enemies?: EnemySpawn[];
}

const mapsDir = path.join(process.cwd(), 'public', 'assets', 'maps');
const assetIndexPath = path.join(process.cwd(), 'public', 'assets', 'models', 'asset-index.json');
const profileKeyRe = /^(npc|enemy)_[a-z0-9_]+$/;
const staticKeyRe = /^[a-z0-9_]+$/;

function loadAssetIndex(): AssetIndex {
  return JSON.parse(readFileSync(assetIndexPath, 'utf8')) as AssetIndex;
}

function loadZones(): ZoneFile[] {
  return readdirSync(mapsDir)
    .filter((file) => file.endsWith('.json'))
    .sort()
    .map((file) => JSON.parse(readFileSync(path.join(mapsDir, file), 'utf8')) as ZoneFile);
}

describe('NPC and enemy model assignments', () => {
  test('keeps removed NPC proxy profiles on the safe runtime fallback path', () => {
    const index = loadAssetIndex();
    const profiles = index.characterProfiles ?? {};
    let fallbackProfiles = 0;

    for (const zone of loadZones()) {
      for (const npc of zone.npcs ?? []) {
        const context = `${zone.id ?? '(unknown zone)'}:${npc.id ?? npc.name ?? '(unknown npc)'}`;
        expect(npc.characterProfileKey || npc.model, context).toBeTruthy();

        if (!npc.characterProfileKey) continue;

        expect(npc.characterProfileKey, context).toMatch(profileKeyRe);
        const indexed = profiles[npc.characterProfileKey];
        if (!indexed) {
          fallbackProfiles += 1;
          continue;
        }
        expect(indexed.lifecycleStatus, context).toBe('approved');
        expect(indexed.runtimeReady, context).not.toBe(false);
        expect(indexed.model, context).toMatch(/^chr_.*\.glb$/);
      }
    }
    expect(fallbackProfiles).toBeGreaterThan(0);
  });

  test('keeps unapproved humanoids and regenerated creatures on runtime fallback', () => {
    const index = loadAssetIndex();
    const profiles = index.characterProfiles ?? {};
    const staticProps = index.staticProps ?? {};
    let fallbackProfiles = 0;

    for (const zone of loadZones()) {
      for (const enemy of zone.enemies ?? []) {
        const context = `${zone.id ?? '(unknown zone)'}:${enemy.id ?? enemy.name ?? '(unknown enemy)'}`;
        expect(enemy.characterProfileKey || enemy.assetKey || enemy.model, context).toBeTruthy();

        if (enemy.characterProfileKey) {
          expect(enemy.characterProfileKey, context).toMatch(profileKeyRe);
          const indexed = profiles[enemy.characterProfileKey];
          if (!indexed) {
            fallbackProfiles += 1;
          } else {
            expect(indexed.lifecycleStatus, context).toBe('approved');
            expect(indexed.runtimeReady, context).not.toBe(false);
            expect(indexed.model, context).toMatch(/^chr_.*\.glb$/);
          }
        }

        if (enemy.assetKey) {
          expect(enemy.assetKey, context).toMatch(staticKeyRe);
          if (enemy.assetKey.startsWith('creature_')) {
            expect(staticProps[enemy.assetKey], context).toBeUndefined();
          } else {
            expect(staticProps[enemy.assetKey]?.model, context).toMatch(/^prop_.*\.glb$/);
          }
        }
      }
    }
    expect(fallbackProfiles).toBeGreaterThan(0);
  });
});
