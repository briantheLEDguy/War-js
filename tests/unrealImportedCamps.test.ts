import { readFileSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
// @ts-expect-error The campaign generator uses executable JavaScript modules.
import { applyImportedCamps, importedPopulation } from '../scripts/campaign/imported-population.mjs';
import { buildContentManifest } from '../scripts/unreal/export-content';

describe('supplied character camps', () => {
  test('adds only the intended identities and is idempotent', () => {
    const retained = { id: 'retained', name: 'Retained objective', encounter: { type: 'keep_commander' } };
    const map = { id: 'brightfen_approach', enemies: [retained], npcs: [] };
    applyImportedCamps(map);
    expect(map.enemies[0]).toBe(retained);
    expect(map.enemies).toHaveLength(4);
    const once = structuredClone(map);
    applyImportedCamps(map);
    expect(map).toEqual(once);
    map.enemies[1].name = 'Owner change';
    expect(() => applyImportedCamps(map)).toThrow(/edited/);
  });

  test('exports seven supported hostile enemies and six friendly inhabitants', async () => {
    const manifest = await buildContentManifest();
    let enemies = 0, inhabitants = 0;
    for (const camp of importedPopulation.camps) {
      const map = manifest.maps.find(row => row.id === camp.zone)!.definition;
      const source = JSON.parse(readFileSync(`public/assets/maps/${camp.zone}.json`, 'utf8'));
      expect(map).toEqual(source);
      for (const member of camp.members) {
        if (camp.allegiance === 'hostile') {
          const enemy = map.enemies.find(row => row.id === member.id)!;
          expect(enemy.archetype).toBe('raider');
          expect(enemy).not.toHaveProperty('encounter');
          expect(enemy.characterProfileKey).toMatch(/^npc_import_/);
          expect(Math.hypot(enemy.x-source.spawnPoint.x, enemy.z-source.spawnPoint.z)).toBeGreaterThan(60);
          for (const point of [...source.zoneTriggers, ...source.rvrObjectives]) {
            expect(Math.hypot(enemy.x-point.x, enemy.z-point.z)).toBeGreaterThan(60 + (point.radius ?? point.captureRadius ?? 0));
          }
          for (const road of source.paths) {
            for (let i = 1; i < road.points.length; i++) {
              const a = road.points[i-1], b = road.points[i];
              const dx = b.x-a.x, dz = b.z-a.z;
              const t = Math.max(0, Math.min(1, ((enemy.x-a.x)*dx+(enemy.z-a.z)*dz)/(dx*dx+dz*dz || 1)));
              expect(Math.hypot(enemy.x-a.x-t*dx, enemy.z-a.z-t*dz)).toBeGreaterThan(15 + road.width/2);
            }
          }
          enemies++;
        } else {
          expect(map.npcs?.find(row => row.id === member.id)?.role).toMatch(/guard|ambient/);
          inhabitants++;
        }
      }
    }
    expect([enemies, inhabitants]).toEqual([7,6]);
  }, 20_000);
});
