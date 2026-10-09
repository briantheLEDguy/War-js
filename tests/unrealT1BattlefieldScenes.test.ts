import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { battlefieldLandscape } from '../scripts/unreal/t1-battlefield-landscape';
import { battlefieldScenes } from '../scripts/unreal/t1-battlefield-scenes';
import { distanceToSpatialSegment } from '../shared/worldSpatial';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';
describe('first-pair battlefield scene cells', () => {
  for (const id of ['sunmeadow_march', 'cinderfen_outskirts']) it(`${id} keeps open roads, objective spaces and off-road choices`, () => {
    const z = battlefieldLandscape(redesignT1(JSON.parse(readFileSync(`public/assets/maps/${id}.json`, 'utf8')) as ZoneDefinition)), before = JSON.stringify(z);
    const cells = battlefieldScenes(z);
    expect(JSON.stringify(z)).toBe(before); expect(cells).toHaveLength(10);
    expect(cells.flatMap(c => c.placements).length).toBeGreaterThan(100);
    for (const c of cells) {
      expect(c.visualApproved).toBe(false); expect(c.combatCoverAccepted).toBe(false);
      for (const p of c.placements) for (const corridor of z.orvrLayout!.terrain.clearCorridors) for (let i = 1; i < corridor.points.length; i++) {
        expect(distanceToSpatialSegment(p, corridor.points[i - 1], corridor.points[i])).toBeGreaterThan(Math.hypot(p.width, p.depth) / 2 + 12);
      }
    }
    expect(battlefieldScenes(z)).toEqual(cells);
    expect(cells.filter(c => c.placements.length > 5).length).toBeGreaterThan(5);
    for (const p of cells.flatMap(c => c.placements)) {
      expect(p.scaleAxes.every(s => s >= .4 && s <= 5.3)).toBe(true);
      expect(p.tiltDegrees.every(a => Math.abs(a) <= 7)).toBe(true);
      for (const objective of z.orvrLayout!.battlefieldObjectives) expect(Math.hypot(p.x-objective.x,p.z-objective.z)).toBeGreaterThan(Math.hypot(p.width,p.depth)/2+42);
    }
    expect(new Set(cells.flatMap(c => c.placements.map(p => p.id))).size).toBe(cells.flatMap(c => c.placements).length);
  });
});

it('reserves pedestrian contour paths that do not grade the terrain', () => {
  const z = battlefieldLandscape(redesignT1(JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8')) as ZoneDefinition));
  const original = battlefieldScenes(z), p = original.flatMap(c => c.placements)[0];
  const path = { id: 'sunmeadow_march_western_spur_counter_test', style: 'dirt_trail' as const, width: 4,
    points: [{ x: p.x - 30, z: p.z }, { x: p.x + 30, z: p.z }] };
  z.paths!.push(path); const terrain = JSON.stringify(z.orvrLayout!.terrain), cells = battlefieldScenes(z);
  expect(JSON.stringify(z.orvrLayout!.terrain)).toBe(terrain);
  expect(cells.flatMap(c => c.placements).some(q => q.id === p.id)).toBe(false);
  for (const q of cells.flatMap(c => c.placements)) expect(distanceToSpatialSegment(q, path.points[0], path.points[1]))
    .toBeGreaterThan(Math.hypot(q.width, q.depth) / 2 + path.width / 2 + 3);
});
