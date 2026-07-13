import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';

interface IndexedModel {
  assetId?: string;
  model?: string;
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
  test('resolve all static NPC character profiles through the model index', () => {
    const index = loadAssetIndex();
    const profiles = index.characterProfiles ?? {};

    for (const zone of loadZones()) {
      for (const npc of zone.npcs ?? []) {
        const context = `${zone.id ?? '(unknown zone)'}:${npc.id ?? npc.name ?? '(unknown npc)'}`;
        expect(npc.characterProfileKey || npc.model, context).toBeTruthy();

        if (!npc.characterProfileKey) continue;

        expect(npc.characterProfileKey, context).toMatch(profileKeyRe);
        expect(profiles[npc.characterProfileKey]?.model, context).toMatch(/^chr_.*\.glb$/);
      }
    }
  });

  test('resolve all combat enemy character and creature visuals through the model index', () => {
    const index = loadAssetIndex();
    const profiles = index.characterProfiles ?? {};
    const staticProps = index.staticProps ?? {};

    for (const zone of loadZones()) {
      for (const enemy of zone.enemies ?? []) {
        const context = `${zone.id ?? '(unknown zone)'}:${enemy.id ?? enemy.name ?? '(unknown enemy)'}`;
        expect(enemy.characterProfileKey || enemy.assetKey || enemy.model, context).toBeTruthy();

        if (enemy.characterProfileKey) {
          expect(enemy.characterProfileKey, context).toMatch(profileKeyRe);
          expect(profiles[enemy.characterProfileKey]?.model, context).toMatch(/^chr_.*\.glb$/);
        }

        if (enemy.assetKey) {
          expect(enemy.assetKey, context).toMatch(staticKeyRe);
          expect(staticProps[enemy.assetKey]?.model, context).toMatch(/^prop_.*\.glb$/);
        }
      }
    }
  });
});
