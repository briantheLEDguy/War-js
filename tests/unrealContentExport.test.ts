import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeAll, describe, expect, test } from 'vitest';
import { CAREER_ABILITY_KITS } from '../shared/game/abilities/abilityData';
import { ITEM_CATALOG } from '../shared/data/items';
import { WORLD_EDITOR_PREFABS } from '../shared/world/editor/PrefabCatalog';
import { assertJsonSerializable, canonicalJson, sourcePointToUnreal, sourceYawToUnrealDegrees } from '../scripts/unreal/content-contract';
import { buildContentManifest, exportContent, REPOSITORY_ROOT, validateContentManifest, type ContentManifest } from '../scripts/unreal/export-content';

let manifest: ContentManifest;
const temporaryDirectories: string[] = [];
beforeAll(async () => { manifest = await buildContentManifest(); }, 15_000);
afterEach(async () => {
  await Promise.all(temporaryDirectories.splice(0).map(directory => rm(directory, { recursive: true, force: true })));
});

function copy(): ContentManifest { return structuredClone(manifest); }

describe('Unreal engine-neutral content archive', () => {
  test('includes the complete current playable, gameplay and authoring catalogs', () => {
    expect(manifest.schemaVersion).toBe(1);
    expect(manifest.careers.classes).toHaveLength(24);
    expect(manifest.careers.playableProfiles).toHaveLength(48);
    expect(manifest.abilities.definitions).toHaveLength(240);
    expect(manifest.items.definitions).toHaveLength(482);
    expect(manifest.quests).toHaveLength(8);
    expect(manifest.crafting.professions).toHaveLength(6);
    expect(manifest.crafting.recipes).toHaveLength(5);
    expect(manifest.crafting.seeds).toHaveLength(2);
    expect(manifest.maps).toHaveLength(32);
    expect(manifest.developmentMaps.map(map => map.id)).toEqual(['zone1']);
    expect(manifest.campaign.edges).toHaveLength(70);
    expect(Object.values(manifest.campaign.objectivesByZone).flat()).toHaveLength(108);
    expect(manifest.builder.prefabs).toEqual(JSON.parse(JSON.stringify(WORLD_EDITOR_PREFABS)));
    expect(manifest.wiki.pages).toHaveLength(305);
    expect(manifest.controls.definitions).toHaveLength(30);
    expect(manifest.settings.defaults.keybindings).toEqual(manifest.controls.defaults);
  });

  test('preserves actual ability effects, unavailable summons, unlocks, equipment and optional payloads', () => {
    expect(manifest.abilities.definitions).toEqual(JSON.parse(JSON.stringify(Object.values(CAREER_ABILITY_KITS).flatMap(kit => kit.abilities))));
    expect(manifest.items.definitions).toEqual(JSON.parse(JSON.stringify(Object.values(ITEM_CATALOG))));
    expect(manifest.abilities.progression.filter(entry => !entry.activatable).map(entry => entry.abilityId)).toEqual([
      'siegewright.deploy_gunlet', 'void_magister.summon_idol',
    ]);
    expect(manifest.abilities.progression.filter(entry => entry.unlockLevel === 1)).toHaveLength(72);
    expect(Math.max(...manifest.abilities.progression.map(entry => entry.unlockLevel))).toBe(8);
  });

  test('retains every original map JSON field without converting or filtering geometry', async () => {
    for (const map of [...manifest.maps, ...manifest.developmentMaps]) {
      const original = JSON.parse(await readFile(path.join(REPOSITORY_ROOT, map.sourcePath), 'utf8'));
      expect(map.definition, map.id).toEqual(original);
    }
  });

  test('produces deterministic bytes and content/source hashes without timestamps or absolute source paths', async () => {
    const again = await buildContentManifest();
    expect(canonicalJson(again)).toBe(canonicalJson(manifest));
    expect(manifest.source.sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(manifest.source.contentSha256).toMatch(/^[a-f0-9]{64}$/);
    expect(manifest.source.files.every(file => !path.isAbsolute(file.path) && !file.path.includes('\\'))).toBe(true);
    expect(manifest.source.files.some(file => file.path === 'migration/browser-reference.json')).toBe(true);
    expect(manifest).not.toHaveProperty('generatedAt');
  });

  test('rejects duplicate catalog IDs and nested map entity IDs', () => {
    const duplicate = copy();
    duplicate.abilities.definitions.push(duplicate.abilities.definitions[0]);
    expect(() => validateContentManifest(duplicate)).toThrow(/Duplicate ability ID/);
    const mapDuplicate = copy();
    const map = mapDuplicate.maps.find(entry => entry.definition.enemies.length > 0)!;
    map.definition.enemies.push(map.definition.enemies[0]);
    expect(() => validateContentManifest(mapDuplicate)).toThrow(/Duplicate map .*enemies ID/);
  });

  test('rejects broken travel references and one-way campaign edges', () => {
    const missingTarget = copy();
    missingTarget.maps[0].definition.zoneTriggers![0].targetZoneId = 'missing_map';
    expect(() => validateContentManifest(missingTarget)).toThrow(/Unknown travel target/);
    const missingReverse = copy();
    missingReverse.campaign.edges.pop();
    expect(() => validateContentManifest(missingReverse)).toThrow(/Missing reverse campaign edge/);
  });

  test('rejects non-finite content and tampered content hashes', () => {
    const nonFinite = copy();
    nonFinite.maps[0].definition.spawnPoint!.x = Number.NaN;
    expect(() => validateContentManifest(nonFinite)).toThrow(/Non-finite number/);
    const tampered = copy();
    tampered.items.definitions[0].name += ' altered';
    expect(() => validateContentManifest(tampered)).toThrow(/Content hash mismatch/);
  });

  test('writes an artifact, checks identical bytes, and refuses missing or stale artifacts without overwriting', async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), 'war-unreal-content-'));
    temporaryDirectories.push(directory);
    const output = path.join(directory, 'content.json');
    await expect(exportContent({ output, check: true })).rejects.toThrow(/missing or stale/);
    await exportContent({ output });
    await expect(exportContent({ output, check: true })).resolves.toHaveProperty('schemaVersion', 1);
    await writeFile(output, 'stale\n');
    await expect(exportContent({ output, check: true })).rejects.toThrow(/missing or stale/);
    expect(await readFile(output, 'utf8')).toBe('stale\n');
  }, 30_000);
});

describe('canonical content and Unreal coordinate contract', () => {
  test('converts translations and direction basis from meters Y-up to centimeters Z-up', () => {
    expect(sourcePointToUnreal({ x: 1, y: 2, z: 3 })).toEqual({ X: 300, Y: 100, Z: 200 });
    expect(sourcePointToUnreal({ x: 0, y: 0, z: 1 })).toEqual({ X: 100, Y: 0, Z: 0 });
    expect(sourcePointToUnreal({ x: 1, y: 0, z: 0 })).toEqual({ X: 0, Y: 100, Z: 0 });
    expect(sourcePointToUnreal({ x: 0, y: 1, z: 0 })).toEqual({ X: 0, Y: 0, Z: 100 });
    expect(sourceYawToUnrealDegrees(Math.PI / 2)).toBeCloseTo(90);
    expect(sourceYawToUnrealDegrees(-Math.PI)).toBeCloseTo(-180);
    const yaw = Math.PI / 3;
    const direction = sourcePointToUnreal({ x: Math.sin(yaw), y: 0, z: Math.cos(yaw) });
    const convertedYaw = sourceYawToUnrealDegrees(yaw) * Math.PI / 180;
    expect(direction.X).toBeCloseTo(Math.cos(convertedYaw) * 100);
    expect(direction.Y).toBeCloseTo(Math.sin(convertedYaw) * 100);
    expect(() => sourcePointToUnreal({ x: Infinity, y: 0, z: 0 })).toThrow();
    expect(() => sourcePointToUnreal({ x: 1e308, y: 0, z: 0 })).toThrow();
    expect(() => sourceYawToUnrealDegrees(NaN)).toThrow();
  });

  test('sorts object keys while retaining array order, null, false and zero', () => {
    expect(canonicalJson({ z: [2, 1], a: { z: undefined, f: false, n: null, v: 0 } }))
      .toBe(canonicalJson({ a: { v: 0, n: null, f: false }, z: [2, 1] }));
    expect(JSON.parse(canonicalJson({ z: [2, 1] })).z).toEqual([2, 1]);
  });

  test('rejects values JSON.stringify would lose or corrupt', () => {
    for (const value of [NaN, Infinity, -Infinity, [undefined], { fn: () => true }, { date: new Date() }, { bigint: 1n }, { [Symbol('x')]: 1 }]) {
      expect(() => assertJsonSerializable(value)).toThrow();
    }
    const circular: { self?: unknown } = {};
    circular.self = circular;
    expect(() => assertJsonSerializable(circular)).toThrow(/Circular/);
  });
});
