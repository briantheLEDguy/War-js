import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';
import { CAMPAIGN_GRAPH_EDGES, CAMPAIGN_ZONES } from '../src/data/campaign';
import { QUESTS } from '../src/data/quests';
import type { EnemySpawn, PropSpawn, ZoneDefinition } from '../src/world/ZoneLoader';

const maps = new Map(CAMPAIGN_ZONES.map((node) => [node.id, readZone(node.id)]));
const keepZones = CAMPAIGN_ZONES.filter((node) => node.nodeRole === 'battlefield' || node.nodeRole === 'fortress');

function readZone(id: string): ZoneDefinition {
  return JSON.parse(readFileSync(path.join(process.cwd(), 'public', 'assets', 'maps', `${id}.json`), 'utf8'));
}

function commanders(zone: ZoneDefinition): EnemySpawn[] {
  return zone.enemies.filter((enemy) => enemy.encounter?.type === 'keep_commander');
}

function expectClearOfColliders(enemy: EnemySpawn, props: PropSpawn[]): void {
  for (const prop of props) {
    for (const collider of prop.colliders ?? []) {
      const sx = (prop.scale ?? 1) * (prop.scaleX ?? 1);
      const sz = (prop.scale ?? 1) * (prop.scaleZ ?? 1);
      const rotation = prop.rotY ?? 0;
      const centerX = prop.x + (collider.x ?? 0) * sx * Math.cos(rotation) - (collider.z ?? 0) * sz * Math.sin(rotation);
      const centerZ = prop.z + (collider.x ?? 0) * sx * Math.sin(rotation) + (collider.z ?? 0) * sz * Math.cos(rotation);
      const angle = rotation + (collider.rotY ?? 0);
      const dx = (enemy.x - centerX) * Math.cos(angle) + (enemy.z - centerZ) * Math.sin(angle);
      const dz = -(enemy.x - centerX) * Math.sin(angle) + (enemy.z - centerZ) * Math.cos(angle);
      const clearance = Math.hypot(
        Math.max(0, Math.abs(dx) - collider.width * sx / 2),
        Math.max(0, Math.abs(dz) - collider.depth * sz / 2),
      );
      expect(clearance, `${enemy.id} intersects ${prop.id}`).toBeGreaterThan(1);
    }
  }
}

describe('generated keep commanders', () => {
  test('binds exactly one uniquely named commander to every keep across all 18 combat zones', () => {
    expect(keepZones).toHaveLength(18);
    const allCommanders = [...maps.values()].flatMap(commanders);
    expect(allCommanders).toHaveLength(36);
    expect(new Set(allCommanders.map((enemy) => enemy.id)).size).toBe(36);
    expect(new Set(allCommanders.map((enemy) => enemy.name)).size).toBe(36);

    for (const node of CAMPAIGN_ZONES) {
      const zone = maps.get(node.id)!;
      const keeps = zone.rvrObjectives?.filter((objective) => objective.type === 'keep') ?? [];
      expect(commanders(zone), node.id).toHaveLength(keeps.length);
      for (const keep of keeps) {
        const bound = commanders(zone).filter((enemy) => enemy.encounter?.objectiveId === keep.id);
        expect(bound, keep.id).toHaveLength(1);
        expect(bound[0].encounter).toEqual({
          type: 'keep_commander', objectiveId: keep.id, realm: keep.defaultRealm, enrageHealthFraction: 0.35,
        });
        expect(bound[0].name).toMatch(keep.defaultRealm === 'aegis'
          ? /^Aegis Castellan [A-Z][a-z]+ [A-Z][a-z]+$/
          : /^Riftbound Warlord [A-Z][a-z]+ [A-Z][a-z]+$/);
      }
    }
  });

  test('places commanders inside the inner courtyard and clear of walls, doors, and furniture', () => {
    for (const node of keepZones) {
      const zone = maps.get(node.id)!;
      for (const enemy of commanders(zone)) {
        const keep = zone.rvrObjectives!.find((objective) => objective.id === enemy.encounter!.objectiveId)!;
        const prefix = `${keep.id}_keep`;
        const wall = (suffix: string) => zone.props.find((prop) => prop.id === `${prefix}_${suffix}`)!;
        expect(enemy.x).toBeGreaterThan(wall('inner_west_wall').x + 2);
        expect(enemy.x).toBeLessThan(wall('inner_east_wall').x - 2);
        expect(enemy.z).toBeGreaterThan(wall('inner_front_door').z + 2);
        expect(enemy.z).toBeLessThan(wall('inner_rear_door').z - 2);
        expect(Math.hypot(enemy.x - keep.x, enemy.z - keep.z)).toBeLessThan(keep.captureRadius);
        expectClearOfColliders(enemy, zone.props);
      }
    }
  });

  test('uses existing approved runtime profiles and keeps encounter difficulty tiered', () => {
    const modelsDir = path.join(process.cwd(), 'public', 'assets', 'models');
    const registry = JSON.parse(readFileSync(path.join(modelsDir, 'asset-index.json'), 'utf8'));
    const expectedLevels: Record<string, number> = { T1: 5, T2: 11, T3: 20, T4: 34, Fortress: 42 };
    const expectedDamage: Record<string, number> = { T1: 7, T2: 9, T3: 11, T4: 13, Fortress: 15 };

    for (const node of keepZones) {
      for (const enemy of commanders(maps.get(node.id)!)) {
        const profile = registry.characterProfiles[enemy.characterProfileKey!];
        expect(profile, enemy.id).toMatchObject({ approvalState: 'approved', runtimeReady: true });
        expect(existsSync(path.join(modelsDir, profile.model)), enemy.id).toBe(true);
        expect(enemy).toMatchObject({
          archetype: 'captain', level: expectedLevels[node.tier],
          attackDamage: expectedDamage[node.tier], aggroRange: 18, attackRange: 3.8,
        });
        expect(enemy.maxHealth).toBe(240 + expectedLevels[node.tier] * 20);
      }
    }
  });

  test('preserves field captains and keeps every expedition kill target independent of commander fights', () => {
    for (const node of keepZones) {
      const isFortress = node.nodeRole === 'fortress';
      const captain = maps.get(node.id)!.enemies.find((enemy) => enemy.id === `${node.id}_${isFortress ? 'captain' : 'field_captain'}`)!;
      expect(captain, node.id).toMatchObject({ archetype: 'captain', x: 0, z: isFortress ? 72 : 78 });
      expect(captain.encounter).toBeUndefined();
    }
    for (const quest of QUESTS) {
      for (const objective of quest.objectives) {
        if (!objective.killTarget || !objective.zoneId) continue;
        const targets = maps.get(objective.zoneId)!.enemies.filter((enemy) => enemy.name === objective.killTarget);
        expect(targets.length, `${quest.id}:${objective.id}`).toBeGreaterThan(0);
        expect(targets.every((enemy) => !enemy.encounter), objective.killTarget).toBe(true);
      }
    }
    for (const [id, name] of [['brightfen_approach', 'Brightfen Field Captain'], ['cinderfen_outskirts', 'Cinderfen Field Captain']]) {
      expect(maps.get(id)!.enemies.find((enemy) => enemy.id === `${id}_field_captain`)).toMatchObject({
        name, level: 4, maxHealth: 220,
      });
    }
  });

  test('preserves campaign routes and keeps arriving players beyond commander aggro range', () => {
    for (const zone of maps.values()) {
      const expectedTargets = CAMPAIGN_GRAPH_EDGES.filter((edge) => edge.fromZoneId === zone.id).map((edge) => edge.toZoneId).sort();
      expect(zone.zoneTriggers!.map((trigger) => trigger.targetZoneId).sort(), zone.id).toEqual(expectedTargets);
      const arrivals = [zone.spawnPoint!, ...[...maps.values()].flatMap((source) =>
        source.zoneTriggers!.filter((trigger) => trigger.targetZoneId === zone.id).map((trigger) => trigger.targetSpawn!),
      )];
      for (const enemy of commanders(zone)) {
        for (const arrival of arrivals) {
          expect(Math.hypot(enemy.x - arrival.x, enemy.z - arrival.z), enemy.id).toBeGreaterThan(enemy.aggroRange! + 10);
        }
      }
    }
  });
});
