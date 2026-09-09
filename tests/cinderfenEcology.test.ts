import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { createOrvrGridHeightSampler } from '../src/shared/orvrTerrain';
import { mapPropNavigation } from '../server/mapNavigation';
import { campaignColliderContains, campaignColliderBlocksHeight } from '../src/shared/orvr/navigation';
import { frontierPropDistances } from '../src/world/FrontierProps';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
// @ts-expect-error Native ESM authoring source.
import { composeCinderfenEcology, cinderfenSurveyHeightAt } from '../scripts/campaign/cinderfen-ecology.mjs';

const read = (file: string) => JSON.parse(readFileSync(file, 'utf8'));
const original = read('public/assets/maps/cinderfen_outskirts.json');
const zone = composeCinderfenEcology(structuredClone(original)) as ZoneDefinition;
const plants = zone.props.filter(p => p.id?.includes('_wetland_'));
const trees = zone.props.filter(p => p.id?.includes('_alder_'));
const metadata = read('authoring/blender/cinderfen-nature/builder-metadata.json');
const heightAt = createOrvrGridHeightSampler(zone.orvrLayout!.terrain, zone.size, zone.segments);
const radius = (key: string, scale: number) => {
  const { minimum: lo, maximum: hi } = metadata.assets[key].boundsYUp;
  return Math.hypot(Math.max(Math.abs(lo[0]), Math.abs(hi[0])), Math.max(Math.abs(lo[2]), Math.abs(hi[2]))) * scale;
};

describe('Cinderfen retained-survey wetland colonies', () => {
  it('is repeatable, retains gameplay and gathers plants into separated colonies', () => {
    expect(composeCinderfenEcology(structuredClone(zone))).toEqual(zone);
    for (const key of ['paths', 'npcs', 'enemies', 'resourceNodes', 'rvrObjectives', 'zoneTriggers', 'spawnPoint', 'ambientLife'] as const)
      expect(zone[key]).toEqual(original[key]);
    expect(zone.orvrLayout!.keeps).toEqual(original.orvrLayout.keeps);
    expect(plants.length).toBeGreaterThan(500); expect(plants.length).toBeLessThan(850);
    expect(new Set(plants.map(p => p.id!.replace(/_\d+$/, ''))).size).toBeGreaterThanOrEqual(9);
    expect(new Set(plants.map(p => p.assetKey)).size).toBe(2);
    for (const node of original.resourceNodes) expect(zone.props.find(p => p.id === node.visualPropId))
      .toEqual(original.props.find((p: { id: string }) => p.id === node.visualPropId));
  });

  it('matches runtime ground samples, plants roots below the surface and keeps deep pools open', () => {
    for (const plant of plants) {
      const height = heightAt(plant.x, plant.z);
      expect(cinderfenSurveyHeightAt(plant.x, plant.z)).toBeCloseTo(height, 6);
      expect(plant.heightMode).toBe('absolute');
      expect(plant.y!).toBeLessThan(height);
      expect(height - plant.y!).toBeLessThan(.2);
      expect(height).toBeGreaterThanOrEqual(-.73); expect(height).toBeLessThanOrEqual(.18);
      if (plant.assetKey!.includes('sedge')) expect(height).toBeGreaterThanOrEqual(-.2);
      expect(plant.colliders).toEqual([]); expect(plant.cameraSolid).toBe(false);
    }
    const changed = structuredClone(original); changed.orvrLayout.terrain.landforms[0].height++;
    expect(() => composeCinderfenEcology(changed)).toThrow(/current retained terrain survey/);
  });

  it('keeps measured foliage envelopes outside roads, capture circles and construction', () => {
    const blockers = mapPropNavigation(zone.props, heightAt).collision;
    const blocked: string[] = [];
    for (const plant of plants) {
      const r = radius(plant.assetKey!, plant.scale ?? 1), point = { x: plant.x, y: plant.y!, z: plant.z };
      if (blockers.some(c => campaignColliderBlocksHeight(c, point.y) && campaignColliderContains(c, point, r))) blocked.push(`${plant.id}: construction`);
      for (const objective of zone.rvrObjectives ?? []) if (Math.hypot(plant.x - objective.x, plant.z - objective.z) <= objective.captureRadius + r) blocked.push(`${plant.id}: objective`);
      for (const road of zone.paths ?? []) for (let i = 1; i < road.points.length; i++) {
        const a = road.points[i - 1], b = road.points[i], dx = b.x - a.x, dz = b.z - a.z;
        const t = Math.max(0, Math.min(1, ((plant.x - a.x) * dx + (plant.z - a.z) * dz) / (dx * dx + dz * dz || 1)));
        if (Math.hypot(plant.x - a.x - dx * t, plant.z - a.z - dz * t) <= road.width / 2 + r) blocked.push(`${plant.id}: road ${road.id}`);
      }
    }
    expect(blocked).toEqual([]);
  });

  it('uses approved GM models with close foliage LODs and no phantom collision', () => {
    const catalog = read('src/world/editor/prefabs.generated.json');
    const registry = read('public/assets/models/asset-index.json').staticProps;
    for (const key of new Set(plants.map(p => p.assetKey!))) {
      const entry = catalog.find((p: { assetKey: string }) => p.assetKey === key);
      expect(registry[key].runtimeReady).toBe(true); expect(entry.group).toBe('Cinderfen Nature');
      expect(new Set([entry.model, ...entry.lodModels]).size).toBe(3); expect(entry.colliders).toEqual([]);
      expect(entry.cameraSolid).toBe(false); expect(frontierPropDistances(key).lod[1]).toBeLessThanOrEqual(18);
      expect(frontierPropDistances(key).cull).toBeLessThanOrEqual(120);
    }
  });

  it('plants varied alder stands on dry margins with their authored trunk collision', () => {
    expect(trees.length).toBeGreaterThan(500); expect(trees.length).toBeLessThanOrEqual(650);
    expect(new Set(trees.map(p => p.id!.replace(/_\d+$/, ''))).size).toBe(12);
    expect(new Set(trees.map(p => p.scale)).size).toBeGreaterThan(100);
    for (const tree of trees) {
      const ground = heightAt(tree.x, tree.z);
      expect(ground).toBeGreaterThanOrEqual(-.14); expect(ground).toBeLessThanOrEqual(9);
      expect(tree.heightMode).toBe('absolute'); expect(tree.y!).toBeLessThan(ground);
      expect(ground - tree.y!).toBeLessThan(.3);
      expect(tree.colliders).toEqual(metadata.assets[tree.assetKey!].colliders);
      expect(tree.colliderSpace).toBe('model'); expect(tree.cameraSolid).toBe(true);
    }
    const entry = read('src/world/editor/prefabs.generated.json').find((p: { assetKey: string }) => p.assetKey === trees[0].assetKey);
    expect(entry.lodModels).toHaveLength(2); expect(entry.colliders).toEqual(trees[0].colliders);
    expect(frontierPropDistances(trees[0].assetKey!)).toEqual({ lod: [0, 35, 90], cull: 450 });
  });

  it('keeps tree crowns clear of built structures and full campaign road widths', () => {
    const blockers = mapPropNavigation(zone.props.filter(p => !p.id?.includes('_alder_')), heightAt).collision;
    const blocked: string[] = [];
    for (const tree of trees) {
      const r = radius(tree.assetKey!, tree.scale ?? 1), point = { x: tree.x, y: tree.y!, z: tree.z };
      if (blockers.some(c => campaignColliderContains(c, point, r))) blocked.push(`${tree.id}: construction`);
      for (const objective of zone.rvrObjectives ?? []) if (Math.hypot(tree.x - objective.x, tree.z - objective.z) <= objective.captureRadius + r) blocked.push(`${tree.id}: objective`);
      for (const road of zone.paths ?? []) for (let i = 1; i < road.points.length; i++) {
        const a = road.points[i - 1], b = road.points[i], dx = b.x - a.x, dz = b.z - a.z;
        const t = Math.max(0, Math.min(1, ((tree.x - a.x) * dx + (tree.z - a.z) * dz) / (dx * dx + dz * dz || 1)));
        if (Math.hypot(tree.x - a.x - dx * t, tree.z - a.z - dz * t) <= road.width / 2 + r) blocked.push(`${tree.id}: road ${road.id}`);
      }
    }
    expect(blocked).toEqual([]);
  });
});
